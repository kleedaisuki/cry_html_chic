# backend/ingest/cache/raw.py
from __future__ import annotations

"""
/**
 * @brief Raw 缓存的文件系统实现 / Filesystem implementation of Raw cache.
 *
 * 设计目标 / Design goals:
 * - 只依赖标准库，保持实现透明干净 / Standard library only, keep it transparent & clean.
 * - payload 一律 bytes，不在 cache 层解析格式 / Payload is always bytes; no parsing at cache layer.
 * - 带完整性校验（SHA-256）与“近似原子写”（temp dir -> rename） / Integrity via SHA-256 and atomic-ish save (temp dir -> rename).
 * - 目录名对 Windows 友好：ISO 时间戳会被“路径安全化” / Windows-friendly dir naming: sanitize ISO timestamp.
 */
"""

import hashlib
import json
import os
import secrets
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional

from ingest.utils.logger import get_logger
from .interface import (
    CacheKey,
    CacheMiss,
    ConcurrentWrite,
    CorruptedCache,
    RawCache,
    RawCacheMeta,
    RawCacheRecord,
)
from ingest.wiring import register_raw_cache

_LOG = get_logger(__name__)


# ============================================================
# Helpers / 工具函数
# ============================================================


def _sha256_hex(data: bytes) -> str:
    """
    /**
     * @brief 计算 bytes 的 SHA-256 十六进制摘要 / Compute SHA-256 hex digest for bytes.
     *
     * @param data
     *        原始字节 / Raw bytes.
     * @return
     *        sha256 hex / SHA-256 hex string.
     */
    """
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _safe_ts_for_path(fetched_at_iso: str) -> str:
    """
    /**
     * @brief 将 ISO 时间戳变为路径安全形式（Windows 兼容）/ Make ISO timestamp path-safe (Windows-friendly).
     *
     * @param fetched_at_iso
     *        ISO 时间戳（可能含 ':' '.' 'Z' 等）/ ISO timestamp (may contain ':' '.' 'Z', etc.).
     * @return
     *        路径安全字符串 / Path-safe string.
     *
     * @note
     *        Windows 文件名不允许 ':'，因此做替换。
     *        Windows forbids ':' in file names, so we replace it.
     */
    """
    # 保守策略：移除 ':' 与 '.'，其余保留（例如 'T' 'Z' '-'）
    # Conservative: remove ':' and '.', keep others.
    return fetched_at_iso.replace(":", "").replace(".", "")


def _read_json(path: Path) -> Dict[str, object]:
    """
    /**
     * @brief 读取 JSON 文件到 dict / Read a JSON file into dict.
     *
     * @param path
     *        JSON 文件路径 / JSON file path.
     * @return
     *        dict / dict.
     * @throw CorruptedCache
     *        JSON 无法解析 / JSON parse error.
     */
    """
    try:
        text = path.read_text(encoding="utf-8")
        obj = json.loads(text)
        if not isinstance(obj, dict):
            raise CorruptedCache(f"meta.json must be an object: {path}")
        return obj
    except CorruptedCache:
        raise
    except Exception as e:
        raise CorruptedCache(f"failed to read json: {path} ({e})") from e


def _write_json_atomic(path: Path, obj: Dict[str, object]) -> None:
    """
    /**
     * @brief 原子写入 JSON（同目录 tmp 文件 -> replace）/ Atomic-ish JSON write (tmp -> replace).
     *
     * @param path
     *        目标路径 / Target path.
     * @param obj
     *        JSON 对象 / JSON object.
     */
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{secrets.token_hex(8)}")
    data = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    tmp.write_text(data, encoding="utf-8")
    # 文件 replace 在同一文件系统内是原子的 / os.replace is atomic for files on same filesystem.
    os.replace(tmp, path)


# ============================================================
# Filesystem Raw Cache / 文件系统 RawCache
# ============================================================


@register_raw_cache("fs_raw")
class FileSystemRawCache(RawCache):
    """
    /**
     * @brief 基于目录结构的 RawCache 实现 / RawCache implementation backed by filesystem directories.
     *
     * Layout / 目录结构:
     *   <base_dir>/
     *     <run_dir>/                       # 例如: 20251220T155900Z-config-abcdef
     *       meta.json                      # RawCacheMeta + 校验字段
     *       payload.bin                    # 原始 bytes
     *
     * run_dir naming / 目录命名:
     *   "<safe_ts>-<config_name>-<content_hash>"
     *
     * @note
     *   - 为避免从目录名反推 ISO 时间戳带来的不确定性，iter_keys 会优先读 meta.json 的 fetched_at_iso。
     *     To avoid ambiguity, iter_keys reads fetched_at_iso from meta.json rather than parsing dir name.
     */
    """

    _META_FILE = "meta.json"
    _PAYLOAD_FILE = "payload.bin"

    def __init__(self, base_dir: str | Path) -> None:
        """
        /**
         * @brief 创建 RawCache（文件系统）/ Create filesystem RawCache.
         *
         * @param base_dir
         *        raw 缓存根目录（例如 data/raw）/ Raw cache root directory (e.g., data/raw).
         */
        """
        self._base_dir = Path(base_dir)

    @property
    def base_dir(self) -> Path:
        """
        /**
         * @brief 获取根目录 / Get base directory.
         */
        """
        return self._base_dir

    # ----------------------------
    # Protocol methods
    # ----------------------------

    def has(self, key: CacheKey) -> bool:
        """
        /**
         * @brief 是否存在该 key 的 raw 缓存 / Whether raw cache exists for key.
         */
        """
        try:
            run_dir = self._resolve_run_dir(key)
        except CacheMiss:
            return False
        meta_path = run_dir / self._META_FILE
        payload_path = run_dir / self._PAYLOAD_FILE
        return meta_path.is_file() and payload_path.is_file()

    def save(self, key: CacheKey, record: RawCacheRecord) -> None:
        """
        /**
         * @brief 保存 raw 缓存（payload + meta）/ Save raw cache (payload + meta).
         *
         * @param key
         *        缓存键 / Cache key.
         * @param record
         *        payload + meta / payload + meta.
         * @throw ConcurrentWrite
         *        并发写冲突 / concurrent write conflict.
         */
        """
        # 统一决定本次 run 的 fetched_at_iso：
        # - 优先用 key.fetched_at_iso
        # - 若 key 未提供，则用 record.meta.fetched_at_iso（更贴近“真实抓取时间”）
        fetched_at_iso = key.fetched_at_iso or record.meta.fetched_at_iso
        if not fetched_at_iso:
            raise ValueError(
                "CacheKey.fetched_at_iso is None and record.meta.fetched_at_iso is empty"
            )

        # 若 key.fetched_at_iso 给了但与 record.meta 不一致：这是上层逻辑错误，直接拒绝
        if (
            key.fetched_at_iso is not None
            and key.fetched_at_iso != record.meta.fetched_at_iso
        ):
            raise ValueError(
                "CacheKey.fetched_at_iso must match record.meta.fetched_at_iso "
                f"(key={key.fetched_at_iso}, meta={record.meta.fetched_at_iso})"
            )

        final_dir = self._run_dir_from_parts(
            config_name=key.config_name,
            content_hash=key.content_hash,
            fetched_at_iso=fetched_at_iso,
        )

        # 并发写/重复写：目录已存在视为冲突（也可理解为幂等，但接口说 throw ConcurrentWrite）
        if final_dir.exists():
            raise ConcurrentWrite(f"raw cache already exists: {final_dir}")

        tmp_dir = self._base_dir / (
            final_dir.name + f".tmp-{os.getpid()}-{secrets.token_hex(8)}"
        )
        tmp_dir.mkdir(parents=True, exist_ok=False)

        try:
            payload_path = tmp_dir / self._PAYLOAD_FILE
            meta_path = tmp_dir / self._META_FILE

            payload = record.payload
            digest = _sha256_hex(payload)

            # 写 payload（文件级别 replace 不需要；tmp_dir 里直接写即可）
            payload_path.write_bytes(payload)

            # meta.json：在 RawCacheMeta 的基础上附加校验字段（cache 层自用）
            meta_obj: Dict[str, object] = {
                "version": 1,
                "checksum": {"algo": "sha256", "hex": digest},
                "size_bytes": len(payload),
                "raw": asdict(record.meta),
                # 冗余存一份 key（便于 debug）
                "key": {
                    "config_name": key.config_name,
                    "content_hash": key.content_hash,
                    "fetched_at_iso": fetched_at_iso,
                },
                # 也明确 payload 文件名（即使 RawCacheMeta.cache_path 可能是别的含义）
                "payload_file": self._PAYLOAD_FILE,
            }
            _write_json_atomic(meta_path, meta_obj)

            # temp -> final（同一文件系统内 rename 基本原子）
            # Windows 下 rename 目录也可用（同盘）。
            final_dir.parent.mkdir(parents=True, exist_ok=True)
            os.rename(tmp_dir, final_dir)

            _LOG.info(
                "raw cache saved: dir=%s size=%d sha256=%s",
                str(final_dir),
                len(payload),
                digest,
            )

        except FileExistsError as e:
            # final_dir 在 rename 瞬间出现：典型并发写
            raise ConcurrentWrite(f"concurrent write: {final_dir}") from e
        except ConcurrentWrite:
            raise
        except Exception as e:
            raise CorruptedCache(
                f"failed to save raw cache into {final_dir}: {e}"
            ) from e
        finally:
            # 若失败且 tmp_dir 仍在，清理
            if tmp_dir.exists():
                try:
                    shutil.rmtree(tmp_dir)
                except Exception:
                    # 清理失败不应吞掉主异常，但这里在 finally，最多打日志
                    _LOG.warning("failed to cleanup tmp dir: %s", str(tmp_dir))

    def load(self, key: CacheKey) -> RawCacheRecord:
        """
        /**
         * @brief 读取 raw 缓存（payload + meta）/ Load raw cache (payload + meta).
         *
         * @param key
         *        缓存键 / Cache key.
         * @return
         *        RawCacheRecord / RawCacheRecord.
         * @throw CacheMiss
         *        缓存不存在 / cache missing.
         * @throw CorruptedCache
         *        缓存损坏 / corrupted cache.
         */
        """
        run_dir = self._resolve_run_dir(key)
        meta_path = run_dir / self._META_FILE
        payload_path = run_dir / self._PAYLOAD_FILE

        if not meta_path.is_file() or not payload_path.is_file():
            raise CacheMiss(f"raw cache missing files: {run_dir}")

        meta_obj = _read_json(meta_path)

        # 校验 meta.json 格式
        try:
            checksum = meta_obj.get("checksum")
            if not isinstance(checksum, dict):
                raise CorruptedCache(f"invalid checksum field: {meta_path}")
            algo = checksum.get("algo")
            hex_digest = checksum.get("hex")
            if (
                algo != "sha256"
                or not isinstance(hex_digest, str)
                or len(hex_digest) < 32
            ):
                raise CorruptedCache(f"invalid checksum content: {meta_path}")

            raw_meta_obj = meta_obj.get("raw")
            if not isinstance(raw_meta_obj, dict):
                raise CorruptedCache(f"invalid raw meta field: {meta_path}")

            # 必填字段检查（RawCacheMeta）
            required = [
                "source_name",
                "fetched_at_iso",
                "content_type",
                "encoding",
                "cache_path",
                "meta",
            ]
            for k in required:
                if k not in raw_meta_obj:
                    raise CorruptedCache(f"raw meta missing '{k}': {meta_path}")

            if not isinstance(raw_meta_obj["meta"], dict):
                raise CorruptedCache(f"raw meta 'meta' must be object: {meta_path}")

            # 构建 RawCacheMeta（meta: Dict[str,str]）
            # 这里做强制 str 化，避免 JSON 里误写为非 str
            meta_flat: Dict[str, str] = {}
            for mk, mv in raw_meta_obj["meta"].items():
                if not isinstance(mk, str):
                    raise CorruptedCache(
                        f"raw meta 'meta' has non-str key: {meta_path}"
                    )
                if not isinstance(mv, str):
                    meta_flat[mk] = str(mv)
                else:
                    meta_flat[mk] = mv

            raw_meta = RawCacheMeta(
                source_name=str(raw_meta_obj["source_name"]),
                fetched_at_iso=str(raw_meta_obj["fetched_at_iso"]),
                content_type=str(raw_meta_obj["content_type"]),
                encoding=str(raw_meta_obj["encoding"]),
                cache_path=str(raw_meta_obj["cache_path"]),
                meta=meta_flat,
            )

        except CorruptedCache:
            raise
        except Exception as e:
            raise CorruptedCache(f"invalid meta.json schema: {meta_path} ({e})") from e

        payload = payload_path.read_bytes()

        # 校验 payload 完整性
        got = _sha256_hex(payload)
        if got != hex_digest:
            raise CorruptedCache(
                f"checksum mismatch: {run_dir} expected={hex_digest} got={got}"
            )

        return RawCacheRecord(payload=payload, meta=raw_meta)

    def iter_keys(self, config_name: str | None = None) -> Iterable[CacheKey]:
        """
        /**
         * @brief 枚举缓存键 / Iterate cache keys.
         *
         * @param config_name
         *        可选过滤 / optional filter.
         * @return
         *        CacheKey 迭代器 / Iterable of CacheKey.
         *
         * @note
         *        为了保证 fetched_at_iso 的可逆性，优先读取 meta.json 中的真实 fetched_at_iso。
         *        To preserve fetched_at_iso, we prefer reading it from meta.json.
         */
        """
        yield from self._iter_keys_impl(config_name=config_name)

    # ----------------------------
    # Internal methods
    # ----------------------------

    def _iter_keys_impl(self, config_name: Optional[str]) -> Iterator[CacheKey]:
        if not self._base_dir.exists():
            return

        for p in sorted(self._base_dir.iterdir()):
            if not p.is_dir():
                continue

            # quick filter by dirname suffix to avoid heavy IO where possible
            # 期望目录名：<safe_ts>-<config_name>-<hash>
            name = p.name
            parts = name.split("-")
            if len(parts) < 3:
                continue

            # 只做“粗筛”：最后两段应当是 config_name/hash（但 config_name 本身也可能含 '-'）
            # 因此这里不强行解析，只在 config_name 过滤时走 meta.json 读取
            meta_path = p / self._META_FILE
            if not meta_path.is_file():
                continue

            try:
                meta_obj = _read_json(meta_path)
                key_obj = meta_obj.get("key")
                raw_obj = meta_obj.get("raw")
                if not isinstance(key_obj, dict) or not isinstance(raw_obj, dict):
                    continue

                cfg = key_obj.get("config_name")
                hsh = key_obj.get("content_hash")
                fetched = raw_obj.get("fetched_at_iso")  # 用 raw.meta 里的真实 ISO

                if (
                    not isinstance(cfg, str)
                    or not isinstance(hsh, str)
                    or not isinstance(fetched, str)
                ):
                    continue

                if config_name is not None and cfg != config_name:
                    continue

                yield CacheKey(
                    config_name=cfg, content_hash=hsh, fetched_at_iso=fetched
                )

            except CorruptedCache:
                # iter 时不因为单个损坏目录而炸掉；记录一下即可
                _LOG.warning("skip corrupted raw cache dir: %s", str(p))
                continue

    def _run_dir_from_parts(
        self, *, config_name: str, content_hash: str, fetched_at_iso: str
    ) -> Path:
        safe_ts = _safe_ts_for_path(fetched_at_iso)
        dirname = f"{safe_ts}-{config_name}-{content_hash}"
        return self._base_dir / dirname

    def _resolve_run_dir(self, key: CacheKey) -> Path:
        """
        /**
         * @brief 将 key 解析到唯一的 run 目录 / Resolve key to a unique run directory.
         *
         * @param key
         *        CacheKey / CacheKey.
         * @return
         *        run 目录 / run directory.
         * @throw CacheMiss
         *        不存在或无法唯一确定 / missing or ambiguous.
         */
        """
        # 若 key 明确给了 fetched_at_iso，则目录名可直接构造（不读磁盘扫描）
        if key.fetched_at_iso is not None:
            run_dir = self._run_dir_from_parts(
                config_name=key.config_name,
                content_hash=key.content_hash,
                fetched_at_iso=key.fetched_at_iso,
            )
            if not run_dir.exists():
                raise CacheMiss(f"raw cache not found: {run_dir}")
            return run_dir

        # 否则：扫描匹配 "<*safe_ts*>-config-hash"
        if not self._base_dir.exists():
            raise CacheMiss("raw cache base dir does not exist")

        suffix = f"-{key.config_name}-{key.content_hash}"
        candidates = [
            p
            for p in self._base_dir.iterdir()
            if p.is_dir() and p.name.endswith(suffix)
        ]
        if not candidates:
            raise CacheMiss(
                f"raw cache not found for config={key.config_name} hash={key.content_hash}"
            )

        if len(candidates) == 1:
            return candidates[0]

        # 多个候选：无法唯一确定（上层应提供 fetched_at_iso，或自行选择最新/指定）
        raise CacheMiss(
            "raw cache key is ambiguous (multiple runs). "
            f"Please provide fetched_at_iso. candidates={[c.name for c in sorted(candidates)]}"
        )


# ============================================================
# Registry / 注册表
# ============================================================

from ..wiring import register_raw_cache

# 注册 FileSystemRawCache
register_raw_cache("fs_raw")(FileSystemRawCache)
