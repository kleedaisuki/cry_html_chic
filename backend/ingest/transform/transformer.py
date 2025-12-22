# backend/ingest/transform/transformer.py
from __future__ import annotations

"""
/**
 * @brief Transform 工具链驱动（driver）：raw cache -> IR -> JS artifacts -> preprocessed cache。
 *        Transform toolchain driver: raw cache -> IR -> JS artifacts -> preprocessed cache.
 *
 * 核心约束 / Core constraints:
 * - 从 ingest.wiring 查 registries（不是注入）。
 *   Registries come from ingest.wiring (not DI).
 * - Registry 的使用方式：require(name) -> class，然后实例化。
 *   Registry usage: require(name) -> class, then instantiate.
 */
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import MutableMapping

from ingest.utils.logger import get_logger
from ingest.cache.interface import (
    CacheKey,
    RawCache,
    PreprocessedCache,
    PreprocessedCacheMeta,
)
from .interface import (
    BackendCompiler,
    FrontendCompiler,
    IRModule,
    JsonValue,
    Optimizer,
    RawMeta,
    RawRecord,
    TransformProvenance,
    TransformResult,
    TransformerSpec,
)

_LOG = get_logger(__name__)


def _utc_now_iso_z() -> str:
    """
    /**
     * @brief 生成 UTC ISO-8601 时间戳（秒级，末尾 Z）/ Generate UTC ISO-8601 timestamp (seconds, trailing Z).
     */
    """
    dt = datetime.now(timezone.utc).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def _ensure_mapping_json_value(d: dict[str, JsonValue], *, what: str) -> None:
    """
    /**
     * @brief 保守校验：顶层值需为 JsonValue（允许 list/dict 嵌套）。
     *        Conservative check: top-level values must be JsonValue (nested list/dict allowed).
     */
    """
    for k, v in d.items():
        if not isinstance(k, str):
            raise TypeError(f"{what}: key must be str, got {type(k)}")
        if v is None or isinstance(v, (bool, int, float, str, list, dict)):
            continue
        raise TypeError(f"{what}: value must be JsonValue, got {type(v)}")


@dataclass
class Transformer:
    """
    /**
     * @brief Transformer 驱动器：负责串联 cache 与三段编译工具链。
     *        Transformer driver: orchestrates caches and 3-stage toolchain.
     */
    """

    spec: TransformerSpec
    raw_cache: RawCache
    preprocessed_cache: PreprocessedCache

    frontend: FrontendCompiler = field(init=False)
    optimizer: Optimizer = field(init=False)
    backend: BackendCompiler = field(init=False)

    def __post_init__(self) -> None:
        """
        /**
         * @brief 从 wiring 查表并实例化 frontend/optimizer/backend。
         *        Instantiate frontend/optimizer/backend via wiring registries.
         */
        """
        # 延迟 import：避免 wiring 在 import-time 拉一堆模块导致循环依赖
        from ingest import wiring

        # 直接按 Registry 用法：require(name) -> class
        f_cls = wiring.FRONTENDS.require(self.spec.frontend_name)
        o_cls = wiring.OPTIMIZERS.require(self.spec.optimizer_name)
        b_cls = wiring.BACKENDS.require(self.spec.backend_name)

        # registry 只存 class，不存 instance；实例化在这里做
        self.frontend = f_cls()
        self.optimizer = o_cls()
        self.backend = b_cls()

        _LOG.info(
            "transformer initialized: frontend=%s optimizer=%s backend=%s ir=%d js_abi=%d",
            getattr(self.frontend, "name", self.spec.frontend_name),
            getattr(self.optimizer, "name", self.spec.optimizer_name),
            getattr(self.backend, "name", self.spec.backend_name),
            self.spec.ir_version,
            self.spec.target.js_abi_version,
        )

    def run(self, key: CacheKey) -> TransformResult:
        """
        /**
         * @brief 执行一次 transform：raw cache -> preprocessed cache。
         *        Run once: raw cache -> preprocessed cache.
         *
         * @param key 输入 raw 的缓存键 / CacheKey for raw input.
         * @return TransformResult（artifacts+provenance+diagnostics）/ result.
         *
         * @note
         *        本方法不吞异常：cache miss、compile/optimize/emit 失败直接上抛。
         *        This method does not swallow exceptions: cache miss and stage failures bubble up.
         */
        """
        _LOG.info(
            "transform run start: config=%s hash=%s fetched_at=%s",
            key.config_name,
            key.content_hash,
            key.fetched_at_iso,
        )

        raw = self.raw_cache.load(key)

        # cache.meta -> transform.RawMeta（只做形状适配）
        meta = RawMeta(
            source_name=raw.meta.source_name,
            fetched_at_iso=raw.meta.fetched_at_iso,
            content_type=raw.meta.content_type,
            encoding=raw.meta.encoding,
            extra=dict(raw.meta.meta),
        )
        record = RawRecord(payload=raw.payload, meta=meta)

        # Stage 1: Frontend compile
        _ensure_mapping_json_value(
            dict(self.spec.frontend_config), what="frontend_config"
        )
        ir0: IRModule = self.frontend.compile(record, config=self.spec.frontend_config)

        # Stage 2: Optimizer
        _ensure_mapping_json_value(
            dict(self.spec.optimizer_config), what="optimizer_config"
        )
        ir1: IRModule = self.optimizer.optimize(ir0, config=self.spec.optimizer_config)

        # Stage 3: Backend emit
        _ensure_mapping_json_value(
            dict(self.spec.backend_config), what="backend_config"
        )
        artifacts = dict(
            self.backend.emit(
                ir1, target=self.spec.target, config=self.spec.backend_config
            )
        )

        # Provenance & Diagnostics
        prov = TransformProvenance(
            frontend=f"{getattr(self.frontend, 'name', self.spec.frontend_name)}@{getattr(self.frontend, 'version', 'unknown')}",
            optimizer=f"{getattr(self.optimizer, 'name', self.spec.optimizer_name)}@{getattr(self.optimizer, 'version', 'unknown')}",
            backend=f"{getattr(self.backend, 'name', self.spec.backend_name)}@{getattr(self.backend, 'version', 'unknown')}",
            ir_version=self.spec.ir_version,
            js_abi_version=self.spec.target.js_abi_version,
            extra={
                "config_name": key.config_name,
                "content_hash": key.content_hash,
                "raw_fetched_at_iso": raw.meta.fetched_at_iso,
            },
        )

        diagnostics: MutableMapping[str, JsonValue] = {
            "artifacts_count": len(artifacts),
            "artifact_names": sorted(list(artifacts.keys())),
        }

        # 写入 preprocessed cache
        built_at_iso = _utc_now_iso_z()

        # 不修改入参 key：若缺 fetched_at_iso，则派生写入 key
        write_key = key
        if write_key.fetched_at_iso is None:
            write_key = CacheKey(
                config_name=key.config_name,
                content_hash=key.content_hash,
                fetched_at_iso=built_at_iso,
            )

        extra: MutableMapping[str, JsonValue] = {
            "transform": {
                "frontend": prov.frontend,
                "optimizer": prov.optimizer,
                "backend": prov.backend,
                "ir_version": prov.ir_version,
                "js_abi_version": prov.js_abi_version,
                "extra": dict(prov.extra),
            },
            "diagnostics": dict(diagnostics),
        }

        meta_pp = PreprocessedCacheMeta(
            built_at_iso=built_at_iso,
            schema_version=self.spec.target.js_abi_version,
            extra=extra,
        )

        self.preprocessed_cache.save(write_key, artifacts=artifacts, meta=meta_pp)

        _LOG.info(
            "transform run done: built_at=%s files=%d", built_at_iso, len(artifacts)
        )

        return TransformResult(
            artifacts=artifacts,
            provenance=prov,
            diagnostics=dict(diagnostics),
        )
