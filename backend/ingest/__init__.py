"""
/**
 * @file __init__.py
 * @brief ingest 包标识与元信息（无副作用）/ Package marker & metadata (no side effects).
 *
 * 约束 / Constraints:
 * - 不在此处 import 子模块，避免 import-time 副作用与循环依赖。
 *   Do NOT import submodules here to avoid import-time side effects and circular imports.
 * - 不做注册（registry），不做扫描（auto-discovery）。
 *   No registry side effects, no auto-discovery.
 */
"""

from __future__ import annotations

__all__: list[str] = []

# 给项目留一个稳定版本号入口（不依赖 import 子模块）
# stable version hook without importing submodules.
__version__: str = "0.1.0"
