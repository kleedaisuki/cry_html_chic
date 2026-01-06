from __future__ import annotations

"""
/**
 * @file datamall_linkfile.py
 * @brief DataMall LinkFile 二阶段数据源 / DataMall link-file two-stage source.
 *
 * 支持 DataMall 返回 {"Link": "..."} 的数据集（PV/*, GeospatialWholeIsland, TrafficFlow 等），
 * 实现二阶段：
 * 1) discovery：请求 DataMall API 拿 Link
 * 2) download：下载文件到 data/tmp
 * 3) unzip（可选）：若为 zip，安全解压
 * 4) emit：读取每个文件 bytes -> yield RawCacheRecord
 *
 * @note
 * - Source 只做“抓取与溯源(provenance)”，不做业务字段清洗（交给 transform）。
 * - payload 统一 bytes；编码信息放到 meta.encoding。
 */
"""

import json
import random
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

import requests

from ingest.wiring import register_source
from ingest.sources.interface import (
    DataSource,
    make_raw_cache_meta,
    make_raw_cache_record,
)
from ingest.cache.interface import RawCacheRecord
from ingest.utils.logger import get_logger

_LOG = get_logger(__name__)


def _mask_url(s: str, head: int = 32, tail: int = 16) -> str:
    """
    @brief 脱敏 URL（避免泄露 pre-signed link）/ Mask URL to avoid leaking pre-signed link.
    """
    if not s:
        return ""
    if len(s) <= head + tail + 3:
        return s
    return f"{s[:head]}...{s[-tail:]}"


@register_source("datamall_linkfile")
class DataMallLinkFileSource(DataSource):
    """
    /**
     * @brief DataMall LinkFile Source（V2）/ DataMall LinkFile source (V2).
     *
     * 构造函数使用 **kwargs 映射，不引入 config dataclass。
     * fetch() 无参，直接 yield RawCacheRecord 流。
     */
    """

    DEFAULT_BASE_URL = "https://datamall2.mytransport.sg/ltaodataservice"

    _ENDPOINTS: Dict[str, str] = {
        # Passenger Volume
        "pv_bus": "/PV/Bus",
        "pv_odbus": "/PV/ODBus",
        "pv_train": "/PV/Train",
        "pv_odtrain": "/PV/ODTrain",
        # Geospatial Whole Island
        "geospatial_whole_island": "/GeospatialWholeIsland",
        # Traffic Flow
        "trafficflow": "/TrafficFlow",
    }

    def __init__(
        self,
        *,
        account_key: str,
        dataset: str,
        params: Optional[Mapping[str, Any]] = None,
        base_url: Optional[str] = None,
        accept: str = "application/json",
        user_agent: str = "SG-TRANSIT-VIS/ingest",
        timeout_seconds: float = 60.0,
        max_retries: int = 3,
        retry_backoff_seconds: float = 0.5,
        min_interval_seconds: float = 0.1,
        tmp_dir: str = "data/tmp",
        keep_downloaded: bool = True,
        keep_extracted: bool = True,
        max_bytes: int = 200 * 1024 * 1024,  # 200MB
        log_name: Optional[str] = None,
    ) -> None:
        """
        /**
         * @brief 构造 / Construct.
         *
         * @param account_key DataMall AccountKey.
         * @param dataset 数据集 key（如 pv_bus）/ Dataset key (e.g., pv_bus).
         * @param params OData/Query 参数 / Query params.
         * @param tmp_dir 下载与解压目录 / Download & extraction dir.
         * @param keep_downloaded 是否保留下载文件 / Keep downloaded file.
         * @param keep_extracted 是否保留解压目录 / Keep extracted directory.
         * @param max_bytes 单文件最大 bytes 限制 / Max bytes per file.
         * @param log_name 可选：自定义 logger 名称 / Optional custom logger name.
         */
        """
        if not isinstance(account_key, str) or not account_key.strip():
            raise ValueError("account_key must be a non-empty string")
        if not isinstance(dataset, str) or not dataset.strip():
            raise ValueError("dataset must be a non-empty string")
        if params is not None and not isinstance(params, Mapping):
            raise ValueError("params must be a mapping if provided")

        self._account_key = account_key.strip()
        self._dataset = dataset.strip().lower()
        self._params = dict(params) if params is not None else None

        self._base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self._accept = str(accept or "application/json")
        self._user_agent = user_agent

        self._timeout_seconds = float(timeout_seconds)
        self._max_retries = int(max_retries)
        self._retry_backoff_seconds = float(retry_backoff_seconds)
        self._min_interval_seconds = float(min_interval_seconds)
        self._last_request_ts: float = 0.0

        self._tmp_dir = Path(tmp_dir)
        self._keep_downloaded = bool(keep_downloaded)
        self._keep_extracted = bool(keep_extracted)
        self._max_bytes = int(max_bytes)

        # 模块单例 _LOG + getChild 形成清晰日志树；log_name 可覆盖用于定位多实例
        base = _LOG if not log_name else get_logger(log_name)
        _LOG = base.getChild(f"{self.name()}.{self._dataset}")

    # ------------------------------------------------------------
    # V2 interface
    # ------------------------------------------------------------
    @classmethod
    def name(cls) -> str:
        """
        /**
         * @brief 数据源稳定名称 / Stable source name.
         */
        """
        return "datamall_linkfile"

    @classmethod
    def describe(cls) -> Dict[str, str]:
        """
        /**
         * @brief 静态描述 / Static description.
         */
        """
        return {
            "source": "datamall_linkfile",
            "provider": "LTA DataMall (Singapore)",
            "base_url_default": cls.DEFAULT_BASE_URL,
            "mode": "two_stage_linkfile",
        }

    def validate(self) -> None:
        """
        /**
         * @brief 校验配置 / Validate config.
         */
        """
        if not self._account_key:
            raise ValueError("account_key is missing")
        if not self._dataset:
            raise ValueError("dataset is missing")

    def fetch(self) -> Iterable[RawCacheRecord]:
        """
        /**
         * @brief 二阶段 fetch：discovery -> download -> (unzip) -> yield records.
         */
        """
        self.validate()
        self._tmp_dir.mkdir(parents=True, exist_ok=True)

        _LOG.info(
            "fetch start: dataset=%s base_url=%s params=%s tmp_dir=%s retries=%s timeout=%.1fs",
            self._dataset,
            self._base_url,
            self._params,
            str(self._tmp_dir.as_posix()),
            self._max_retries,
            self._timeout_seconds,
        )

        stage1_url = self._build_stage1_url()
        _LOG.info("stage1 discovery: url=%s", stage1_url)

        link, stage1_payload_json, stage1_ct, stage1_enc = self._discovery_link(
            stage1_url
        )
        _LOG.info(
            "stage1 ok: content_type=%s encoding=%s link=%s",
            stage1_ct,
            stage1_enc,
            _mask_url(link),
        )

        run_id = self._run_id()
        download_path = self._tmp_dir / f"{run_id}-{self._dataset}.bin"
        _LOG.info("stage2 download: -> %s", str(download_path.as_posix()))

        final_path = self._download_link(link, download_path)
        size = self._try_stat_size(final_path)
        _LOG.info("stage2 ok: path=%s bytes=%s", str(final_path.as_posix()), size)

        is_zip = self._is_zip(final_path)
        _LOG.info("stage3 detect zip: %s", "yes" if is_zip else "no")

        records = 0

        if not is_zip:
            payload = self._read_bytes_limited(final_path)
            ct = self._guess_content_type(final_path.name)

            _LOG.info(
                "stage4 emit: file=%s bytes=%s content_type=%s",
                final_path.name,
                len(payload),
                ct,
            )
            yield self._make_record(
                payload=payload,
                content_type=ct,
                encoding="utf-8",
                extra={
                    "dataset": self._dataset,
                    "stage1_url": stage1_url,
                    "stage1_content_type": stage1_ct,
                    "stage1_encoding": stage1_enc,
                    "stage1_payload_json": stage1_payload_json,
                    "download_link_masked": _mask_url(link),
                    "download_path": str(final_path.as_posix()),
                    "inner_file": final_path.name,
                    "is_zip": "0",
                    "run_id": run_id,
                },
            )
            records = 1

            if not self._keep_downloaded:
                self._safe_unlink(final_path)

            _LOG.info("fetch done: dataset=%s records=%s", self._dataset, records)
            return

        extract_dir = self._tmp_dir / f"{run_id}-{self._dataset}"
        extract_dir.mkdir(parents=True, exist_ok=True)

        _LOG.info(
            "stage3 unzip: zip=%s -> dir=%s",
            final_path.name,
            str(extract_dir.as_posix()),
        )

        extracted_files = list(self._safe_unzip(final_path, extract_dir))
        _LOG.info("stage3 ok: extracted_files=%s", len(extracted_files))

        for fp in extracted_files:
            # 为了日志与安全阀准确：这里读取一次 bytes
            payload = self._read_bytes_limited(fp)
            ct = self._guess_content_type(fp.name)
            _LOG.info(
                "stage4 emit: file=%s bytes=%s content_type=%s",
                fp.name,
                len(payload),
                ct,
            )

            yield self._make_record(
                payload=payload,
                content_type=ct,
                encoding="utf-8",
                extra={
                    "dataset": self._dataset,
                    "stage1_url": stage1_url,
                    "stage1_content_type": stage1_ct,
                    "stage1_encoding": stage1_enc,
                    "stage1_payload_json": stage1_payload_json,
                    "download_link_masked": _mask_url(link),
                    "download_path": str(final_path.as_posix()),
                    "extract_dir": str(extract_dir.as_posix()),
                    "inner_file": fp.name,
                    "inner_path": str(fp.as_posix()),
                    "is_zip": "1",
                    "run_id": run_id,
                },
            )
            records += 1

        if not self._keep_downloaded:
            self._safe_unlink(final_path)
        if not self._keep_extracted:
            self._safe_rmtree(extract_dir)

        _LOG.info("fetch done: dataset=%s records=%s", self._dataset, records)

    # ------------------------------------------------------------
    # Internals: stage 1
    # ------------------------------------------------------------
    def _build_stage1_url(self) -> str:
        path = self._ENDPOINTS.get(self._dataset)
        if not path:
            # 允许用户把 dataset 当 path（例如 "/PV/Bus"）
            path = self._dataset if self._dataset.startswith("/") else None
        if not path:
            raise ValueError(f"unknown datamall_linkfile dataset: {self._dataset}")
        return f"{self._base_url}{path}"

    def _discovery_link(self, stage1_url: str) -> Tuple[str, str, str, str]:
        headers = {
            "AccountKey": self._account_key,
            "Accept": self._accept,
            "User-Agent": self._user_agent,
        }
        resp = self._request_with_retry(
            "GET", stage1_url, headers=headers, params=self._params
        )
        payload_bytes = resp.content
        content_type = resp.headers.get("Content-Type", "") or self._accept
        encoding = (resp.encoding or "utf-8").lower()

        _LOG.debug(
            "stage1 response: status=%s content_type=%s bytes=%s",
            resp.status_code,
            content_type,
            len(payload_bytes) if payload_bytes is not None else -1,
        )

        text = payload_bytes.decode("utf-8", errors="replace")
        try:
            obj = json.loads(text)
        except Exception as e:
            _LOG.error("stage1 json parse failed: err=%s body_prefix=%r", e, text[:200])
            raise ValueError(f"stage1 is not valid json: {e}")

        link = obj.get("Link")
        if not isinstance(link, str) or not link.strip():
            _LOG.error("stage1 json missing Link field: keys=%s", list(obj.keys())[:50])
            raise ValueError("stage1 json does not contain a valid 'Link' field")

        stage1_payload_json = json.dumps(obj, ensure_ascii=False, sort_keys=True)
        return link.strip(), stage1_payload_json, content_type, encoding

    # ------------------------------------------------------------
    # Internals: stage 2 (download) + stage 3 (unzip) + stage 4 (emit)
    # ------------------------------------------------------------
    def _download_link(self, link: str, out_path: Path) -> Path:
        # pre-signed URL：通常不需要 AccountKey
        resp = self._request_with_retry(
            "GET", link, headers={"User-Agent": self._user_agent}, params=None
        )
        out_path.write_bytes(resp.content)
        _LOG.debug(
            "stage2 saved: path=%s bytes=%s",
            str(out_path.as_posix()),
            len(resp.content),
        )
        return out_path

    def _is_zip(self, path: Path) -> bool:
        try:
            with open(path, "rb") as f:
                sig = f.read(4)
            return sig == b"PK\x03\x04"
        except Exception as e:
            _LOG.warning("zip detect failed: path=%s err=%s", str(path.as_posix()), e)
            return False

    def _safe_unzip(self, zip_path: Path, extract_dir: Path) -> Iterable[Path]:
        out: list[Path] = []
        with zipfile.ZipFile(zip_path, "r") as zf:
            infos = zf.infolist()
            _LOG.debug("zip entries: %s", len(infos))

            for info in infos:
                if info.is_dir():
                    continue

                name = info.filename.replace("\\", "/")

                # Zip Slip (../ or absolute path)
                if name.startswith("/") or ".." in name.split("/"):
                    raise ValueError(f"zip slip detected: {info.filename}")

                target = (extract_dir / name).resolve()
                if not str(target).startswith(str(extract_dir.resolve())):
                    raise ValueError(f"zip slip detected (resolved): {info.filename}")

                target.parent.mkdir(parents=True, exist_ok=True)

                with zf.open(info, "r") as src:
                    data = src.read()

                if self._max_bytes > 0 and len(data) > self._max_bytes:
                    raise ValueError(
                        f"extracted file too large: {name} bytes={len(data)}"
                    )

                target.write_bytes(data)
                out.append(target)

                _LOG.debug("unzipped: file=%s bytes=%s", name, len(data))

        return out

    def _read_bytes_limited(self, path: Path) -> bytes:
        data = path.read_bytes()
        if self._max_bytes > 0 and len(data) > self._max_bytes:
            raise ValueError(f"file too large: {path.name} bytes={len(data)}")
        return data

    def _guess_content_type(self, filename: str) -> str:
        low = filename.lower()
        if low.endswith(".csv"):
            return "text/csv"
        if low.endswith(".json"):
            return "application/json"
        if low.endswith(".geojson"):
            return "application/geo+json"
        return "application/octet-stream"

    def _make_record(
        self,
        *,
        payload: bytes,
        content_type: str,
        encoding: str,
        extra: Mapping[str, str],
    ) -> RawCacheRecord:
        meta = make_raw_cache_meta(
            source_name=self.name(),
            fetched_at_iso=self._now_iso_utc(),
            content_type=content_type,
            encoding=encoding,
            cache_path="",
            meta=extra,
        )
        return make_raw_cache_record(payload=payload, meta=meta)

    def _now_iso_utc(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _run_id(self) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        r = f"{random.randint(0, 999999):06d}"
        return f"{ts}-{r}"

    def _try_stat_size(self, path: Path) -> int:
        try:
            return int(path.stat().st_size)
        except Exception:
            return -1

    # ------------------------------------------------------------
    # HTTP with retry + basic rate limit
    # ------------------------------------------------------------
    def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        params: Optional[Mapping[str, Any]],
    ) -> requests.Response:
        for attempt in range(self._max_retries + 1):
            now = time.time()
            delta = now - self._last_request_ts
            if delta < self._min_interval_seconds:
                time.sleep(self._min_interval_seconds - delta)
            self._last_request_ts = time.time()

            try:
                _LOG.debug(
                    "http request: %s %s attempt=%s params=%s",
                    method,
                    _mask_url(url),
                    attempt,
                    params,
                )
                resp = requests.request(
                    method,
                    url,
                    headers=dict(headers),
                    params=dict(params) if params is not None else None,
                    timeout=self._timeout_seconds,
                )
                resp.raise_for_status()
                _LOG.debug(
                    "http response: %s %s status=%s bytes=%s",
                    method,
                    _mask_url(url),
                    resp.status_code,
                    len(resp.content) if resp.content is not None else -1,
                )
                return resp
            except Exception as e:
                if attempt >= self._max_retries:
                    _LOG.exception(
                        "http failed (final): %s %s attempt=%s/%s err=%s",
                        method,
                        _mask_url(url),
                        attempt,
                        self._max_retries,
                        e,
                    )
                    raise

                backoff = self._retry_backoff_seconds * (2**attempt + random.random())
                _LOG.warning(
                    "http retry: %s %s attempt=%s/%s backoff=%.3fs err=%s",
                    method,
                    _mask_url(url),
                    attempt,
                    self._max_retries,
                    backoff,
                    e,
                )
                time.sleep(backoff)

        raise RuntimeError("unreachable")

    # ------------------------------------------------------------
    # filesystem helpers (best-effort)
    # ------------------------------------------------------------
    def _safe_unlink(self, path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            _LOG.debug("unlink failed (ignored): %s", str(path.as_posix()))

    def _safe_rmtree(self, path: Path) -> None:
        try:
            for p in sorted(path.rglob("*"), reverse=True):
                if p.is_file():
                    self._safe_unlink(p)
                else:
                    try:
                        p.rmdir()
                    except Exception:
                        pass
            try:
                path.rmdir()
            except Exception:
                pass
        except Exception:
            _LOG.debug("rmtree failed (ignored): %s", str(path.as_posix()))
