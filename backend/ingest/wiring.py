"""
/**
 * @file wiring.py
 * @brief Ingest 系统的注册表装配点 / Registry wiring for ingest system.
 *
 * 本模块只做一件事：
 * - 声明 ingest 系统中的所有扩展点（extension points）
 * - 为每个扩展点实例化唯一的 Registry
 * - 暴露标准的注册入口（decorator / function）
 *
 * ⚠️ 注意：
 * - 本模块不 import 任何具体实现（如 datamall / raw cache / cli commands）
 * - 实现模块通过 import + decorator 进行显式注册
 */
"""

from ingest.utils.registry import Registry

# ============================================================
# Sources registry / 数据源注册表
# ============================================================

from ingest.sources.interface import DataSource

#: Registry for all DataSource implementations.
#: 所有 DataSource 实现的注册表。
SOURCES: Registry = Registry(
    name="sources",
    base=DataSource,
)

#: Decorator / function for registering a DataSource.
#: 用于注册 DataSource 的装饰器 / 函数。
register_source = SOURCES.register
