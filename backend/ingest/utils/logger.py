"""
@brief 日志系统配置模块（支持 stdout/stderr 分流 + 微秒时间戳）
@brief Logging configuration module with stdout/stderr split and microsecond timestamps

使用方法 / Usage:
    from ingest.utils.logger import configure_logging, get_logger

    configure_logging(level="INFO", force=True)
    log = get_logger(__name__)
    log.info("hello")
    log.warning("warn")
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from typing import Optional


# -----------------------------------------------------------------------------
# Formatter
# -----------------------------------------------------------------------------


class _MicrosecondFormatter(logging.Formatter):
    """
    @brief 支持微秒时间戳的 Formatter（Windows 兼容）
    @brief Formatter with microsecond-precision timestamps (Windows compatible)
    """

    def formatTime(
        self, record: logging.LogRecord, datefmt: Optional[str] = None
    ) -> str:
        dt = datetime.fromtimestamp(record.created)
        if datefmt:
            return dt.strftime(datefmt)
        # fallback（一般不会走到）
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")


# -----------------------------------------------------------------------------
# Filters
# -----------------------------------------------------------------------------


class _MaxLevelFilter(logging.Filter):
    """
    @brief 限制最大日志等级的过滤器（用于 stdout）
    @brief Filter that allows records up to a maximum level (for stdout)
    """

    def __init__(self, max_level: int) -> None:
        super().__init__()
        self._max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self._max_level


# -----------------------------------------------------------------------------
# Handlers
# -----------------------------------------------------------------------------


class _EncodingSafeStreamHandler(logging.StreamHandler):
    """
    @brief Windows 友好的 StreamHandler（防止编码异常）
    @brief Windows-friendly StreamHandler (guards against encoding issues)
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            super().emit(record)
        except UnicodeEncodeError:
            msg = self.format(record)
            stream = self.stream
            stream.write(
                msg.encode(stream.encoding, errors="replace").decode(stream.encoding)
            )
            stream.write(self.terminator)
            self.flush()


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def configure_logging(
    *,
    level: str | int = "INFO",
    force: bool = False,
    stdout=sys.stdout,
    stderr=sys.stderr,
) -> None:
    """
    @brief 配置全局日志系统（stdout / stderr 分流）
    @brief Configure global logging with stdout/stderr split

    @param level 日志最低等级 / Minimum log level
    @param force 是否清空已有 handlers / Whether to reset existing handlers
    """
    lvl = logging.getLevelName(level) if isinstance(level, str) else level

    root = logging.getLogger()
    root.setLevel(lvl)

    if force:
        for h in list(root.handlers):
            root.removeHandler(h)

    formatter = _MicrosecondFormatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S.%f",
    )

    # --- stdout handler: <= INFO ---
    stdout_handler = _EncodingSafeStreamHandler(stream=stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.setLevel(lvl)
    stdout_handler.addFilter(_MaxLevelFilter(logging.INFO))

    # --- stderr handler: >= WARNING ---
    stderr_handler = _EncodingSafeStreamHandler(stream=stderr)
    stderr_handler.setFormatter(formatter)
    stderr_handler.setLevel(logging.WARNING)

    root.addHandler(stdout_handler)
    root.addHandler(stderr_handler)


def set_log_level(level: str | int) -> None:
    """
    @brief 动态调整全局日志等级（不会破坏 stdout/stderr 分流）
    @brief Dynamically update global log level without breaking stream split
    """
    lvl = logging.getLevelName(level) if isinstance(level, str) else level
    root = logging.getLogger()
    root.setLevel(lvl)

    for h in root.handlers:
        # stdout handler 跟随全局等级
        if any(isinstance(f, _MaxLevelFilter) for f in h.filters):
            h.setLevel(lvl)
        # stderr handler 永远保持 WARNING+
        else:
            h.setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    @brief 获取模块级 logger
    @brief Get a module-level logger
    """
    return logging.getLogger(name)
