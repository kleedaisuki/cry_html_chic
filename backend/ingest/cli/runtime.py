from __future__ import annotations

"""
/**
 * @file runtime.py
 * @brief Plugin import helper.
 *
 * 本模块的唯一职责：
 * - 根据配置文件，确保所有声明的插件模块被 import
 * - 从而触发插件的注册副作用（写入全局 registry）
 *
 * 注意：
 * - Registry 是全局一致的
 * - 本模块不管理 registry
 * - 本模块不管理任何运行时对象或生命周期
 * - task 不应直接 import 插件
 *
 * This module exists solely to make plugin imports explicit.
 */
"""

import importlib
import threading
from typing import Iterable

from ingest.utils.logger import get_logger
from .configs import LoadedConfig

_LOG = get_logger(__name__)

# 进程级去重，避免重复 import
_import_lock = threading.Lock()
_imported_plugins: set[str] = set()


def ensure_plugins_loaded(loaded: LoadedConfig) -> None:
    """
    @brief 根据配置确保插件被 import
           Ensure all plugins declared in config are imported.

    @param loaded
           LoadedConfig（已解析配置）
    """
    _ensure_modules_imported(loaded.config.plugins)


def _ensure_modules_imported(modules: Iterable[str]) -> None:
    """
    @brief import 一组模块名（幂等）
           Import a sequence of module names (idempotent).
    """
    with _import_lock:
        for module_name in modules:
            if module_name in _imported_plugins:
                continue

            _LOG.info("import plugin: %s", module_name)
            importlib.import_module(module_name)
            _imported_plugins.add(module_name)
