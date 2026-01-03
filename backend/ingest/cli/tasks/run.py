from __future__ import annotations

"""
/**
 * @file run.py
 * @brief 执行单个 ingest job 的 Task runner。
 *
 * 职责边界（非常重要）：
 * - 只负责「一个 job」的生命周期调度
 * - 不解析 JSON（configs.py 已完成）
 * - 不 import 具体实现（source/cache/transform）
 * - 通过 wiring + registry 实例化对象
 *
 * Run exactly one job, nothing more.
 */
"""

from dataclasses import dataclass
from typing import Optional

from ingest.utils.logger import get_logger
from ingest.cli.configs import LoadedConfig, JobConfig
from .interface import (
    Task,
    TaskState,
    TaskError,
    Artifact,
    Diagnostics,
)

from ingest.cache.interface import CacheKey
from ingest.transform.interface import TransformerSpec, JsTargetSpec
from ingest.transform.transformer import Transformer

from ingest.cache.hashlib import make_cache_key

_LOG = get_logger(__name__)


# ============================================================
# Task implementation
# ============================================================


@dataclass
class RunJobTask(Task):
    """
    @brief 执行单个 Job 的 Task 实现
           Task implementation for running exactly one job.
    """

    loaded: LoadedConfig
    job: JobConfig

    _state: TaskState = TaskState.CREATED
    _artifacts: list[Artifact] = None  # type: ignore
    _diagnostics: Diagnostics = None  # type: ignore
    _error: Optional[TaskError] = None

    # runtime objects
    _transformer: Optional[Transformer] = None

    # -----------------------
    # lifecycle
    # -----------------------

    def prepare(self) -> None:
        """
        @brief 准备阶段：实例化 cache / transformer / source
        """
        _LOG.info("task[%s] prepare start", self.job.name)
        self._state = TaskState.PREPARED

        self._artifacts = []
        self._diagnostics = Diagnostics()

        cfg = self.loaded.config
        paths = self.loaded.paths

        # 延迟 import：避免 import-time 副作用
        from ingest import wiring

        # -------- caches --------
        raw_cache_cls = wiring.RAW_CACHES.require(cfg.cache_configs.raw.name)
        pre_cache_cls = wiring.PREPROCESSED_CACHES.require(
            cfg.cache_configs.preprocessed.name
        )

        raw_cache = raw_cache_cls(**cfg.cache_configs.raw.config)
        pre_cache = pre_cache_cls(**cfg.cache_configs.preprocessed.config)

        # -------- transformer spec --------
        tcfg = cfg.transform_configs
        spec = TransformerSpec(
            frontend_name=self.job.frontend.name,
            optimizer_name=self.job.optimizer.name,
            backend_name=self.job.backend.name,
            ir_version=tcfg.ir_version,
            target=JsTargetSpec(
                js_abi_version=tcfg.js_abi_version,
                module_format=tcfg.module_format,
                layout=tcfg.layout,
                path_prefix=tcfg.path_prefix,
                options=tcfg.options,
            ),
            frontend_config=self.job.frontend.config,
            optimizer_config=self.job.optimizer.config,
            backend_config=self.job.backend.config,
        )

        self._transformer = Transformer(
            spec=spec,
            raw_cache=raw_cache,
            preprocessed_cache=pre_cache,
        )

        self._diagnostics.data["job"] = self.job.name
        self._diagnostics.data["transformer"] = {
            "frontend": spec.frontend_name,
            "optimizer": spec.optimizer_name,
            "backend": spec.backend_name,
        }

        _LOG.info("task[%s] prepare done", self.job.name)

    def run(self) -> None:
        """
        @brief 执行阶段：source -> raw -> transform -> preprocessed
        """
        if self._state is not TaskState.PREPARED:
            raise RuntimeError("task.run() called before prepare()")

        self._state = TaskState.RUNNING
        _LOG.info("task[%s] run start", self.job.name)

        try:
            from ingest import wiring

            # -------- source --------
            # V2：source 封装 config；validate()/fetch() 不再注入 config
            source_cls = wiring.SOURCES.require(self.job.source.name)
            source = source_cls(**self.job.source.config)

            source.validate()

            # -------- fetch & cache raw --------
            # V2：source.fetch() 直接产出 RawCacheRecord（payload + meta），cache 对齐
            raw_cache = self._transformer.raw_cache  # type: ignore

            keys: list[CacheKey] = []

            for record in source.fetch():
                key = make_cache_key(
                    config_name=self.loaded.config.profile,
                    record=record,
                )
                raw_cache.save(key, record)
                keys.append(key)

            self._diagnostics.data["raw_items"] = len(keys)

            # -------- transform --------
            for key in keys:
                result = self._transformer.run(key)
                for path in result.artifacts.keys():
                    self._artifacts.append(
                        Artifact(
                            kind="preprocessed",
                            path=path,
                        )
                    )

            self._state = TaskState.FINISHED
            _LOG.info("task[%s] run finished", self.job.name)

        except Exception as e:  # noqa: BLE001
            import traceback

            self._state = TaskState.FAILED
            self._error = TaskError(
                type=type(e).__name__,
                message=str(e),
                traceback=traceback.format_exc(),
            )
            _LOG.error(
                "task[%s] failed: %s\n%s", self.job.name, e, traceback.format_exc()
            )
            raise

    def close(self) -> None:
        """
        @brief 清理阶段（必须幂等）
        """
        _LOG.info("task[%s] close", self.job.name)
        self._state = TaskState.CLOSED

    # -----------------------
    # state & results
    # -----------------------

    @property
    def state(self) -> TaskState:
        return self._state

    @property
    def artifacts(self) -> list[Artifact]:
        return self._artifacts or []

    @property
    def meta(self):
        return {
            "job": self.job.name,
            "state": self._state.value,
        }

    @property
    def diagnostics(self) -> Diagnostics:
        return self._diagnostics

    @property
    def error(self) -> Optional[TaskError]:
        return self._error
