# backend/ingest/utils/logger.py
"""
/**
 * @brief 项目统一日志工具（logging）：get_logger(__name__) 获取 logger；
 *        stdout/stderr 分流；支持全局等级过滤；并处理 IO 编码安全输出。
 *        Project unified logging utility (logging): get_logger(__name__) for module logger;
 *        split stdout/stderr; global level filtering; safe IO encoding output.
 */
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from typing import Optional, TextIO


# ============================================================
# 全局状态 / Global state
# ============================================================

_CONFIGURED: bool = False
_ROOT_LEVEL: int = logging.INFO

_STDOUT_HANDLER: Optional[logging.Handler] = None
_STDERR_HANDLER: Optional[logging.Handler] = None


# ============================================================
# 编码处理 / Encoding handling
# ============================================================


def _stream_encoding(stream: TextIO) -> str:
    """
    /**
     * @brief 获取文本流编码（优先 stream.encoding），缺失则回退到 UTF-8。
     *        Get text stream encoding (prefer stream.encoding), fallback to UTF-8.
     *
     * @param stream
     *        文本流对象 / Text stream object.
     * @return
     *        编码名称 / Encoding name.
     */
    """
    enc = getattr(stream, "encoding", None)
    return enc or "utf-8"


class _EncodingSafeStreamHandler(logging.StreamHandler):
    """
    /**
     * @brief 编码安全 StreamHandler：确保日志文本可被目标流编码输出，避免 UnicodeEncodeError。
     *        Encoding-safe StreamHandler: ensures log text is encodable by target stream.
     *
     * @note
     *        使用 backslashreplace 保证不可编码字符以 \\uXXXX 形式可见（不丢信息）。
     *        Uses backslashreplace so unencodable chars become \\uXXXX (no silent loss).
     */
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            stream = self.stream
            enc = _stream_encoding(stream)

            safe_msg = msg.encode(enc, errors="backslashreplace").decode(
                enc, errors="strict"
            )

            stream.write(safe_msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


class _MaxLevelFilter(logging.Filter):
    """
    /**
     * @brief 过滤器：只允许 <= max_level 的日志通过（用于把 WARNING 及以上挡去 stderr）。
     *        Filter: allows records with level <= max_level (used to route below WARNING to stdout).
     *
     * @param max_level
     *        最大级别（包含） / Maximum level (inclusive).
     */
    """

    def __init__(self, max_level: int) -> None:
        super().__init__()
        self._max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self._max_level


# ============================================================
# 配置 / Configuration
# ============================================================


@dataclass
class LoggingConfig:
    """
    /**
     * @brief 日志配置数据类：stdout/stderr 流、全局最小等级、format、时间格式。
     *        Logging config dataclass: stdout/stderr streams, global min level, format, date format.
     */
    """

    level: int = logging.INFO
    stdout: TextIO = sys.stdout
    stderr: TextIO = sys.stderr
    fmt: str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    datefmt: str = "%Y-%m-%d %H:%M:%S"


def _parse_level(level: str | int | None) -> int:
    """
    /**
     * @brief 将 level（字符串或整数）解析为 logging level。
     *        Parse level (str or int) into logging level.
     *
     * @param level
     *        级别 / Level.
     * @return
     *        logging 级别整数 / logging level int.
     */
    """
    if level is None:
        return _ROOT_LEVEL
    if isinstance(level, int):
        return level

    s = str(level).strip().upper()
    mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
        "FATAL": logging.CRITICAL,
    }
    return mapping.get(s, _ROOT_LEVEL)


def configure_logging(
    *,
    level: str | int = logging.INFO,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
    force: bool = False,
) -> None:
    """
    /**
     * @brief 配置根日志：stdout/stderr 分流 + 全局等级过滤 + 编码安全输出。
     *        Configure root logging: split stdout/stderr + global level filtering + encoding-safe output.
     *
     * @param level
     *        全局最小日志等级（过滤低优先级） / Global minimum log level (filters low priority).
     * @param stdout
     *        标准输出流（DEBUG/INFO 默认走这里） / Stdout stream (DEBUG/INFO go here).
     * @param stderr
     *        标准错误流（WARNING+ 默认走这里） / Stderr stream (WARNING+ go here).
     * @param force
     *        是否强制重新配置（替换已有 handler） / Force reconfigure (replace existing handlers).
     */
    """
    global _CONFIGURED, _ROOT_LEVEL, _STDOUT_HANDLER, _STDERR_HANDLER

    lvl = _parse_level(level)
    cfg = LoggingConfig(level=lvl, stdout=stdout, stderr=stderr)

    root = logging.getLogger()
    root.setLevel(lvl)

    # 避免重复 handler
    if _CONFIGURED and not force:
        # 已经配置过，只同步等级即可
        set_log_level(lvl)
        return

    # 清理旧 handler（无论是否 force，都确保只有我们控制的两路）
    for h in list(root.handlers):
        root.removeHandler(h)

    formatter = logging.Formatter(fmt=cfg.fmt, datefmt=cfg.datefmt)

    # stdout：只收 <= INFO 的日志（也就是 DEBUG / INFO）
    stdout_handler = _EncodingSafeStreamHandler(stream=cfg.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.setLevel(lvl)  # 全局最小等级过滤（在 handler 级别再过一遍）
    stdout_handler.addFilter(_MaxLevelFilter(logging.INFO))

    # stderr：收 >= WARNING 的日志（WARNING / ERROR / CRITICAL）
    stderr_handler = _EncodingSafeStreamHandler(stream=cfg.stderr)
    stderr_handler.setFormatter(formatter)
    stderr_handler.setLevel(lvl)

    root.addHandler(stdout_handler)
    root.addHandler(stderr_handler)

    _STDOUT_HANDLER = stdout_handler
    _STDERR_HANDLER = stderr_handler
    _ROOT_LEVEL = lvl
    _CONFIGURED = True


def set_log_level(level: str | int) -> None:
    """
    /**
     * @brief 动态设置全局最小日志等级，用于过滤低优先级日志。
     *        Dynamically set global minimum log level to filter low-priority logs.
     *
     * @param level
     *        级别（如 "INFO" / "DEBUG" / logging.INFO 等） / Level (e.g. "INFO"/"DEBUG"/logging.INFO).
     */
    """
    global _ROOT_LEVEL
    lvl = _parse_level(level)
    _ROOT_LEVEL = lvl

    root = logging.getLogger()
    root.setLevel(lvl)

    # 同步到两个 handler（若已配置）
    if _STDOUT_HANDLER is not None:
        _STDOUT_HANDLER.setLevel(lvl)
    if _STDERR_HANDLER is not None:
        _STDERR_HANDLER.setLevel(lvl)


def get_logger(name: str) -> logging.Logger:
    """
    /**
     * @brief 获取模块 logger：建议模块内通过 get_logger(__name__) 使用。
     *        Get module logger: recommended usage get_logger(__name__) inside each module.
     *
     * @param name
     *        logger 名称（通常传 __name__） / Logger name (usually __name__).
     * @return
     *        logging.Logger 实例 / logging.Logger instance.
     *
     * @note
     *        若尚未 configure_logging，会用默认 INFO 并自动完成 stdout/stderr 分流配置。
     *        If not configured, auto-configures with default INFO and stdout/stderr split.
     */
    """
    if not _CONFIGURED:
        configure_logging(
            level=logging.INFO, stdout=sys.stdout, stderr=sys.stderr, force=False
        )
    return logging.getLogger(name)
