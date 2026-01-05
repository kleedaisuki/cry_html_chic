"""
@file hashlib.py
@brief CacheKey 派生函数 / CacheKey derivation helpers.

本模块定义 cache domain 内“如何从 record + config 推导 CacheKey”的
唯一权威实现，必须满足确定性（deterministic）与可复现性（replayable）。
"""

from __future__ import annotations

import hashlib
import json
from typing import Mapping

from ingest.cache.interface import CacheKey, RawCacheRecord


def make_cache_key(
    *,
    config_name: str,
    record: RawCacheRecord,
    extra_identity: Mapping[str, str] | None = None,
) -> CacheKey:
    """
    @brief 从 RawCacheRecord 与配置派生 CacheKey
           Derive CacheKey from RawCacheRecord and config.

    @param config_name:
        配置 profile 名称 / Config profile name.
    @param record:
        原始缓存记录（payload + meta）/ Raw cache record.
    @param extra_identity:
        额外参与 identity 的稳定字段（可选）/ Optional extra identity fields.

    @return CacheKey:
        稳定、可复现的缓存键 / Stable and replayable cache key.

    @note
    - fetched_at_iso **不参与 content_hash**，否则会导致 key 漂移。
    - payload 建议 hash，但不要直接拼 bytes（避免巨大内存占用）。
    """

    h = hashlib.sha256()

    # 1. config identity
    h.update(config_name.encode("utf-8"))

    # 2. payload identity
    h.update(hashlib.sha256(record.payload).digest())

    # 3. provenance meta（必须是稳定字段）
    if record.meta.meta:
        canonical_meta = json.dumps(
            record.meta.meta,
            sort_keys=True,
            separators=(",", ":"),
        )
        h.update(canonical_meta.encode("utf-8"))

    # 4. optional extension point
    if extra_identity:
        canonical_extra = json.dumps(
            extra_identity,
            sort_keys=True,
            separators=(",", ":"),
        )
        h.update(canonical_extra.encode("utf-8"))

    return CacheKey(
        config_name=config_name,
        content_hash=h.hexdigest(),
        fetched_at_iso=record.meta.fetched_at_iso,
    )
