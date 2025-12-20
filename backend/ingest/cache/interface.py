# backend/ingest/cache/interface.py
from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    Iterable,
    Mapping,
    Protocol,
    Sequence,
    Union,
    runtime_checkable,
)

# ---------------------------
# JSON type (shared utility)
# ---------------------------

JsonValue = Union[
    None,
    bool,
    int,
    float,
    str,
    Sequence["JsonValue"],
    Mapping[str, "JsonValue"],
]


# ---------------------------
# Error types
# ---------------------------


class CacheError(RuntimeError):
    """
    @brief 缓存系统基类异常 / Base exception for cache subsystem.
    """


class CacheMiss(CacheError):
    """
    @brief 缓存缺失 / Cache miss (no such run/artifact).
    """


class CorruptedCache(CacheError):
    """
    @brief 缓存损坏 / Corrupted cache (invalid meta, partial write, checksum mismatch, etc.).
    """


class ConcurrentWrite(CacheError):
    """
    @brief 并发写冲突 / Concurrent write conflict (same run key being written).
    """


# ---------------------------
# Identity / keys
# ---------------------------


@dataclass(frozen=True)
class CacheKey:
    """
    @brief 缓存键（定位一次 pipeline 运行）/ Cache key (locate one pipeline run).
    @note
    - 这是“目录名/路径”的抽象，不把路径细节泄露给上层。
      Abstracts directory naming; hides path details from callers.
    - content_hash 应该稳定地由“输入配置 + Source provenance +（可选）代码版本”等生成。
      content_hash should be derived stably from config + provenance (+ optional code version).
    """

    config_name: str
    content_hash: str
    fetched_at_iso: str | None = (
        None
    )


# ---------------------------
# Raw cache meta (aligned with source/interface.py)
# ---------------------------


@dataclass(frozen=True)
class RawCacheMeta:
    """
    @brief Raw 缓存元信息（对齐 RawArtifact 字段）/ Raw cache metadata (aligned with RawArtifact).
    @note
    - 这里刻意保留 meta: Dict[str, str] 这种“扁平字符串字典”，以保持 provenance 简洁稳定；
      Keep meta as Dict[str,str] to stay simple & stable for provenance.
    - cache_path 在 Source 层是“产物写到了哪里”；在 Cache 层它更像“相对路径/句柄”；
      At Source layer, cache_path is where it was written; at Cache layer it can be a relative path/handle.
    """

    source_name: str
    fetched_at_iso: str
    content_type: str
    encoding: str
    cache_path: str
    meta: Dict[str, str]


@dataclass(frozen=True)
class RawCacheRecord:
    """
    @brief Raw 缓存记录（payload + meta）/ Raw cache record (payload + meta).
    @note
    - payload 统一用 bytes：不把 JSON/CSV/二进制格式写死在接口里（We don't break userspace）。
      Use bytes payload to avoid locking into JSON/CSV/etc (We don't break userspace).
    """

    payload: bytes
    meta: RawCacheMeta


# ---------------------------
# Preprocessed cache meta
# ---------------------------


@dataclass(frozen=True)
class PreprocessedCacheMeta:
    """
    @brief Preprocessed 缓存元信息 / Preprocessed cache metadata.
    @note
    - preprocessed 产物通常是多个命名文件（例如 *.js），所以 meta 与 manifest 分离更干净。
      Preprocessed usually has multiple named artifacts, so separate meta and manifest.
    """

    built_at_iso: str
    schema_version: int
    # 允许挂载额外 provenance（例如 transform name/version、输入 raw 的 key、统计信息等）
    # Allow extra provenance (e.g., transform name/version, input raw key, stats).
    extra: Mapping[str, JsonValue]


@dataclass(frozen=True)
class ArtifactManifest:
    """
    @brief 成品清单（文件名集合）/ Artifact manifest (set of artifact names).
    """

    files: Sequence[str]


# ---------------------------
# Protocols (behavior contracts)
# ---------------------------


@runtime_checkable
class RawCache(Protocol):
    """
    @brief Raw 缓存纯接口 / Raw cache protocol (behavior contract only).
    @note
    - 只定义“可缓存/可追溯”的行为，不规定目录结构、原子写、锁等实现细节。
      Only defines cache/provenance behaviors; no constraints on layout/atomic write/locking impl.
    """

    def has(self, key: CacheKey) -> bool:
        """
        @brief 是否存在该 key 的 raw 缓存 / Whether raw cache exists for key.
        """
        ...

    def save(self, key: CacheKey, record: RawCacheRecord) -> None:
        """
        @brief 保存 raw 缓存（payload + meta）/ Save raw cache (payload + meta).
        @param key 缓存键 / Cache key.
        @param record payload + meta / payload + meta.
        @throw ConcurrentWrite 并发写冲突 / concurrent write conflict.
        """
        ...

    def load(self, key: CacheKey) -> RawCacheRecord:
        """
        @brief 读取 raw 缓存（payload + meta）/ Load raw cache (payload + meta).
        @param key 缓存键 / Cache key.
        @return RawCacheRecord / RawCacheRecord.
        @throw CacheMiss 缓存不存在 / cache missing.
        @throw CorruptedCache 缓存损坏 / corrupted cache.
        """
        ...

    def iter_keys(self, config_name: str | None = None) -> Iterable[CacheKey]:
        """
        @brief 枚举缓存键 / Iterate cache keys.
        @param config_name 可选过滤 / optional filter.
        @return CacheKey 迭代器 / Iterable of CacheKey.
        """
        ...


@runtime_checkable
class PreprocessedCache(Protocol):
    """
    @brief Preprocessed 缓存纯接口 / Preprocessed cache protocol (behavior contract only).
    @note
    - preprocessed 是“多个命名产物 + meta”，适合用 manifest 做稳定枚举。
      Preprocessed is "multiple named artifacts + meta", manifest provides stable enumeration.
    """

    def has(self, key: CacheKey) -> bool:
        """
        @brief 是否存在该 key 的 preprocessed 缓存 / Whether preprocessed cache exists for key.
        """
        ...

    def save(
        self,
        key: CacheKey,
        artifacts: Mapping[str, bytes],
        meta: PreprocessedCacheMeta,
    ) -> None:
        """
        @brief 保存 preprocessed 缓存（多文件 + meta）/ Save preprocessed cache (artifacts + meta).
        @param key 缓存键 / Cache key.
        @param artifacts 文件名->内容 / name->content.
        @param meta 元信息 / metadata.
        @throw ConcurrentWrite 并发写冲突 / concurrent write conflict.
        """
        ...

    def load_manifest(self, key: CacheKey) -> ArtifactManifest:
        """
        @brief 读取成品清单 / Load manifest.
        @param key 缓存键 / Cache key.
        @return ArtifactManifest / ArtifactManifest.
        @throw CacheMiss 缓存不存在 / cache missing.
        @throw CorruptedCache 缓存损坏 / corrupted cache.
        """
        ...

    def load_artifact(self, key: CacheKey, name: str) -> bytes:
        """
        @brief 读取单个成品文件 / Load one artifact by name.
        @param key 缓存键 / Cache key.
        @param name 文件名 / artifact name.
        @return 文件内容 / artifact bytes.
        @throw CacheMiss 缓存或文件不存在 / cache or artifact missing.
        @throw CorruptedCache 缓存损坏 / corrupted cache.
        """
        ...

    def read_meta(self, key: CacheKey) -> PreprocessedCacheMeta:
        """
        @brief 读取 preprocessed 元信息 / Read preprocessed metadata.
        @param key 缓存键 / Cache key.
        @return PreprocessedCacheMeta / PreprocessedCacheMeta.
        @throw CacheMiss 缓存不存在 / cache missing.
        @throw CorruptedCache 缓存损坏 / corrupted cache.
        """
        ...

    def iter_keys(self, config_name: str | None = None) -> Iterable[CacheKey]:
        """
        @brief 枚举缓存键 / Iterate cache keys.
        @param config_name 可选过滤 / optional filter.
        @return CacheKey 迭代器 / Iterable of CacheKey.
        """
        ...
