# backend/ingest/sources/new_interface.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import (
    Any,
    Dict,
    Iterable,
    Mapping,
    Sequence,
    Union,
)

from ingest.cache.interface import RawCacheMeta, RawCacheRecord


JsonValue = Union[
    None, bool, int, float, str, Sequence["JsonValue"], Mapping[str, "JsonValue"]
]

SourceConfig = Mapping[str, Any]


class DataSource(ABC):
    """
    /**
     * @brief V2 数据源接口：封装 config，fetch 直接产出 RawCacheRecord / V2 data source interface: config is encapsulated; fetch yields RawCacheRecord.
     *
     * 设计动机 / Motivation:
     * - 封装性（Encapsulation）：不再让应用层重复注入 config（避免双通道状态）。
     *   Encapsulation: stop re-injecting config from the app layer (avoid dual-channel state).
     * - 对齐缓存 IR（Cache IR alignment）：Source 输出与 RawCacheRecord 对齐（payload + meta），消灭 staging file 的双 IO 路径。
     *   Align to cache IR: Source outputs RawCacheRecord (payload + meta), eliminating the double-IO staging path.
     *
     * @note
     * - Source 只负责“抓取原始数据并描述它”，不负责语义统一；语义统一属于 transform。
     *   Source only fetches raw and describes it; semantic unification belongs to transform.
     * - payload 一律 bytes（或未来扩展为 stream），cache 层不解析格式。
     *   Payload is bytes (or extensible to streams); cache layer does not parse formats.
     */
    """

    @classmethod
    @abstractmethod
    def name(cls) -> str:
        """
        /**
         * @brief 数据源稳定名称（用于 registry key）/ Stable source name (registry key).
         */
        """
        ...

    @classmethod
    @abstractmethod
    def describe(cls) -> Dict[str, str]:
        """
        /**
         * @brief 数据源静态描述（用于 provenance）/ Static description for provenance.
         *
         * @return
         *   字符串字典（稳定、可序列化）/ A stable, serializable dict.
         */
        """
        ...

    @abstractmethod
    def validate(self) -> None:
        """
        /**
         * @brief 校验 self.config（失败抛异常）/ Validate self.config (raise on failure).
         */
        """
        ...

    @abstractmethod
    def fetch(self) -> Iterable[RawCacheRecord]:
        """
        /**
         * @brief 拉取数据并产出 RawCacheRecord 流 / Fetch data and yield a stream of RawCacheRecord.
         *
         * @return
         *   RawCacheRecord 迭代器 / Iterable of RawCacheRecord.
         *
         * @note
         * - fetch 内部可包含分页、重试、限速、二阶段 discovery 等任意实现。
         *   Any internal impl is allowed: paging, retries, rate limiting, multi-stage discovery, etc.
         */
        """
        ...


def make_raw_cache_meta(
    *,
    source_name: str,
    fetched_at_iso: str,
    content_type: str,
    encoding: str,
    cache_path: str = "",
    meta: Mapping[str, str] | None = None,
) -> RawCacheMeta:
    """
    /**
     * @brief 构造 RawCacheMeta 的小工具 / Small helper to build RawCacheMeta.
     *
     * @param source_name
     *   数据源名称 / Source name.
     * @param fetched_at_iso
     *   抓取时间 ISO 字符串 / Fetch time ISO string.
     * @param content_type
     *   MIME 类型 / MIME type.
     * @param encoding
     *   编码（例如 utf-8）/ Encoding (e.g., utf-8).
     * @param cache_path
     *   可选：来源侧路径（若你仍想保留 provenance 指针）/ Optional: source-side path pointer (if you still want provenance).
     * @param meta
     *   额外 provenance 字段 / Extra provenance fields.
     * @return
     *   RawCacheMeta / RawCacheMeta.
     *
     * @note
     * - 这里保留 cache_path 是为了兼容你现有 meta 字段结构；若你决定彻底去掉 staging/path，
     *   可以在后续版本把 cache_path 固定为空字符串并逐步移除该参数。
     *   cache_path is kept for compatibility with existing meta structure; you may phase it out later.
     */
    """
    # RawCacheMeta 的字段以 ingest.cache.interface 为准；
    # 这里采用“按字段名构造”的方式，要求 RawCacheMeta 与这些字段同名。
    # If RawCacheMeta differs, adjust here accordingly.
    return RawCacheMeta(
        source_name=source_name,
        fetched_at_iso=fetched_at_iso,
        content_type=content_type,
        encoding=encoding,
        cache_path=cache_path,
        meta=dict(meta or {}),
    )


def make_raw_cache_record(*, payload: bytes, meta: RawCacheMeta) -> RawCacheRecord:
    """
    /**
     * @brief 构造 RawCacheRecord / Build a RawCacheRecord.
     *
     * @param payload
     *   原始字节 / Raw bytes.
     * @param meta
     *   RawCacheMeta / RawCacheMeta.
     * @return
     *   RawCacheRecord / RawCacheRecord.
     */
    """
    return RawCacheRecord(payload=payload, meta=meta)
