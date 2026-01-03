"""
/**
 * @file datamall.py
 * @brief DataMall V2 数据源实现 / DataMall V2 data source implementation.
 *
 * 本模块封装 Singapore LTA DataMall API 的访问逻辑，并对齐新版 V2 DataSource 接口：
 * - config 封装在构造函数（kwargs）中
 * - fetch() 无参，直接 yield RawCacheRecord（payload=bytes, meta=RawCacheMeta）
 *
 * 设计原则 / Principles:
 * - A1: 基类只做接口，不做框架（Source 自己处理分页/重试/限速） / Base defines interface only.
 * - A2: registry 只负责 name->class，不管理对象生命周期 / Registry maps name->class only.
 */
"""

from __future__ import annotations

import json
import random
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Mapping, Optional

import requests

from ingest.wiring import register_source
from ingest.sources.interface import (
    DataSource,
    make_raw_cache_meta,
    make_raw_cache_record,
)
from ingest.cache.interface import RawCacheRecord


@register_source("datamall")
class DataMallSource(DataSource):
    """
    /**
     * @brief Singapore LTA DataMall 数据源（V2） / Singapore LTA DataMall source (V2).
     *
     * 构造函数使用 **dict 映射（kwargs），不引入 config dataclass。
     * fetch() 直接产出 RawCacheRecord 流，与 RawCache 对齐。
     */
    """

    DEFAULT_BASE_URL = "https://datamall2.mytransport.sg/ltaodataservice"

    # endpoint registry: dataset_key -> spec
    # spec fields:
    # - path: str
    # - mode: "paged" | "realtime" | "scenario" | "linkfile"
    # - page_size: Optional[int]
    _ENDPOINTS: Dict[str, Dict[str, Any]] = {
        "busstops": {"path": "/BusStops", "mode": "paged", "page_size": 500},
        "busroutes": {"path": "/BusRoutes", "mode": "paged", "page_size": 500},
        "trafficincidents": {
            "path": "/TrafficIncidents",
            "mode": "realtime",
            "page_size": None,
        },
        # TODO: extend as needed
    }

    def __init__(
        self,
        *,
        account_key: str,
        dataset: str,
        params: Optional[Mapping[str, Any]] = None,
        accept: str = "application/json",
        mode: Optional[str] = None,
        base_url: Optional[str] = None,
        user_agent: str = "SG-TRANSIT-VIS/ingest",
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        retry_backoff_seconds: float = 0.5,
        min_interval_seconds: float = 0.1,
    ) -> None:
        """
        /**
         * @brief 构造 DataMallSource / Construct DataMallSource.
         *
         * @param account_key DataMall AccountKey.
         * @param dataset 数据集 key（如 busstops）/ Dataset key (e.g., busstops).
         * @param params OData 查询参数 / OData query params.
         * @param accept Accept header（默认 JSON）/ Accept header (default JSON).
         * @param mode 覆盖 endpoint 默认模式 / Override endpoint default mode.
         * @param base_url API base URL（默认官方）/ API base URL (default official).
         * @param user_agent UA / User-Agent.
         * @param timeout_seconds HTTP timeout / HTTP 超时秒数.
         * @param max_retries 最大重试次数 / Max retries.
         * @param retry_backoff_seconds 退避基数 / Backoff base seconds.
         * @param min_interval_seconds 最小请求间隔（限速）/ Min interval between requests (rate limit).
         */
        """

        if not isinstance(account_key, str) or not account_key.strip():
            raise ValueError("account_key must be a non-empty string")
        if not isinstance(dataset, str) or not dataset.strip():
            raise ValueError("dataset must be a non-empty string")

        if params is not None and not isinstance(params, Mapping):
            raise ValueError("params must be a mapping if provided")

        self._account_key = account_key.strip()
        self._dataset = dataset.strip()
        self._params = dict(params) if params is not None else None
        self._accept = str(accept or "application/json")

        self._mode_override = str(mode).strip().lower() if mode is not None else None
        self._base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self._user_agent = user_agent

        self._timeout_seconds = float(timeout_seconds)
        self._max_retries = int(max_retries)
        self._retry_backoff_seconds = float(retry_backoff_seconds)
        self._min_interval_seconds = float(min_interval_seconds)

        self._last_request_ts: float = 0.0

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
        return "datamall"

    @classmethod
    def describe(cls) -> Dict[str, str]:
        """
        /**
         * @brief 数据源静态描述 / Static description for provenance.
         */
        """
        return {
            "source": "datamall",
            "provider": "LTA DataMall (Singapore)",
            "base_url_default": cls.DEFAULT_BASE_URL,
        }

    def validate(self) -> None:
        """
        /**
         * @brief 校验 self.config（失败抛异常）/ Validate self.config (raise on failure).
         */
        """
        if not self._account_key:
            raise ValueError("account_key is missing")

        spec = self._resolve_endpoint(self._dataset)

        mode = (self._mode_override or spec["mode"]).lower()
        if mode not in ("paged", "realtime", "scenario", "linkfile"):
            raise ValueError(f"unknown datamall mode: {mode}")

        if mode == "paged":
            page_size = spec.get("page_size")
            if not isinstance(page_size, int) or page_size <= 0:
                raise ValueError(
                    f"paged mode requires a positive page_size, got: {page_size}"
                )

    def fetch(self) -> Iterable[RawCacheRecord]:
        """
        /**
         * @brief 拉取数据并产出 RawCacheRecord 流 / Fetch and yield RawCacheRecord stream.
         */
        """
        self.validate()

        spec = self._resolve_endpoint(self._dataset)
        mode = (self._mode_override or spec["mode"]).lower()

        if mode == "paged":
            yield from self._fetch_paged(spec)
            return

        if mode in ("realtime", "scenario"):
            yield self._fetch_one(spec, params=self._params)
            return

        if mode == "linkfile":
            # 目前保持为单次请求；若未来有真正 link discovery，可在这里扩展二阶段 fetch。
            yield self._fetch_one(spec, params=self._params)
            return

        raise ValueError(f"unknown datamall mode: {mode}")

    # ------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------
    def _resolve_endpoint(self, dataset: str) -> Dict[str, Any]:
        key = dataset.strip().lower()
        if key not in self._ENDPOINTS:
            raise ValueError(f"unknown datamall dataset: {key}")
        return self._ENDPOINTS[key]

    def _now_iso_utc(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _build_url(self, spec: Mapping[str, Any]) -> str:
        return f"{self._base_url}{spec['path']}"

    def _fetch_one(
        self, spec: Mapping[str, Any], *, params: Optional[Mapping[str, Any]]
    ) -> RawCacheRecord:
        url = self._build_url(spec)
        headers = {
            "AccountKey": self._account_key,
            "Accept": self._accept,
            "User-Agent": self._user_agent,
        }

        resp = self._request_with_retry("GET", url, headers=headers, params=params)

        # payload must be bytes in V2
        payload = resp.content

        # content-type: prefer response header, fallback to accept
        content_type = resp.headers.get("Content-Type", "") or self._accept
        # very conservative encoding: requests may guess; fallback to utf-8
        encoding = (resp.encoding or "utf-8").lower()

        meta = make_raw_cache_meta(
            source_name=self.name(),
            fetched_at_iso=self._now_iso_utc(),
            content_type=content_type,
            encoding=encoding,
            cache_path="",
            meta={
                "dataset": self._dataset,
                "url": url,
                "mode": (self._mode_override or spec["mode"]).lower(),
                "params_json": json.dumps(
                    dict(params or {}), ensure_ascii=False, sort_keys=True
                ),
            },
        )

        return make_raw_cache_record(payload=payload, meta=meta)

    def _fetch_paged(self, spec: Mapping[str, Any]) -> Iterable[RawCacheRecord]:
        page_size = int(spec["page_size"])
        skip = 0

        while True:
            params = dict(self._params or {})
            params["$skip"] = skip

            record = self._fetch_one(spec, params=params)
            yield record

            # Determine whether to continue paging:
            # For JSON responses following DataMall style: {"value":[...], ...}
            try:
                decoded = record.payload.decode("utf-8", errors="replace")
                data = json.loads(decoded)
                value = data.get("value") or []
                if not isinstance(value, list):
                    # Unexpected shape -> stop to avoid infinite loop
                    break
                if len(value) < page_size:
                    break
            except Exception:
                # If parse fails, stop paging (better safe than infinite loop)
                break

            skip += page_size

    # ------------------------------------------------------------
    # HTTP
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
            # basic rate limit
            now = time.time()
            delta = now - self._last_request_ts
            if delta < self._min_interval_seconds:
                time.sleep(self._min_interval_seconds - delta)

            self._last_request_ts = time.time()

            try:
                resp = requests.request(
                    method,
                    url,
                    headers=dict(headers),
                    params=dict(params) if params is not None else None,
                    timeout=self._timeout_seconds,
                )
                resp.raise_for_status()
                return resp
            except Exception:
                if attempt >= self._max_retries:
                    raise
                backoff = self._retry_backoff_seconds * (2**attempt + random.random())
                time.sleep(backoff)

        raise RuntimeError("unreachable")
