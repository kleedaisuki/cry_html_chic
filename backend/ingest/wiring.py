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

from __future__ import annotations

# Use package-relative imports so `Backend` can be used as a top-level package
from .utils.registry import Registry
# ============================================================
# Sources registry / 数据源注册表
# ============================================================

from .sources.interface import DataSource

#: Registry for all DataSource implementations.
#: 所有 DataSource 实现的注册表。
SOURCES: Registry = Registry(
    namespace="sources",
    base=DataSource,
)

#: Decorator / function for registering a DataSource.
#: 用于注册 DataSource 的装饰器 / 函数。
register_source = SOURCES.register


# ============================================================
# Caches registry / 缓存注册表
# ============================================================

from .cache.interface import PreprocessedCache, RawCache

#: Registry for all RawCache implementations.
#: 所有 RawCache 实现的注册表。
RAW_CACHES: Registry = Registry(
    namespace="raw_caches",
    base=RawCache,
)

#: Decorator / function for registering a RawCache.
#: 用于注册 RawCache 的装饰器 / 函数。
register_raw_cache = RAW_CACHES.register

#: Registry for all PreprocessedCache implementations.
#: 所有 PreprocessedCache 实现的注册表。
PREPROCESSED_CACHES: Registry = Registry(
    namespace="preprocessed_caches",
    base=PreprocessedCache,
)

#: Decorator / function for registering a PreprocessedCache.
#: 用于注册 PreprocessedCache 的装饰器 / 函数。
register_preprocessed_cache = PREPROCESSED_CACHES.register


# ============================================================
# Transform toolchain registries / Transform 工具链注册表
# ============================================================

from .transform.interface import BackendCompiler, FrontendCompiler, Optimizer

#: Registry for all FrontendCompiler implementations.
#: 所有 FrontendCompiler 实现的注册表。
FRONTENDS: Registry = Registry(
    namespace="frontends",
    base=FrontendCompiler,
)

#: Decorator / function for registering a FrontendCompiler.
#: 用于注册 FrontendCompiler 的装饰器 / 函数。
register_frontend = FRONTENDS.register

#: Registry for all Optimizer implementations.
#: 所有 Optimizer 实现的注册表。
OPTIMIZERS: Registry = Registry(
    namespace="optimizers",
    base=Optimizer,
)

#: Decorator / function for registering an Optimizer.
#: 用于注册 Optimizer 的装饰器 / 函数。
register_optimizer = OPTIMIZERS.register

#: Registry for all BackendCompiler implementations.
#: 所有 BackendCompiler 实现的注册表。
BACKENDS: Registry = Registry(
    namespace="backends",
    base=BackendCompiler,
)

#: Decorator / function for registering a BackendCompiler.
#: 用于注册 BackendCompiler 的装饰器 / 函数。
register_backend = BACKENDS.register
