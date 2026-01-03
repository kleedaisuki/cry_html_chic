from __future__ import annotations

"""
/**
 * @file plain_optimizer.py
 * @brief 最小 Optimizer：不修改 IR，仅透传 / Minimal Optimizer: pass-through IR without changes.
 *
 * 设计意图 / Design intent:
 * - 作为工具链占位符：Front-end -> (Plain Optimizer) -> Back-end
 *   Placeholder in toolchain: Front-end -> (Plain Optimizer) -> Back-end
 * - 确保工具链可跑通，并提供一个“无优化基线”用于对比。
 *   Ensures the pipeline runs and provides a no-op baseline for comparison.
 *
 * 核心约束 / Core constraints:
 * - 必须通过 ingest.wiring.register_optimizer 注册（registry 存 class，不存 instance）。
 *   Must register via ingest.wiring.register_optimizer (registry stores classes, not instances).
 */
"""

from typing import Mapping

from ingest.utils.logger import get_logger
from ingest.wiring import register_optimizer
from ingest.transform.interface import IRModule, JsonValue, Optimizer

_LOG = get_logger(__name__)


@register_optimizer("plain")
class PlainOptimizer(Optimizer):
    """
    /**
     * @brief 空优化器（No-op Optimizer）：输入 IRModule 原样输出。
     *        No-op optimizer: returns the input IRModule unchanged.
     *
     * @note
     * - 为避免“同一个 dict 被多阶段意外共享修改”，默认做浅拷贝 dict(module)。
     *   To reduce accidental shared-mutation across stages, returns a shallow copy by default.
     * - 若未来需要真正的优化逻辑，可新增 optimizer 实现，不要在基类/driver 里塞复杂分支。
     *   If real optimization is needed, add another optimizer implementation; keep the driver simple.
     */
    """

    #: @brief 优化器名字 / Optimizer name.
    #: @brief Optimizer name.
    name: str = "plain"

    #: @brief 版本号 / Version string.
    #: @brief Version string.
    version: str = "1.0.0"

    def optimize(
        self, module: IRModule, *, config: Mapping[str, JsonValue]
    ) -> IRModule:
        """
        /**
         * @brief 透传优化：不改变 IR，仅返回浅拷贝。
         *        Pass-through optimization: returns a shallow copy of IR.
         *
         * @param module
         *        输入 IRModule / Input IRModule.
         * @param config
         *        优化器配置（本实现忽略）/ Optimizer config (ignored by this implementation).
         *
         * @return
         *        输出 IRModule（浅拷贝）/ Output IRModule (shallow copy).
         */
        """
        if config:
            _LOG.debug(
                "plain optimizer: config is provided but ignored: keys=%s",
                list(config.keys()),
            )
        # Shallow copy to avoid accidental mutation by later stages.
        return dict(module)
