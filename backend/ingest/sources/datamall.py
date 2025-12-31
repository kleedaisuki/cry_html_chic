# backend/ingest/sources/datamall.py
from __future__ import annotations

"""
/**
 * @brief LTA DataMall 数据源实现 / LTA DataMall data source implementation.
 *
 * 设计取向 / Design intent:
 * - 继承只做“接口”，不做“框架” / Inheritance defines interface only; avoid framework-y base control flow.
 * - 标准库实现 HTTP，避免外部依赖 / Use stdlib HTTP; avoid external dependencies.
 * - 把 endpoint 行为差异封装在本模块内部（分页/实时/链接下载）
 *   Encapsulate endpoint behaviors here (paged / realtime / link-to-file).
 *
 * @note
 * - 该模块假设项目中存在 ingest.sources.interface，提供 DataSource 与 RawArtifact。
 *   This module assumes ingest.sources.interface exists and provides DataSource and RawArtifact.
 * - 若你的 DataSource 接口细节与此处假设略有出入，可在本模块底部的适配层进行微调。
 *   If your DataSource interface differs slightly, adjust the adapter methods at bottom.
 */
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import (
    Any,
    Dict,
    List,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Tuple,
)

from ingest.utils.logger import get_logger
from ingest.sources.interface import DataSource, RawArtifact

from ingest.wiring import register_source


_LOG = get_logger(__name__)


# ============================================================
# Public config dataclasses / 公共配置数据类
# ============================================================


@dataclass(frozen=True)
class DataMallEndpointSpec:
    """
    /**
     * @brief DataMall endpoint 规格 / DataMall endpoint specification.
     *
     * @param name
     *        逻辑名称（config 里使用）/ Logical dataset name (used in config).
     * @param path
     *        URL 路径（不含 base）/ URL path (without base).
     * @param mode
     *        行为模式：paged / realtime / linkfile / scenario / Behavior mode.
     */
    """

    name: str
    path: str
    mode: str = "paged"


@dataclass(frozen=True)
class DataMallRequest:
    """
    /**
     * @brief 一次 DataMall 抓取请求（抽象层）/ One DataMall fetch request (abstract).
     *
     * @param dataset
     *        数据集名字（如 "BusStops"）/ Dataset name (e.g., "BusStops").
     * @param params
     *        Query 参数 / Query params.
     * @param accept
     *        Accept 头（默认 JSON）/ Accept header (default JSON).
     */
    """

    dataset: str
    params: Mapping[str, Any] | None = None
    accept: str = "application/json"


# ============================================================
# Internal helpers / 内部工具
# ============================================================


def _utc_now_iso_z() -> str:
    """
    /**
     * @brief 获取当前 UTC 时间的 ISO-8601（带 Z）/ Get current UTC time in ISO-8601 with 'Z'.
     */
    """
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_content_hash(parts: Sequence[str]) -> str:
    """
    /**
     * @brief 计算稳定 content_hash（SHA-256）/ Compute stable content_hash (SHA-256).
     *
     * @param parts
     *        参与 hash 的字符串片段 / String parts for hashing.
     * @return
     *        sha256 hex / sha256 hex string.
     */
    """
    h = sha256()
    for p in parts:
        h.update(p.encode("utf-8", errors="strict"))
        h.update(b"\n")
    return h.hexdigest()


def _normalize_params(params: Mapping[str, Any] | None) -> List[Tuple[str, str]]:
    """
    /**
     * @brief 规范化 query 参数（稳定排序 + 字符串化）/ Normalize query params (stable sort + stringify).
     *
     * @param params
     *        query 参数 / query params.
     * @return
     *        [(k,v),...] 稳定列表 / stable (k,v) list.
     */
    """
    if not params:
        return []
    items: List[Tuple[str, str]] = []
    for k, v in params.items():
        if v is None:
            continue
        items.append((str(k), str(v)))
    items.sort(key=lambda kv: kv[0])
    return items


def _encode_query(params: Mapping[str, Any] | None) -> str:
    """
    /**
     * @brief 将 params 编码为 query string / Encode params into query string.
     *
     * @param params
     *        query 参数 / query params.
     * @return
     *        "k=v&..."（不含前导 '?'）/ "k=v&..." (no leading '?').
     */
    """
    items = _normalize_params(params)
    # doseq=True 允许 list 值，但我们先把它 string 化了；保持简单。
    # doseq=True supports list values, but we stringify earlier; keep it simple.
    return urllib.parse.urlencode(items, doseq=True)


def _json_find_first_link(obj: Any) -> Optional[str]:
    """
    /**
     * @brief 在 JSON 结构中尝试寻找“下载链接”字段 / Try to find a download link in JSON.
     *
     * @param obj
     *        解析后的 JSON / Parsed JSON.
     * @return
     *        链接 URL 或 None / URL or None.
     *
     * @note
     *        DataMall 的 passenger volume 类接口通常返回一个包含 Link 的对象（字段名可能是 Link/link）。
     *        Passenger volume endpoints often return an object containing Link/link.
     */
    """
    # 常见结构：{"value": [{"Link": "https://..."}]}
    if isinstance(obj, dict):
        for k in ("Link", "link", "URL", "Url", "url"):
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        v = obj.get("value")
        if isinstance(v, list) and v:
            for item in v:
                link = _json_find_first_link(item)
                if link:
                    return link
    if isinstance(obj, list):
        for item in obj:
            link = _json_find_first_link(item)
            if link:
                return link
    return None


# ============================================================
# DataMall Source / DataMall 数据源
# ============================================================


@register_source("datamall")
class DataMallSource(DataSource):
    """
    /**
     * @brief LTA DataMall 数据源 / LTA DataMall source.
     *
     * @note
     * - 默认 base_url 使用 datamall2.mytransport.sg（DataMall v6.5 示例域名）。
     *   Default base_url uses datamall2.mytransport.sg (DataMall v6.5 example domain).
     * - endpoint 的“行为模式”由 _ENDPOINTS 表决定，可在 config 中覆盖。
     *   Endpoint behavior modes defined by _ENDPOINTS; can be overridden by config.
     */
    """

    # DataMall 文档示例的 base（不带 /ltaodataservice 也可以，但这里固定含上更直观）
    # Base from docs examples (include /ltaodataservice for clarity).
    DEFAULT_BASE_URL = "https://datamall2.mytransport.sg/ltaodataservice"

    # 经验默认：分页接口每页 500（官方强调一般为 500）；此处作为默认实现常量。
    # Typical page size is 500 per docs; keep as default constant.
    DEFAULT_PAGE_SIZE = 500

    # 最小可用的 endpoint 映射（按需增补）。
    # Minimal endpoint map (extend as needed).
    _ENDPOINTS: Dict[str, DataMallEndpointSpec] = {
        # Bus
        "busstops": DataMallEndpointSpec("BusStops", "/BusStops", "paged"),
        "busroutes": DataMallEndpointSpec("BusRoutes", "/BusRoutes", "paged"),
        "busservices": DataMallEndpointSpec("BusServices", "/BusServices", "paged"),
        "busarrivalv2": DataMallEndpointSpec(
            "BusArrivalv2", "/BusArrivalv2", "realtime"
        ),
        # Rail
        "trainservicealerts": DataMallEndpointSpec(
            "TrainServiceAlerts", "/TrainServiceAlerts", "scenario"
        ),
        # Passenger volume (返回 link，需立即下载)
        "passengervolumebybusstops": DataMallEndpointSpec(
            "PassengerVolumeByBusStops", "/PV/Bus", "linkfile"
        ),
        "passengervolumebyoriginDestinationtrain": DataMallEndpointSpec(
            "PassengerVolumeByOriginDestinationTrain", "/PV/ODTrain", "linkfile"
        ),
    }

    def __init__(
        self,
        *,
        account_key: str,
        base_url: str | None = None,
        user_agent: str = "SG-TRANSIT-VIS/ingest",
        timeout_seconds: float = 30.0,
        min_interval_seconds: float = 0.0,
        max_retries: int = 3,
        retry_backoff_seconds: float = 0.8,
    ) -> None:
        """
        /**
         * @brief 创建 DataMallSource / Create a DataMallSource.
         *
         * @param account_key
         *        DataMall AccountKey / DataMall AccountKey.
         * @param base_url
         *        Base URL（默认 datamall2）/ Base URL (default datamall2).
         * @param user_agent
         *        User-Agent / User-Agent.
         * @param timeout_seconds
         *        HTTP 超时（秒）/ HTTP timeout (seconds).
         * @param min_interval_seconds
         *        最小请求间隔（节流）/ Minimum interval between requests (throttling).
         * @param max_retries
         *        最大重试次数 / Max retries.
         * @param retry_backoff_seconds
         *        退避基数（指数退避）/ Backoff base for exponential backoff.
         */
        """
        if not isinstance(account_key, str) or not account_key.strip():
            raise ValueError("account_key must be a non-empty string")

        self._account_key = account_key.strip()
        self._base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self._user_agent = user_agent
        self._timeout_seconds = float(timeout_seconds)
        self._min_interval_seconds = float(min_interval_seconds)
        self._max_retries = int(max_retries)
        self._retry_backoff_seconds = float(retry_backoff_seconds)
        self._last_request_ts: float = 0.0

    # --------------------------------------------------------
    # DataSource identity / DataSource 标识
    # --------------------------------------------------------

    @classmethod
    def name(cls) -> str:
        """
        /**
         * @brief 数据源稳定名称（registry key）/ Stable source name (registry key).
         */
        """
        return "datamall"

    @classmethod
    def describe(cls) -> Dict[str, str]:
        """
        /**
         * @brief 数据源静态描述信息 / Static description for provenance.
         */
        """
        return {
            "source": "datamall",
            "provider": "Land Transport Authority (LTA), Singapore",
            "api": "LTA DataMall",
            "base_url": cls.DEFAULT_BASE_URL,
            "transport_modes": "bus, mrt, lrt",
            "data_type": "public transport operational data",
        }

    def validate(self, config: Mapping[str, Any]) -> None:
        """
        /**
         * @brief 校验 DataMall Source 配置 / Validate DataMall source config.
         *
         * @param config
         *        ingest 配置对象 / Ingest config mapping.
         *
         * @throws ValueError
         *         若配置非法 / If config is invalid.
         */
        """
        if not isinstance(config, Mapping):
            raise ValueError("config must be a mapping")

        account_key = config.get("account_key")
        if not isinstance(account_key, str) or not account_key.strip():
            raise ValueError("config['account_key'] must be a non-empty string")

        dataset = config.get("dataset")
        if not isinstance(dataset, str) or not dataset.strip():
            raise ValueError("config['dataset'] must be a non-empty string")

        # endpoint 是否已知（提前 fail fast）
        try:
            self._resolve_endpoint(dataset)
        except Exception as e:
            raise ValueError(f"unknown datamall dataset: {dataset}") from e

    # --------------------------------------------------------
    # Main entry / 主入口
    # --------------------------------------------------------

    def fetch(self, request: Mapping[str, Any] | DataMallRequest) -> List[RawArtifact]:
        """
        /**
         * @brief 抓取 DataMall 原始数据并返回 RawArtifact 列表 / Fetch raw data from DataMall and return RawArtifact list.
         *
         * @param request
         *        抓取请求（dict 或 DataMallRequest）/ Request (dict or DataMallRequest).
         * @return
         *        RawArtifact 列表（可能多页/可能包含下载文件）/ List of RawArtifacts (may be multi-page / may include downloaded file).
         */
        """
        req = self._coerce_request(request)
        spec = self._resolve_endpoint(req.dataset)

        # 允许通过 dict request 覆盖 mode
        mode_override = None
        if isinstance(request, Mapping):
            mode_override = request.get("mode")
        mode = str(mode_override or spec.mode).strip().lower()

        if mode == "paged":
            return self._fetch_paged(spec, req)
        if mode == "realtime":
            return [self._fetch_one(spec, req)]
        if mode == "scenario":
            # 场景型：本模块只做一次抓取；轮询策略应由 pipeline/config 控制。
            # Scenario type: single fetch here; polling is controlled by pipeline/config.
            return [self._fetch_one(spec, req)]
        if mode == "linkfile":
            return self._fetch_linkfile(spec, req)

        raise ValueError(f"unknown datamall mode: {mode}")

    # ========================================================
    # Endpoint resolution / endpoint 解析
    # ========================================================

    def _resolve_endpoint(self, dataset: str) -> DataMallEndpointSpec:
        """
        /**
         * @brief 将 dataset 名解析为 endpoint spec / Resolve dataset name to endpoint spec.
         *
         * @param dataset
         *        数据集名 / Dataset name.
         * @return
         *        endpoint spec / endpoint spec.
         */
        """
        if not isinstance(dataset, str) or not dataset.strip():
            raise ValueError("dataset must be a non-empty string")
        key = dataset.strip().lower()
        if key in self._ENDPOINTS:
            return self._ENDPOINTS[key]
        # 允许用户直接传真实 path 名称（例如 "BusStops"）：做一次宽松匹配
        # Allow passing canonical names (e.g., "BusStops"); do a loose match.
        for k, v in self._ENDPOINTS.items():
            if v.name.lower() == key:
                return v
        raise ValueError(f"unknown datamall dataset: {dataset}")

    def _coerce_request(
        self, request: Mapping[str, Any] | DataMallRequest
    ) -> DataMallRequest:
        """
        /**
         * @brief 将 dict request 规范化为 DataMallRequest / Coerce dict request into DataMallRequest.
         */
        """
        if isinstance(request, DataMallRequest):
            return request
        if not isinstance(request, Mapping):
            raise TypeError("request must be a Mapping or DataMallRequest")

        dataset = request.get("dataset")
        if not isinstance(dataset, str) or not dataset.strip():
            raise ValueError("request['dataset'] must be a non-empty string")
        params = request.get("params")
        if params is None:
            p: Mapping[str, Any] | None = None
        elif isinstance(params, Mapping):
            p = dict(params)
        else:
            raise ValueError("request['params'] must be a mapping if provided")

        accept = request.get("accept") or "application/json"
        return DataMallRequest(dataset=dataset.strip(), params=p, accept=str(accept))

    # ========================================================
    # HTTP layer / HTTP 层
    # ========================================================

    def _throttle(self) -> None:
        """
        /**
         * @brief 简单节流：确保请求间隔 >= min_interval_seconds。
         *        Simple throttling: ensure interval >= min_interval_seconds.
         */
        """
        if self._min_interval_seconds <= 0:
            return
        now = time.time()
        delta = now - self._last_request_ts
        if delta < self._min_interval_seconds:
            time.sleep(self._min_interval_seconds - delta)

    def _http_get(self, url: str, *, accept: str) -> Tuple[int, Dict[str, str], bytes]:
        """
        /**
         * @brief 执行 HTTP GET（含重试）/ Perform HTTP GET (with retries).
         *
         * @param url
         *        完整 URL / Full URL.
         * @param accept
         *        Accept header / Accept header.
         * @return
         *        (status_code, headers, body_bytes) / (status_code, headers, body_bytes).
         */
        """
        last_err: Optional[BaseException] = None
        for attempt in range(self._max_retries + 1):
            self._throttle()
            try:
                req = urllib.request.Request(
                    url,
                    method="GET",
                    headers={
                        "AccountKey": self._account_key,
                        "accept": accept,
                        "User-Agent": self._user_agent,
                    },
                )
                with urllib.request.urlopen(req, timeout=self._timeout_seconds) as resp:
                    status = int(getattr(resp, "status", 200))
                    headers = {str(k): str(v) for k, v in resp.headers.items()}
                    body = resp.read()
                    self._last_request_ts = time.time()
                    return status, headers, body
            except urllib.error.HTTPError as e:
                # HTTPError 也是 response，读 body 以便诊断
                # HTTPError contains response; read body for diagnostics.
                try:
                    body = e.read()  # type: ignore[attr-defined]
                except Exception:
                    body = b""
                status = int(getattr(e, "code", 0) or 0)
                last_err = e
                # 429/5xx 才重试，4xx（除 429）直接抛
                # Retry on 429/5xx; for other 4xx fail fast.
                if status == 429 or 500 <= status < 600:
                    backoff = self._retry_backoff_seconds * (2**attempt)
                    _LOG.warning(
                        "DataMall HTTP %s on %s (attempt=%d/%d), backoff=%.2fs",
                        status,
                        url,
                        attempt,
                        self._max_retries,
                        backoff,
                    )
                    time.sleep(backoff)
                    continue
                # non-retryable
                raise RuntimeError(
                    f"DataMall HTTP error {status} for {url}: {body[:256]!r}"
                ) from e
            except Exception as e:
                last_err = e
                backoff = self._retry_backoff_seconds * (2**attempt)
                _LOG.warning(
                    "DataMall request failed: %s (attempt=%d/%d), backoff=%.2fs",
                    e,
                    attempt,
                    self._max_retries,
                    backoff,
                )
                time.sleep(backoff)

        raise RuntimeError(
            f"DataMall request failed after retries: {url}"
        ) from last_err

    def _build_url(
        self, spec: DataMallEndpointSpec, params: Mapping[str, Any] | None
    ) -> str:
        """
        /**
         * @brief 构造完整 URL / Build full URL.
         *
         * @param spec
         *        endpoint spec / endpoint spec.
         * @param params
         *        query params / query params.
         * @return
         *        完整 URL / Full URL.
         */
        """
        base = self._base_url
        path = spec.path
        if not path.startswith("/"):
            path = "/" + path
        q = _encode_query(params)
        return f"{base}{path}" + (f"?{q}" if q else "")

    # ========================================================
    # Fetch modes / 抓取模式
    # ========================================================

    def _fetch_one(
        self, spec: DataMallEndpointSpec, req: DataMallRequest
    ) -> RawArtifact:
        """
        /**
         * @brief 单次抓取（不分页）/ Fetch once (no pagination).
         */
        """
        fetched_at = _utc_now_iso_z()
        url = self._build_url(spec, req.params)
        status, headers, body = self._http_get(url, accept=req.accept)
        content_type = headers.get("Content-Type", "application/octet-stream")

        # content_hash：稳定地由“请求规范”导出（而不是响应 bytes）
        # content_hash: derive stably from request spec (not from response bytes).
        norm_items = _normalize_params(req.params)
        norm_q = "&".join([f"{k}={v}" for k, v in norm_items])
        content_hash = _stable_content_hash(
            [
                self.name,
                spec.name,
                spec.path,
                req.accept,
                norm_q,
            ]
        )

        meta: Dict[str, str] = {
            "dataset": spec.name,
            "path": spec.path,
            "url": url,
            "mode": spec.mode,
            "http_status": str(status),
            "accept": req.accept,
        }
        if norm_q:
            meta["query"] = norm_q

        # 若包含 $skip，显式写入分页信息，避免上层/下层再去解析 query。
        # If $skip is present, explicitly record paging info.
        if req.params and "$skip" in req.params:
            try:
                meta["skip"] = str(int(req.params.get("$skip") or 0))
            except Exception:
                meta["skip"] = str(req.params.get("$skip"))

        # RawArtifact：由项目 sources/interface.py 定义。
        # 我们尽量只使用“常见字段名”，以提高兼容性。
        return RawArtifact(
            source_name=self.name,
            fetched_at_iso=fetched_at,
            content_type=content_type,
            encoding="utf-8",
            content_hash=content_hash,
            payload=body,
            meta=meta,
        )

    def _fetch_paged(
        self, spec: DataMallEndpointSpec, req: DataMallRequest
    ) -> List[RawArtifact]:
        """
        /**
         * @brief 分页抓取（$skip）/ Paged fetch ($skip).
         *
         * @note
         * - DataMall 常见分页：每页 500，使用 $skip=0,500,1000...
         *   Typical paging: 500 per page, with $skip.
         */
        """
        base_params: MutableMapping[str, Any] = dict(req.params or {})
        # 如果用户显式给了 $skip，我们从它开始。
        # If user explicitly provides $skip, start from it.
        start_skip = 0
        if "$skip" in base_params:
            try:
                start_skip = int(base_params.get("$skip") or 0)
            except Exception:
                start_skip = 0

        artifacts: List[RawArtifact] = []
        skip = start_skip
        while True:
            page_params = dict(base_params)
            page_params["$skip"] = skip
            page_req = DataMallRequest(
                dataset=req.dataset, params=page_params, accept=req.accept
            )
            art = self._fetch_one(spec, page_req)
            artifacts.append(art)

            # 终止条件：尝试解析 JSON，若 value 长度 < 500 或为空则停止。
            # Stop condition: parse JSON; if len(value) < 500 or empty => stop.
            try:
                obj = json.loads(art.payload.decode("utf-8", errors="strict"))
                value = obj.get("value") if isinstance(obj, dict) else None
                n = len(value) if isinstance(value, list) else None
            except Exception:
                # 若无法解析（例如非 JSON），保守停止，避免无限循环。
                # If not parseable, stop conservatively to avoid infinite loop.
                _LOG.warning(
                    "DataMall paged response is not JSON; stop paging: %s",
                    art.meta.get("url"),
                )
                break

            if n is None:
                # 没有 value 字段：保守停止
                break
            if n <= 0:
                break
            if n < self.DEFAULT_PAGE_SIZE:
                break
            skip += self.DEFAULT_PAGE_SIZE

        return artifacts

    def _fetch_linkfile(
        self, spec: DataMallEndpointSpec, req: DataMallRequest
    ) -> List[RawArtifact]:
        """
        /**
         * @brief 链接下载型：先抓 JSON，再立刻下载 link 指向的文件。
         *        Linkfile mode: fetch JSON first, then immediately download the linked file.
         */
        """
        first = self._fetch_one(spec, req)
        # 解析 JSON 找 link
        try:
            obj = json.loads(first.payload.decode("utf-8", errors="strict"))
        except Exception as e:
            raise RuntimeError(
                f"linkfile endpoint did not return JSON: dataset={spec.name} url={first.meta.get('url')}"
            ) from e

        link = _json_find_first_link(obj)
        if not link:
            raise RuntimeError(
                f"linkfile endpoint JSON has no link field: dataset={spec.name} url={first.meta.get('url')}"
            )

        # 立刻下载；accept 设为 */* 更稳
        fetched_at = _utc_now_iso_z()
        status, headers, body = self._http_get(link, accept="*/*")
        content_type = headers.get("Content-Type", "application/octet-stream")

        # 对下载文件：content_hash 仍然按“请求规范”稳定导出（用 link 自身作为 identity）
        content_hash = _stable_content_hash(
            [
                self.name,
                spec.name,
                "download",
                link,
            ]
        )
        meta: Dict[str, str] = {
            "dataset": spec.name,
            "mode": "linkfile",
            "download_url": link,
            "http_status": str(status),
            "content_from": "download",
            # 给出强提示：该 link 通常短期过期（DataMall 文档提到 5 分钟）
            # Strong hint: link usually expires quickly (docs mention 5 minutes).
            "hint_link_expiry": "short-lived",
        }

        download_art = RawArtifact(
            source_name=self.name,
            fetched_at_iso=fetched_at,
            content_type=content_type,
            encoding="utf-8",
            content_hash=content_hash,
            payload=body,
            meta=meta,
        )

        # 返回两份：
        # 1) link JSON（可用于复现/溯源）
        # 2) 下载文件 bytes
        return [first, download_art]
