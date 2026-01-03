# backend/ingest/cache/preprocessed.py
from __future__ import annotations

"""
/**
 * @brief Preprocessed 缓存的文件系统实现 / Filesystem implementation of Preprocessed cache.
 *
 * 设计目标 / Design goals:
 * - 只依赖标准库 / Standard library only.
 * - 多文件产物（name->bytes）+ meta + manifest / Multiple artifacts + meta + manifest.
 * - 完整性校验：每个 artifact 记录 SHA-256 / Integrity: per-artifact SHA-256.
 * - 近似原子写：tmp dir -> rename / Atomic-ish save via temp dir -> rename.
 */
"""

import hashlib
import json
import os
import secrets
import shutil
from pathlib import Path
from typing import Dict, Iterable, Iterator, Mapping, Optional, Sequence

from ingest.utils.logger import get_logger
from .interface import (
    ArtifactManifest,
    CacheKey,
    CacheMiss,
    ConcurrentWrite,
    CorruptedCache,
    PreprocessedCache,
    PreprocessedCacheMeta,
)
from ingest.wiring import register_preprocessed_cache

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


def _safe_ts_for_path(iso: str) -> str:
    """
    /**
     * @brief 将 ISO 时间戳变为路径安全形式（Windows 兼容）/ Make ISO timestamp path-safe (Windows-friendly).
     *
     * @param iso
     *        ISO 时间戳 / ISO timestamp.
     * @return
     *        路径安全字符串 / Path-safe string.
     *
     * @note
     *        Windows 文件名不允许 ':'，因此做替换。
     *        Windows forbids ':' in file names, so we replace it.
     */
    """
    return iso.replace(":", "").replace(".", "")


def _read_json_obj(path: Path) -> Dict[str, object]:
    """
    /**
     * @brief 读取 JSON 文件为 dict / Read JSON file as dict.
     *
     * @param path
     *        JSON 文件路径 / JSON file path.
     * @return
     *        dict / dict.
     * @throw CorruptedCache
     *        JSON 无法解析或不是对象 / parse error or not an object.
     */
    """
    try:
        text = path.read_text(encoding="utf-8")
        obj = json.loads(text)
        if not isinstance(obj, dict):
            raise CorruptedCache(f"json must be an object: {path}")
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
    os.replace(tmp, path)


def _is_relative_safe_name(name: str) -> bool:
    """
    /**
     * @brief 校验 artifact 名称是否安全（相对路径、无上跳、无绝对路径）/ Validate artifact name safety.
     *
     * @param name
     *        文件名 / artifact name.
     * @return
     *        是否安全 / safe or not.
     *
     * @note
     *        防止 name='../../x' 这种目录穿越。
     *        Prevent path traversal like '../../x'.
     */
    """
    if name == "":
        return False
    p = Path(name)
    if p.is_absolute():
        return False
    # 禁止上跳 / disallow parent traversal
    if any(part == ".." for part in p.parts):
        return False
    # 允许子目录（例如 'foo/bar.js'）但不允许空段
    if any(part == "" for part in p.parts):
        return False
    return True


def _ensure_parent_dir(path: Path) -> None:
    """
    /**
     * @brief 确保父目录存在 / Ensure parent directory exists.
     */
    """
    path.parent.mkdir(parents=True, exist_ok=True)


# ============================================================
# Filesystem Preprocessed Cache / 文件系统 PreprocessedCache
# ============================================================


@register_preprocessed_cache("fs_preprocessed")
class FileSystemPreprocessedCache(PreprocessedCache):
    """
    /**
     * @brief 基于目录结构的 PreprocessedCache 实现 / PreprocessedCache implementation backed by filesystem directories.
     *
     * Layout / 目录结构:
     *   <base_dir>/
     *     <run_dir>/                       # 例如: 20251220T155900Z-config-abcdef
     *       meta.json                      # PreprocessedCacheMeta + key
     *       manifest.json                  # ArtifactManifest + 每文件校验信息
     *       artifacts/...                  # 产物文件（可含子目录）
     *
     * run_dir naming / 目录命名:
     *   "<safe_ts>-<config_name>-<content_hash>"
     */
    """

    _META_FILE = "meta.json"
    _MANIFEST_FILE = "manifest.json"
    _ARTIFACTS_DIR = "artifacts"

    def __init__(self, base_dir: str | Path) -> None:
        """
        /**
         * @brief 创建 PreprocessedCache（文件系统）/ Create filesystem PreprocessedCache.
         *
         * @param base_dir
         *        preprocessed 缓存根目录（例如 data/preprocessed）/ Root directory (e.g., data/preprocessed).
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
         * @brief 是否存在该 key 的 preprocessed 缓存 / Whether preprocessed cache exists for key.
         */
        """
        try:
            run_dir = self._resolve_run_dir(key)
        except CacheMiss:
            return False
        meta_path = run_dir / self._META_FILE
        manifest_path = run_dir / self._MANIFEST_FILE
        artifacts_dir = run_dir / self._ARTIFACTS_DIR
        return (
            meta_path.is_file() and manifest_path.is_file() and artifacts_dir.is_dir()
        )

    def save(
        self, key: CacheKey, artifacts: Mapping[str, bytes], meta: PreprocessedCacheMeta
    ) -> None:
        """
        /**
         * @brief 保存 preprocessed 缓存（多文件 + meta）/ Save preprocessed cache (artifacts + meta).
         *
         * @param key
         *        缓存键 / Cache key.
         * @param artifacts
         *        文件名->内容 / artifact name -> bytes.
         * @param meta
         *        元信息 / metadata.
         * @throw ConcurrentWrite
         *        并发写冲突 / concurrent write conflict.
         * @throw CorruptedCache
         *        非法 artifact 名称等 / invalid artifact name, etc.
         */
        """
        if not meta.built_at_iso:
            raise ValueError("PreprocessedCacheMeta.built_at_iso is empty")

        # preprocessed 依赖 built_at_iso 作为 run 时间戳（key.fetched_at_iso 也复用这个字段以统一定位）
        # 约束：若 key.fetched_at_iso 给了，必须与 meta.built_at_iso 一致，否则拒绝（防止“写错目录”）
        if key.fetched_at_iso is not None and key.fetched_at_iso != meta.built_at_iso:
            raise ValueError(
                "CacheKey.fetched_at_iso must match PreprocessedCacheMeta.built_at_iso "
                f"(key={key.fetched_at_iso}, built={meta.built_at_iso})"
            )

        # 目录名时间戳采用 built_at_iso（路径安全化）
        final_dir = self._run_dir_from_parts(
            config_name=key.config_name,
            content_hash=key.content_hash,
            built_at_iso=meta.built_at_iso,
        )

        if final_dir.exists():
            raise ConcurrentWrite(f"preprocessed cache already exists: {final_dir}")

        # 基础校验：artifact 名称必须安全
        for name in artifacts.keys():
            if not isinstance(name, str) or not _is_relative_safe_name(name):
                raise CorruptedCache(f"invalid artifact name: {name!r}")

        # tmp 目录
        tmp_dir = self._base_dir / (
            final_dir.name + f".tmp-{os.getpid()}-{secrets.token_hex(8)}"
        )
        tmp_dir.mkdir(parents=True, exist_ok=False)

        try:
            artifacts_root = tmp_dir / self._ARTIFACTS_DIR
            artifacts_root.mkdir(parents=True, exist_ok=True)

            # 写 artifacts + 计算校验信息
            manifest_files: Sequence[str] = sorted(artifacts.keys())
            checksums: Dict[str, Dict[str, object]] = {}

            for name in manifest_files:
                content = artifacts[name]
                digest = _sha256_hex(content)
                rel_path = artifacts_root / name
                _ensure_parent_dir(rel_path)
                rel_path.write_bytes(content)

                checksums[name] = {
                    "algo": "sha256",
                    "hex": digest,
                    "size_bytes": len(content),
                }

            # 写 manifest.json
            manifest_obj: Dict[str, object] = {
                "version": 1,
                "manifest": {
                    "files": list(manifest_files),
                },
                "checksums": checksums,
                "key": {
                    "config_name": key.config_name,
                    "content_hash": key.content_hash,
                    "fetched_at_iso": meta.built_at_iso,  # 对齐 CacheKey 语义（一次 run 的“时间戳”）
                },
            }
            _write_json_atomic(tmp_dir / self._MANIFEST_FILE, manifest_obj)

            # 写 meta.json
            # 注意：extra 允许 JsonValue（嵌套结构），直接丢给 json 就好（必须确保可序列化）
            meta_obj: Dict[str, object] = {
                "version": 1,
                "preprocessed": {
                    "built_at_iso": meta.built_at_iso,
                    "schema_version": meta.schema_version,
                    "extra": meta.extra,  # type: ignore[typeddict-item]
                },
                "key": {
                    "config_name": key.config_name,
                    "content_hash": key.content_hash,
                    "fetched_at_iso": meta.built_at_iso,
                },
            }
            _write_json_atomic(tmp_dir / self._META_FILE, meta_obj)

            # tmp -> final（目录 rename）
            final_dir.parent.mkdir(parents=True, exist_ok=True)
            os.rename(tmp_dir, final_dir)

            _LOG.info(
                "preprocessed cache saved: dir=%s files=%d",
                str(final_dir),
                len(manifest_files),
            )

        except FileExistsError as e:
            raise ConcurrentWrite(f"concurrent write: {final_dir}") from e
        except ConcurrentWrite:
            raise
        except CorruptedCache:
            raise
        except Exception as e:
            raise CorruptedCache(
                f"failed to save preprocessed cache into {final_dir}: {e}"
            ) from e
        finally:
            if tmp_dir.exists():
                try:
                    shutil.rmtree(tmp_dir)
                except Exception:
                    _LOG.warning("failed to cleanup tmp dir: %s", str(tmp_dir))

    def load_manifest(self, key: CacheKey) -> ArtifactManifest:
        """
        /**
         * @brief 读取成品清单 / Load manifest.
         *
         * @param key
         *        缓存键 / Cache key.
         * @return
         *        ArtifactManifest / ArtifactManifest.
         * @throw CacheMiss
         *        缓存不存在 / cache missing.
         * @throw CorruptedCache
         *        manifest.json 损坏 / corrupted manifest.
         */
        """
        run_dir = self._resolve_run_dir(key)
        manifest_path = run_dir / self._MANIFEST_FILE
        if not manifest_path.is_file():
            raise CacheMiss(f"manifest missing: {manifest_path}")

        obj = _read_json_obj(manifest_path)

        try:
            mani = obj.get("manifest")
            if not isinstance(mani, dict):
                raise CorruptedCache(f"invalid manifest field: {manifest_path}")

            files = mani.get("files")
            if not isinstance(files, list) or not all(
                isinstance(x, str) for x in files
            ):
                raise CorruptedCache(
                    f"manifest.files must be list[str]: {manifest_path}"
                )

            # 安全性：所有文件名必须安全
            for name in files:
                if not _is_relative_safe_name(name):
                    raise CorruptedCache(f"invalid artifact name in manifest: {name!r}")

            return ArtifactManifest(files=tuple(files))

        except CorruptedCache:
            raise
        except Exception as e:
            raise CorruptedCache(
                f"invalid manifest schema: {manifest_path} ({e})"
            ) from e

    def load_artifact(self, key: CacheKey, name: str) -> bytes:
        """
        /**
         * @brief 读取单个成品文件 / Load one artifact by name.
         *
         * @param key
         *        缓存键 / Cache key.
         * @param name
         *        文件名 / artifact name.
         * @return
         *        文件内容 / artifact bytes.
         * @throw CacheMiss
         *        缓存或文件不存在 / cache or artifact missing.
         * @throw CorruptedCache
         *        校验失败或 manifest 损坏 / checksum mismatch or corrupted manifest.
         */
        """
        if not _is_relative_safe_name(name):
            raise CacheMiss(f"artifact name is not safe: {name!r}")

        run_dir = self._resolve_run_dir(key)
        artifacts_root = run_dir / self._ARTIFACTS_DIR
        manifest_path = run_dir / self._MANIFEST_FILE
        if not manifest_path.is_file():
            raise CacheMiss(f"manifest missing: {manifest_path}")

        manifest_obj = _read_json_obj(manifest_path)
        checksums_obj = manifest_obj.get("checksums")
        if not isinstance(checksums_obj, dict):
            raise CorruptedCache(f"invalid checksums field: {manifest_path}")

        checksum = checksums_obj.get(name)
        if not isinstance(checksum, dict):
            raise CacheMiss(f"artifact not found in manifest: {name}")

        algo = checksum.get("algo")
        hex_digest = checksum.get("hex")
        if algo != "sha256" or not isinstance(hex_digest, str):
            raise CorruptedCache(
                f"invalid checksum for artifact {name}: {manifest_path}"
            )

        fpath = artifacts_root / name
        if not fpath.is_file():
            raise CacheMiss(f"artifact file missing: {fpath}")

        data = fpath.read_bytes()
        got = _sha256_hex(data)
        if got != hex_digest:
            raise CorruptedCache(
                f"checksum mismatch: {fpath} expected={hex_digest} got={got}"
            )
        return data

    def read_meta(self, key: CacheKey) -> PreprocessedCacheMeta:
        """
        /**
         * @brief 读取 preprocessed 元信息 / Read preprocessed metadata.
         *
         * @param key
         *        缓存键 / Cache key.
         * @return
         *        PreprocessedCacheMeta / PreprocessedCacheMeta.
         * @throw CacheMiss
         *        缓存不存在 / cache missing.
         * @throw CorruptedCache
         *        meta.json 损坏 / corrupted meta.json.
         */
        """
        run_dir = self._resolve_run_dir(key)
        meta_path = run_dir / self._META_FILE
        if not meta_path.is_file():
            raise CacheMiss(f"meta missing: {meta_path}")

        obj = _read_json_obj(meta_path)

        try:
            pp = obj.get("preprocessed")
            if not isinstance(pp, dict):
                raise CorruptedCache(f"invalid preprocessed field: {meta_path}")

            built_at_iso = pp.get("built_at_iso")
            schema_version = pp.get("schema_version")
            extra = pp.get("extra")

            if not isinstance(built_at_iso, str) or built_at_iso == "":
                raise CorruptedCache(f"invalid built_at_iso: {meta_path}")
            if not isinstance(schema_version, int):
                raise CorruptedCache(f"invalid schema_version: {meta_path}")

            # extra 允许 JsonValue（None/bool/num/str/list/dict），json 解析后天然满足；
            # 这里只做“顶层可接受类型”的保守检查。
            if not self._is_json_value(extra):
                raise CorruptedCache(f"invalid extra (not JsonValue): {meta_path}")

            # typing: Mapping[str, JsonValue]
            if isinstance(extra, dict):
                # key 必须是 str（json 解析保证），value 递归保证 JsonValue
                if not all(isinstance(k, str) for k in extra.keys()):
                    raise CorruptedCache(f"invalid extra keys: {meta_path}")

            return PreprocessedCacheMeta(
                built_at_iso=built_at_iso,
                schema_version=schema_version,
                extra=extra if isinstance(extra, dict) else {"value": extra},  # type: ignore[arg-type]
            )

        except CorruptedCache:
            raise
        except Exception as e:
            raise CorruptedCache(f"invalid meta schema: {meta_path} ({e})") from e

    def iter_keys(self, config_name: str | None = None) -> Iterable[CacheKey]:
        """
        /**
         * @brief 枚举缓存键 / Iterate cache keys.
         *
         * @param config_name
         *        可选过滤 / optional filter.
         * @return
         *        CacheKey 迭代器 / Iterable of CacheKey.
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

            meta_path = p / self._META_FILE
            manifest_path = p / self._MANIFEST_FILE
            artifacts_root = p / self._ARTIFACTS_DIR
            if (
                not meta_path.is_file()
                or not manifest_path.is_file()
                or not artifacts_root.is_dir()
            ):
                continue

            try:
                meta_obj = _read_json_obj(meta_path)
                key_obj = meta_obj.get("key")
                pp_obj = meta_obj.get("preprocessed")
                if not isinstance(key_obj, dict) or not isinstance(pp_obj, dict):
                    continue

                cfg = key_obj.get("config_name")
                hsh = key_obj.get("content_hash")
                built = pp_obj.get("built_at_iso")

                if (
                    not isinstance(cfg, str)
                    or not isinstance(hsh, str)
                    or not isinstance(built, str)
                ):
                    continue

                if config_name is not None and cfg != config_name:
                    continue

                yield CacheKey(config_name=cfg, content_hash=hsh, fetched_at_iso=built)

            except CorruptedCache:
                _LOG.warning("skip corrupted preprocessed cache dir: %s", str(p))
                continue

    def _run_dir_from_parts(
        self, *, config_name: str, content_hash: str, built_at_iso: str
    ) -> Path:
        safe_ts = _safe_ts_for_path(built_at_iso)
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
        if key.fetched_at_iso is not None:
            run_dir = self._run_dir_from_parts(
                config_name=key.config_name,
                content_hash=key.content_hash,
                built_at_iso=key.fetched_at_iso,
            )
            if not run_dir.exists():
                raise CacheMiss(f"preprocessed cache not found: {run_dir}")
            return run_dir

        if not self._base_dir.exists():
            raise CacheMiss("preprocessed cache base dir does not exist")

        suffix = f"-{key.config_name}-{key.content_hash}"
        candidates = [
            p
            for p in self._base_dir.iterdir()
            if p.is_dir() and p.name.endswith(suffix)
        ]
        if not candidates:
            raise CacheMiss(
                f"preprocessed cache not found for config={key.config_name} hash={key.content_hash}"
            )
        if len(candidates) == 1:
            return candidates[0]

        raise CacheMiss(
            "preprocessed cache key is ambiguous (multiple runs). "
            f"Please provide fetched_at_iso. candidates={[c.name for c in sorted(candidates)]}"
        )

    def _is_json_value(self, v: object) -> bool:
        """
        /**
         * @brief 检查对象是否满足 JsonValue / Check whether object matches JsonValue.
         *
         * @param v
         *        任意对象 / any object.
         * @return
         *        是否为 JsonValue / is JsonValue or not.
         *
         * @note
         *        这是一个保守的运行时检查，用于 meta.extra 的健壮性。
         *        Conservative runtime check for meta.extra robustness.
         */
        """
        if v is None:
            return True
        if isinstance(v, (bool, int, float, str)):
            return True
        if isinstance(v, list):
            return all(self._is_json_value(x) for x in v)
        if isinstance(v, dict):
            return all(
                isinstance(k, str) and self._is_json_value(val) for k, val in v.items()
            )
        return False


# ============================================================
# Registry / 注册表
# ============================================================

from ..wiring import register_preprocessed_cache

# 注册 FileSystemPreprocessedCache
register_preprocessed_cache("fs_preprocessed")(FileSystemPreprocessedCache)
