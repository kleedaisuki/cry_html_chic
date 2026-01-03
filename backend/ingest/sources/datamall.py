"""
/**
 * @file datamall.py
 * @brief DataMall 数据源实现 / DataMall data source implementation.
 *
 * 本模块封装 Singapore DataMall API 访问逻辑。
 * 设计原则：
 * - DataMallSource 实例 = 一个绑定 dataset 的数据源（request-bound）
 * - 构造函数吃下完整 config（account + dataset + params + mode）
 * - validate / fetch 不再依赖外部注入 cfg，仅保留参数以兼容公共接口
 */
"""

from __future__ import annotations

import time
import json
import random
from typing import Any, Mapping, Optional, List
from dataclasses import dataclass

import requests

from .interface import DataSource, RawArtifact
from ingest.wiring import register_source


# ============================================================
# DataMall request & endpoint models
# ============================================================


@dataclass(frozen=True)
class DataMallRequest:
    """
    /**
     * @brief DataMall 抓取请求模型 / DataMall fetch request model.
     *
     * @param dataset
     *        数据集名称 / Dataset name.
     * @param params
     *        查询参数（OData）/ Query params (OData).
     * @param accept
     *        Accept header / Accept header.
     */
    """

    dataset: str
    params: Optional[Mapping[str, Any]] = None
    accept: str = "application/json"


@dataclass(frozen=True)
class DataMallEndpointSpec:
    """
    /**
     * @brief DataMall endpoint 规格 / DataMall endpoint spec.
     *
     * @param path
     *        API path / API path.
     * @param mode
     *        默认抓取模式 / Default fetch mode.
     * @param page_size
     *        分页大小（若支持）/ Page size if supported.
     */
    """

    path: str
    mode: str
    page_size: Optional[int] = None


# ============================================================
# DataMallSource
# ============================================================


@register_source("datamall")
class DataMallSource(DataSource):
    """
    /**
     * @brief Singapore DataMall 数据源 / Singapore DataMall source.
     *
     * 设计要点：
     * - 实例即请求（request-bound）
     * - 构造函数绑定 dataset / params / mode
     * - fetch/validate 参数仅作兼容，不作为主驱动
     */
    """

    # DataMall 文档示例的 base（不带 /ltaodataservice 也可以，但这里固定含上更直观）
    # Base from docs examples (include /ltaodataservice for clarity).
    DEFAULT_BASE_URL = "https://datamall2.mytransport.sg/ltaodataservice"

    # ------------------------------------------------------------
    # Endpoint registry
    # ------------------------------------------------------------
    _ENDPOINTS: Mapping[str, DataMallEndpointSpec] = {
        "busstops": DataMallEndpointSpec(
            path="/BusStops",
            mode="paged",
            page_size=500,
        ),
        "busroutes": DataMallEndpointSpec(
            path="/BusRoutes",
            mode="paged",
            page_size=500,
        ),
        "trafficincidents": DataMallEndpointSpec(
            path="/TrafficIncidents",
            mode="realtime",
        ),
        # 可继续补充
    }

    # ------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------
    def __init__(
        self,
        *,
        account_key: str,
        dataset: Optional[str] = None,
        params: Optional[Mapping[str, Any]] = None,
        accept: str = "application/json",
        mode: Optional[str] = None,
        base_url: Optional[str] = None,
        user_agent: str = "SG-TRANSIT-VIS/ingest",
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        """
        /**
         * @brief 构造 DataMallSource / Construct DataMallSource.
         *
         * @param account_key
         *        DataMall AccountKey.
         * @param dataset
         *        数据集名称（绑定到实例）/ Dataset name (bind to instance).
         * @param params
         *        查询参数 / Query params.
         * @param accept
         *        Accept header.
         * @param mode
         *        模式覆盖（paged/realtime/linkfile/scenario）/ Mode override.
         */
        """

        # ---- identity / client config ----
        if not isinstance(account_key, str) or not account_key.strip():
            raise ValueError("account_key must be a non-empty string")

        self._account_key = account_key.strip()
        self._base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self._user_agent = user_agent
        self._timeout_seconds = float(timeout_seconds)
        self._max_retries = int(max_retries)
        self._retry_backoff_seconds = float(retry_backoff_seconds)
        self._last_request_ts: float = 0.0

        # ---- bind request at construction time ----
        self._request: Optional[DataMallRequest] = None
        if dataset is not None:
            if not isinstance(dataset, str) or not dataset.strip():
                raise ValueError("dataset must be a non-empty string if provided")
            if params is not None and not isinstance(params, Mapping):
                raise ValueError("params must be a mapping if provided")

            self._request = DataMallRequest(
                dataset=dataset.strip(),
                params=dict(params) if params is not None else None,
                accept=str(accept or "application/json"),
            )

        # ---- mode override ----
        self._mode_override: Optional[str] = None
        if mode is not None:
            m = str(mode).strip().lower()
            if not m:
                raise ValueError("mode must be non-empty if provided")
            self._mode_override = m

    # ------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------
    def _resolve_endpoint(self, dataset: str) -> DataMallEndpointSpec:
        key = dataset.strip().lower()
        if key not in self._ENDPOINTS:
            raise KeyError(key)
        return self._ENDPOINTS[key]

    def _coerce_request(
        self, value: Mapping[str, Any] | DataMallRequest
    ) -> DataMallRequest:
        if isinstance(value, DataMallRequest):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("request must be a mapping or DataMallRequest")

        dataset = value.get("dataset")
        if not isinstance(dataset, str) or not dataset.strip():
            raise ValueError("request['dataset'] must be a non-empty string")

        params = value.get("params")
        if params is not None and not isinstance(params, Mapping):
            raise ValueError("request['params'] must be a mapping if provided")

        accept = value.get("accept") or "application/json"
        return DataMallRequest(dataset=dataset.strip(), params=params, accept=accept)

    def _effective_request(
        self, compat_value: Mapping[str, Any] | DataMallRequest
    ) -> DataMallRequest:
        """
        /**
         * @brief 获取本次抓取使用的有效 request / Get effective request.
         *
         * 优先级：
         * 1) 构造函数绑定的 self._request（推荐）
         * 2) 兼容参数（仅当实例未绑定 request）
         */
        """
        if self._request is not None:
            return self._request
        return self._coerce_request(compat_value)

    # ------------------------------------------------------------
    # Public interface (unchanged)
    # ------------------------------------------------------------
    def validate(self, config: Mapping[str, Any]) -> None:
        """
        /**
         * @brief 校验 DataMallSource 实例 / Validate DataMallSource instance.
         *
         * @note
         * - 参数 config 仅为兼容 DataSource 接口
         * - 本实现默认验证实例字段
         */
        """

        # account_key 已在构造函数校验
        if not self._account_key:
            raise ValueError("account_key is missing")

        try:
            req = self._effective_request(config)
        except Exception as e:
            raise ValueError(f"invalid datamall request: {e}") from e

        try:
            self._resolve_endpoint(req.dataset)
        except Exception as e:
            raise ValueError(f"unknown datamall dataset: {req.dataset}") from e

        if self._mode_override is not None:
            if self._mode_override not in ("paged", "realtime", "scenario", "linkfile"):
                raise ValueError(f"unknown datamall mode: {self._mode_override}")

    def fetch(self, request: Mapping[str, Any] | DataMallRequest) -> List[RawArtifact]:
        """
        /**
         * @brief 抓取 DataMall 数据 / Fetch data from DataMall.
         *
         * @note
         * - 实际行为由实例字段驱动
         * - 参数 request 仅用于兼容旧调用
         */
        """

        req = self._effective_request(request)
        spec = self._resolve_endpoint(req.dataset)

        mode = (self._mode_override or spec.mode).lower()

        if mode == "paged":
            return self._fetch_paged(spec, req)
        if mode == "realtime":
            return [self._fetch_one(spec, req)]
        if mode == "scenario":
            return [self._fetch_one(spec, req)]
        if mode == "linkfile":
            return self._fetch_linkfile(spec, req)

        raise ValueError(f"unknown datamall mode: {mode}")

    @classmethod
    def name(cls) -> str:
        """
        /**
         * @brief 数据源稳定名称（用于 registry key）/ Stable source name (registry key).
         * @return 稳定名称 / Stable name.
         */
        """
        return "datamall"

    @classmethod
    def describe(cls) -> dict[str, str]:
        """
        /**
         * @brief 数据源静态描述（用于 provenance）/ Static description (for provenance).
         * @return 描述键值 / Description kvs.
         */
        """
        return {
            "source": "datamall",
            "provider": "LTA DataMall (Singapore)",
            "base_url_default": cls.DEFAULT_BASE_URL,
        }

    # ------------------------------------------------------------
    # Fetch implementations (unchanged)
    # ------------------------------------------------------------
    def _fetch_one(
        self, spec: DataMallEndpointSpec, req: DataMallRequest
    ) -> RawArtifact:
        url = f"{self._base_url}{spec.path}"
        headers = {
            "AccountKey": self._account_key,
            "Accept": req.accept,
            "User-Agent": self._user_agent,
        }

        resp = self._request_with_retry("GET", url, headers=headers, params=req.params)
        return RawArtifact(
            payload=resp.text,
            meta={
                "dataset": req.dataset,
                "url": url,
            },
        )

    def _fetch_paged(
        self, spec: DataMallEndpointSpec, req: DataMallRequest
    ) -> List[RawArtifact]:
        assert spec.page_size is not None

        artifacts: List[RawArtifact] = []
        skip = 0

        while True:
            params = dict(req.params or {})
            params["$skip"] = skip

            artifact = self._fetch_one(
                spec,
                DataMallRequest(dataset=req.dataset, params=params, accept=req.accept),
            )
            artifacts.append(artifact)

            data = json.loads(artifact.payload)
            value = data.get("value") or []
            if len(value) < spec.page_size:
                break

            skip += spec.page_size

        return artifacts

    def _fetch_linkfile(
        self, spec: DataMallEndpointSpec, req: DataMallRequest
    ) -> List[RawArtifact]:
        # 保持原实现
        return [self._fetch_one(spec, req)]

    # ------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------
    def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        params: Optional[Mapping[str, Any]] = None,
    ) -> requests.Response:
        for attempt in range(self._max_retries + 1):
            now = time.time()
            if now - self._last_request_ts < 0.1:
                time.sleep(0.1)

            self._last_request_ts = time.time()

            try:
                resp = requests.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    timeout=self._timeout_seconds,
                )
                resp.raise_for_status()
                return resp
            except Exception:
                if attempt >= self._max_retries:
                    raise
                time.sleep(self._retry_backoff_seconds * (2**attempt + random.random()))

        raise RuntimeError("unreachable")
