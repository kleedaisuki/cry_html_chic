from __future__ import annotations

"""
/**
 * @file data_gov_sg.py
 * @brief data.gov.sg 数据源集合：Realtime / Datastore Search / Download / Catalog（V2 interface）。
 *        data.gov.sg sources bundle: Realtime / Datastore Search / Download / Catalog (V2 interface).
 *
 * 设计要点 / Design notes:
 * - 采用 V2 DataSource 接口：构造函数封装 config；fetch 直接产出 RawCacheRecord（payload + meta）。
 *   Uses V2 DataSource: __init__ encapsulates config; fetch yields RawCacheRecord (payload + meta).
 * - Source 只负责抓取 raw bytes + provenance meta；语义清洗交给 Transformers。
 *   Sources output raw bytes + provenance meta; semantic normalization belongs to transformers.
 * - 不再写 staging file，消灭无意义的双 IO 路径；cache 层负责持久化。
 *   No staging files; cache layer owns persistence.
 * - 注册采用 wiring.register_source 装饰器，在 import 时完成显式注册。
 *   Registration via wiring.register_source decorator at import time.
 */
"""

import json
import random
import time
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from ingest.sources.interface import (
    DataSource,
    make_raw_cache_meta,
    make_raw_cache_record,
)
from ingest.utils.logger import get_logger
from ingest.wiring import register_source


_LOG = get_logger(__name__)


# ============================================================
# Shared helpers / 共享工具
# ============================================================


def _utc_now_iso() -> str:
    """
    /**
     * @brief 生成 UTC ISO8601 时间戳 / Generate UTC ISO8601 timestamp.
     * @return UTC 时间戳字符串 / UTC timestamp string.
     */
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _require_str(config: Mapping[str, Any], key: str) -> str:
    """
    /**
     * @brief 读取必需字符串字段 / Read required string field.
     * @param config 配置对象 / Config mapping.
     * @param key 字段名 / Field name.
     * @return 字符串值 / String value.
     * @throws ValueError 字段缺失或非字符串 / Missing or not a string.
     */
    """
    v = config.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"Missing or invalid '{key}' (expected non-empty string)")
    return v.strip()


def _optional_str(config: Mapping[str, Any], key: str) -> Optional[str]:
    """
    /**
     * @brief 读取可选字符串字段 / Read optional string field.
     * @param config 配置对象 / Config mapping.
     * @param key 字段名 / Field name.
     * @return 字符串或 None / String or None.
     */
    """
    v = config.get(key)
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError(f"Invalid '{key}' (expected string)")
    s = v.strip()
    return s or None


def _optional_int(
    config: Mapping[str, Any], key: str, *, min_value: int | None = None
) -> Optional[int]:
    """
    /**
     * @brief 读取可选整数字段 / Read optional int field.
     * @param config 配置对象 / Config mapping.
     * @param key 字段名 / Field name.
     * @param min_value 最小值（可选） / Minimum allowed value (optional).
     * @return 整数或 None / Int or None.
     */
    """
    v = config.get(key)
    if v is None:
        return None
    if not isinstance(v, int):
        raise ValueError(f"Invalid '{key}' (expected int)")
    if min_value is not None and v < min_value:
        raise ValueError(f"Invalid '{key}' (expected >= {min_value})")
    return v


def _canonicalize_params(params: Mapping[str, Any]) -> Dict[str, str]:
    """
    /**
     * @brief 规范化 query 参数：排序、稳定 JSON 序列化、过滤 None。
     *        Canonicalize query params: sort, stable JSON serialize, drop None.
     *
     * @param params 原始参数 / Raw params.
     * @return 规范化后的参数（string->string）/ Canonical params (string->string).
     */
    """
    out: Dict[str, str] = {}
    for k in sorted(params.keys()):
        v = params[k]
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            out[str(k)] = str(v)
        else:
            out[str(k)] = json.dumps(
                v, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
    return out


@dataclass(frozen=True)
class _Retry:
    """
    /**
     * @brief 重试策略 / Retry policy.
     * @param max_retries 最大重试次数 / Maximum retries.
     * @param base_backoff_s 基础退避秒数 / Base backoff seconds.
     * @param max_backoff_s 最大退避秒数 / Max backoff seconds.
     */
    """

    max_retries: int = 5
    base_backoff_s: float = 0.5
    max_backoff_s: float = 20.0


def _sleep_backoff(attempt: int, retry_after_s: Optional[float], retry: _Retry) -> None:
    """
    /**
     * @brief 执行指数退避（带 jitter），优先尊重 Retry-After。
     *        Exponential backoff with jitter; prefers Retry-After.
     *
     * @param attempt 第几次重试（从 1 开始）/ Retry attempt number (starting at 1).
     * @param retry_after_s 服务器建议等待秒数 / Server-provided wait seconds.
     * @param retry 重试策略 / Retry policy.
     */
    """
    if retry_after_s is not None and retry_after_s > 0:
        delay = min(float(retry_after_s), retry.max_backoff_s)
    else:
        raw = (2 ** max(0, attempt - 1)) * retry.base_backoff_s
        delay = min(raw, retry.max_backoff_s)
        delay = delay * (0.75 + 0.5 * random.random())
    time.sleep(delay)


def _parse_retry_after(headers: Mapping[str, str]) -> Optional[float]:
    """
    /**
     * @brief 解析 Retry-After header（秒）/ Parse Retry-After header (seconds).
     * @param headers 响应头 / Response headers.
     * @return 秒数或 None / Seconds or None.
     */
    """
    ra = None
    for k in ("Retry-After", "retry-after"):
        if k in headers:
            ra = headers.get(k)
            break
    if ra is None:
        return None
    try:
        return float(str(ra).strip())
    except Exception:
        return None


def _build_headers(
    api_key: Optional[str], extra: Optional[Mapping[str, str]] = None
) -> Dict[str, str]:
    """
    /**
     * @brief 构建请求头（可选 x-api-key）/ Build request headers (optional x-api-key).
     * @param api_key API key / API key.
     * @param extra 额外头 / Extra headers.
     * @return headers 字典 / Headers dict.
     */
    """
    h: Dict[str, str] = {
        "Accept": "application/json, */*;q=0.8",
        "User-Agent": "DataGovSg-Ingest/0.1 (+https://example.invalid)",
    }
    if api_key:
        h["x-api-key"] = api_key
    if extra:
        for k, v in extra.items():
            h[str(k)] = str(v)
    return h


def _http_request(
    *,
    method: str,
    url: str,
    headers: Mapping[str, str],
    timeout_s: float,
    body: Optional[bytes] = None,
) -> Tuple[int, Dict[str, str], bytes]:
    """
    /**
     * @brief 执行一次 HTTP 请求 / Execute a single HTTP request.
     * @param method HTTP 方法 / HTTP method.
     * @param url 完整 URL / Full URL.
     * @param headers 请求头 / Request headers.
     * @param timeout_s 超时秒数 / Timeout seconds.
     * @param body 请求体（可选）/ Request body (optional).
     * @return (status, headers, payload_bytes) / (status, headers, payload_bytes).
     */
    """
    req = urllib.request.Request(url=url, data=body, method=method.upper())
    for k, v in headers.items():
        req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = int(getattr(resp, "status", resp.getcode()))
            resp_headers = {k: v for k, v in resp.headers.items()}
            payload = resp.read() or b""
            return status, resp_headers, payload
    except urllib.error.HTTPError as e:
        status = int(getattr(e, "code", 0) or 0)
        resp_headers = {k: v for k, v in (e.headers.items() if e.headers else [])}
        payload = e.read() if hasattr(e, "read") else b""
        return status, resp_headers, payload


def _http_request_with_retry(
    *,
    method: str,
    url: str,
    headers: Mapping[str, str],
    timeout_s: float,
    retry: _Retry,
    body: Optional[bytes] = None,
    rate_limit_sleep_s: float = 0.0,
) -> Tuple[int, Dict[str, str], bytes, Dict[str, str]]:
    """
    /**
     * @brief 执行 HTTP 请求（含限流 + 重试）/ Execute HTTP request (rate-limit + retries).
     *
     * @param method HTTP 方法 / HTTP method.
     * @param url URL / URL.
     * @param headers 请求头 / Headers.
     * @param timeout_s 超时 / Timeout seconds.
     * @param retry 重试策略 / Retry policy.
     * @param body 请求体 / Body.
     * @param rate_limit_sleep_s 简易限流：每次请求前 sleep 秒 / Simple throttling sleep per request.
     * @return (status, resp_headers, payload, diag_meta) / (status, resp_headers, payload, diag_meta).
     */
    """
    diag: Dict[str, str] = {"retries": "0"}

    if rate_limit_sleep_s and rate_limit_sleep_s > 0:
        time.sleep(rate_limit_sleep_s)

    for attempt in range(0, retry.max_retries + 1):
        if attempt > 0:
            diag["retries"] = str(attempt)

        status, resp_headers, payload = _http_request(
            method=method,
            url=url,
            headers=headers,
            timeout_s=timeout_s,
            body=body,
        )

        if 200 <= status < 300:
            return status, resp_headers, payload, diag

        if status in (408, 429) or 500 <= status < 600:
            if attempt >= retry.max_retries:
                return status, resp_headers, payload, diag

            ra = _parse_retry_after(resp_headers)
            _LOG.warning(
                "HTTP %s %s -> %s (retry %s/%s)",
                method,
                url,
                status,
                attempt + 1,
                retry.max_retries,
            )
            _sleep_backoff(attempt + 1, ra, retry)
            continue

        return status, resp_headers, payload, diag

    return 0, {}, b"", diag


def _join_url(base_url: str, path: str) -> str:
    """
    /**
     * @brief 拼接 base_url 与 path / Join base_url and path.
     * @param base_url 基础 URL / Base URL.
     * @param path 路径（以 / 开头）/ Path (leading '/').
     * @return 完整 URL / Full URL.
     */
    """
    b = base_url.rstrip("/")
    p = path if path.startswith("/") else ("/" + path)
    return b + p


def _safe_cache_path(*parts: str) -> str:
    """
    /**
     * @brief 构造安全的 cache_path 片段（仅做轻度清理）/ Build safe cache_path segments.
     * @param parts 路径片段 / Path segments.
     * @return 相对路径 / Relative path.
     */
    """
    cleaned = []
    for p in parts:
        s = str(p)
        s = s.replace("..", "_")
        s = s.replace("/", "_")
        s = s.replace("\\", "_")
        s = s.strip() or "_"
        cleaned.append(s)
    return "/".join(cleaned)


def _json_loads_bytes(payload: bytes) -> Any:
    """
    /**
     * @brief 将 bytes 解析为 JSON（UTF-8 优先）/ Parse bytes into JSON (prefer UTF-8).
     * @param payload JSON bytes / JSON bytes.
     * @return Python object / Python object.
     */
    """
    if not payload:
        return None
    try:
        return json.loads(payload.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(payload.decode("utf-8", errors="replace"))


def _default_base_url(config: Mapping[str, Any]) -> str:
    """
    /**
     * @brief 获取 base_url（默认 api-open.data.gov.sg）/ Get base_url (default api-open.data.gov.sg).
     * @param config 配置 / Config.
     * @return base_url / base_url.
     */
    """
    return _optional_str(config, "base_url") or "https://api-open.data.gov.sg"


def _default_timeout_s(config: Mapping[str, Any]) -> float:
    """
    /**
     * @brief 获取 timeout 秒数（默认 30）/ Get timeout seconds (default 30).
     * @param config 配置 / Config.
     * @return 超时秒数 / Timeout seconds.
     */
    """
    v = config.get("timeout_s")
    if v is None:
        return 30.0
    if isinstance(v, (int, float)) and float(v) > 0:
        return float(v)
    raise ValueError("Invalid 'timeout_s' (expected positive number)")


def _default_rate_limit_sleep_s(config: Mapping[str, Any]) -> float:
    """
    /**
     * @brief 简易限流：每次请求前 sleep 秒数（默认 0）/ Simple throttling sleep seconds per request (default 0).
     * @param config 配置 / Config.
     * @return 秒数 / Seconds.
     */
    """
    v = config.get("rate_limit_sleep_s")
    if v is None:
        return 0.0
    if isinstance(v, (int, float)) and float(v) >= 0:
        return float(v)
    raise ValueError("Invalid 'rate_limit_sleep_s' (expected >= 0)")


def _default_retry(config: Mapping[str, Any]) -> _Retry:
    """
    /**
     * @brief 从 config 读取 retry 策略（提供合理默认）/ Read retry policy from config (with defaults).
     * @param config 配置 / Config.
     * @return _Retry / _Retry.
     */
    """
    rc = config.get("retry")
    if rc is None:
        return _Retry()
    if not isinstance(rc, Mapping):
        raise ValueError("Invalid 'retry' (expected mapping)")
    mr = rc.get("max_retries", 5)
    bb = rc.get("base_backoff_s", 0.5)
    mb = rc.get("max_backoff_s", 20.0)
    if not isinstance(mr, int) or mr < 0:
        raise ValueError("Invalid retry.max_retries")
    if not isinstance(bb, (int, float)) or float(bb) <= 0:
        raise ValueError("Invalid retry.base_backoff_s")
    if not isinstance(mb, (int, float)) or float(mb) <= 0:
        raise ValueError("Invalid retry.max_backoff_s")
    return _Retry(max_retries=mr, base_backoff_s=float(bb), max_backoff_s=float(mb))


def _api_key(config: Mapping[str, Any]) -> Optional[str]:
    """
    /**
     * @brief 从 config 读取 api_key（可选）/ Read optional api_key from config.
     * @param config 配置 / Config.
     * @return api_key 或 None / api_key or None.
     */
    """
    return _optional_str(config, "api_key")


def _parse_charset_from_content_type(content_type: str) -> Optional[str]:
    """
    /**
     * @brief 从 Content-Type 解析 charset（若存在）/ Parse charset from Content-Type (if any).
     * @param content_type Content-Type 头（可能包含 charset=...）/ Content-Type header (may include charset=...).
     * @return charset 字符串或 None / charset string or None.
     */
    """
    if not content_type:
        return None
    # Example: "application/json; charset=utf-8"
    parts = [p.strip() for p in content_type.split(";") if p.strip()]
    for p in parts[1:]:
        if p.lower().startswith("charset="):
            v = p.split("=", 1)[1].strip().strip('"').strip("'")
            return v or None
    return None


def _infer_text_encoding(content_type: str) -> str:
    """
    /**
     * @brief 基于 Content-Type 推断文本编码（仅返回可用于 Python decode 的 codec 名）/
     *        Infer text encoding from Content-Type (returns Python-decodable codec name).
     *
     * @note
     * - 若 Content-Type 表示 JSON/text（例如 application/json, text/*, */*+json），默认返回 utf-8。
     *   If Content-Type indicates JSON/text (e.g., application/json, text/*, */*+json), default to utf-8.
     * - 否则返回 "binary" 作为哨兵值，表示不应走文本 decode。
     *   Otherwise returns "binary" sentinel, meaning should not be text-decoded.
     */
    """
    ct = (content_type or "").lower()
    charset = _parse_charset_from_content_type(ct)
    if charset:
        return charset
    is_text_like = (
        ct.startswith("text/")
        or "application/json" in ct
        or "+json" in ct
        or ct.endswith("/json")
    )
    return "utf-8" if is_text_like else "binary"


# ============================================================
# DataSource: Realtime / 实时接口
# ============================================================


@register_source("data_gov_sg.realtime")
class DataGovSgRealtimeSource(DataSource):
    """
    /**
     * @brief data.gov.sg Realtime API 数据源 / data.gov.sg realtime API source.
     *
     * 配置示例 / Example config:
     * {
     *   "source": "data_gov_sg.realtime",
     *   "endpoint": "pm25",
     *   "date": "2025-12-20",          // optional
     *   "api_key": "...",              // optional
     *   "base_url": "https://api-open.data.gov.sg",  // optional
     *   "timeout_s": 30,
     *   "retry": {"max_retries": 5}
     * }
     */
    """

    def __init__(self, **config: Any) -> None:
        """
        /**
         * @brief 构造函数：封装 **config（不使用 dataclass 配置）/ Ctor: encapsulate **config (no dataclass config).
         * @param config 配置键值对 / Config key-values.
         */
        """
        self.config: Dict[str, Any] = dict(config)

    @classmethod
    def name(cls) -> str:
        """@brief 数据源名称 / Source name."""
        return "data_gov_sg.realtime"

    @classmethod
    def describe(cls) -> Dict[str, str]:
        """@brief 静态描述 / Static description."""
        return {"provider": "data.gov.sg", "family": "realtime", "transport": "https"}

    def validate(self) -> None:
        _require_str(self.config, "endpoint")
        d = _optional_str(self.config, "date")
        if d is not None and not d:
            raise ValueError("Invalid 'date'")
        _default_timeout_s(self.config)
        _default_rate_limit_sleep_s(self.config)
        _default_retry(self.config)

    def fetch(self) -> Iterable[Any]:
        cfg = self.config
        base_url = _default_base_url(cfg)
        api_key = _api_key(cfg)
        endpoint = _require_str(cfg, "endpoint")
        date = _optional_str(cfg, "date")
        timeout_s = _default_timeout_s(cfg)
        rate_sleep = _default_rate_limit_sleep_s(cfg)
        retry = _default_retry(cfg)

        path = f"/v2/real-time/api/{urllib.parse.quote(endpoint)}"
        url = _join_url(base_url, path)
        params = _canonicalize_params({"date": date} if date else {})
        if params:
            url = url + "?" + urllib.parse.urlencode(params)

        headers = _build_headers(api_key)
        status, resp_headers, payload, diag = _http_request_with_retry(
            method="GET",
            url=url,
            headers=headers,
            timeout_s=timeout_s,
            retry=retry,
            rate_limit_sleep_s=rate_sleep,
        )

        content_type = resp_headers.get("Content-Type", "application/json")
        cache_path = _safe_cache_path(
            "data_gov_sg", "realtime", endpoint, date or "latest", "response.json"
        )

        meta = {
            **self.describe(),
            "endpoint": endpoint,
            "date": date or "",
            "url": url,
            "http_status": str(status),
            "retries": diag.get("retries", "0"),
        }

        m = make_raw_cache_meta(
            source_name=self.name(),
            fetched_at_iso=_utc_now_iso(),
            content_type=content_type,
            encoding="utf-8",
            cache_path=cache_path,
            meta=meta,
        )
        yield make_raw_cache_record(payload=payload, meta=m)


# ============================================================
# DataSource: Datastore Search / CKAN 查询
# ============================================================


@register_source("data_gov_sg.datastore_search")
class DataGovSgDatastoreSearchSource(DataSource):
    """
    /**
     * @brief data.gov.sg datastore_search（CKAN 风格）数据源 / data.gov.sg datastore_search source.
     *
     * 配置示例 / Example config:
     * {
     *   "source": "data_gov_sg.datastore_search",
     *   "base_url": "https://data.gov.sg",     // optional (note: different domain)
     *   "resource_id": "d_...",
     *   "page_size": 500,
     *   "max_pages": 200,                        // optional (recommended)
     *   "max_rows": 100000,                      // optional
     *   "filters": {"year": 2025},              // optional
     *   "q": "keyword",                         // optional
     *   "sort": "field asc",                    // optional
     *   "fields": ["a","b"],                   // optional
     *   "api_key": "...",                       // optional
     *   "retry": {"max_retries": 5}
     * }
     */
    """

    def __init__(self, **config: Any) -> None:
        """
        /**
         * @brief 构造函数：封装 **config（不使用 dataclass 配置）/ Ctor: encapsulate **config (no dataclass config).
         * @param config 配置键值对 / Config key-values.
         */
        """
        self.config: Dict[str, Any] = dict(config)

    @classmethod
    def name(cls) -> str:
        return "data_gov_sg.datastore_search"

    @classmethod
    def describe(cls) -> Dict[str, str]:
        return {
            "provider": "data.gov.sg",
            "family": "datastore_search",
            "transport": "https",
        }

    def validate(self) -> None:
        cfg = self.config
        _require_str(cfg, "resource_id")
        page_size = _optional_int(cfg, "page_size", min_value=1) or 500
        if page_size > 5000:
            raise ValueError("'page_size' too large; please keep <= 5000")

        max_pages = _optional_int(cfg, "max_pages", min_value=1)
        max_rows = _optional_int(cfg, "max_rows", min_value=1)
        if max_pages is None and max_rows is None:
            raise ValueError(
                "For safety, require at least one of 'max_pages' or 'max_rows'"
            )

        filters = cfg.get("filters")
        if filters is not None and not isinstance(filters, Mapping):
            raise ValueError("Invalid 'filters' (expected mapping)")
        fields = cfg.get("fields")
        if fields is not None and not isinstance(fields, list):
            raise ValueError("Invalid 'fields' (expected list)")

        _default_timeout_s(cfg)
        _default_rate_limit_sleep_s(cfg)
        _default_retry(cfg)

    def fetch(self) -> Iterable[Any]:
        cfg = self.config
        base_url = _optional_str(cfg, "base_url") or "https://data.gov.sg"
        api_key = _api_key(cfg)
        timeout_s = _default_timeout_s(cfg)
        rate_sleep = _default_rate_limit_sleep_s(cfg)
        retry = _default_retry(cfg)

        resource_id = _require_str(cfg, "resource_id")
        page_size = _optional_int(cfg, "page_size", min_value=1) or 500
        max_pages = _optional_int(cfg, "max_pages", min_value=1)
        max_rows = _optional_int(cfg, "max_rows", min_value=1)

        filters = cfg.get("filters")
        q = _optional_str(cfg, "q")
        sort = _optional_str(cfg, "sort")
        fields = cfg.get("fields")

        path = "/api/action/datastore_search"
        base = _join_url(base_url, path)
        headers = _build_headers(api_key)

        yielded_pages = 0
        yielded_rows = 0
        offset = 0

        while True:
            if max_pages is not None and yielded_pages >= max_pages:
                break
            if max_rows is not None and yielded_rows >= max_rows:
                break

            params_raw: Dict[str, Any] = {
                "resource_id": resource_id,
                "limit": page_size,
                "offset": offset,
                "filters": dict(filters) if isinstance(filters, Mapping) else None,
                "q": q,
                "sort": sort,
                "fields": fields,
            }
            params = _canonicalize_params(params_raw)
            url = base + "?" + urllib.parse.urlencode(params)

            status, resp_headers, payload, diag = _http_request_with_retry(
                method="GET",
                url=url,
                headers=headers,
                timeout_s=timeout_s,
                retry=retry,
                rate_limit_sleep_s=rate_sleep,
            )

            content_type = resp_headers.get("Content-Type", "application/json")
            # Allow callers to override encoding explicitly (useful for weird endpoints).
            encoding_override = _optional_str(cfg, "encoding")
            encoding = encoding_override or _infer_text_encoding(content_type)
            _LOG.info(
                "data_gov_sg.download direct: url=%s content_type=%s encoding=%s (override=%s) bytes=%d",
                url,
                content_type,
                encoding,
                encoding_override or "",
                len(payload),
            )
            cache_path = _safe_cache_path(
                "data_gov_sg",
                "datastore_search",
                resource_id,
                f"offset_{offset}",
                "page.json",
            )
            meta = {
                **self.describe(),
                "resource_id": resource_id,
                "offset": str(offset),
                "limit": str(page_size),
                "url": url,
                "http_status": str(status),
                "retries": diag.get("retries", "0"),
            }
            m = make_raw_cache_meta(
                source_name=self.name(),
                fetched_at_iso=_utc_now_iso(),
                content_type=content_type,
                # IMPORTANT: encoding must be a Python codec name when text-like; avoid
                # poisoning downstream JSON frontend with the "binary" sentinel.
                encoding=encoding,
                cache_path=cache_path,
                meta=meta,
            )
            yield make_raw_cache_record(payload=payload, meta=m)

            yielded_pages += 1

            # Determine termination by payload size.
            try:
                obj = _json_loads_bytes(payload)
                records = None
                if isinstance(obj, Mapping):
                    res = obj.get("result")
                    if isinstance(res, Mapping):
                        records = res.get("records")
                n = len(records) if isinstance(records, list) else 0
            except Exception:
                n = 0

            yielded_rows += n
            if n < page_size:
                break

            offset += page_size


# ============================================================
# DataSource: Dataset Download / 导出/下载
# ============================================================


@register_source("data_gov_sg.download")
class DataGovSgDownloadSource(DataSource):
    """
    /**
     * @brief data.gov.sg 下载型数据源 / data.gov.sg download-like source.
     *
     * 说明 / Notes:
     * - 仍保留两种路径：
     *   1) download_url 直接下载；
     *   2) job_start_url + poll + result_url_key 的简化状态机。
     * - V2 版不落盘：所有阶段 payload 都以 RawCacheRecord 形式交给 RawCache。
     */
    """

    def __init__(self, **config: Any) -> None:
        """
        /**
         * @brief 构造函数：封装 **config（不使用 dataclass 配置）/ Ctor: encapsulate **config (no dataclass config).
         * @param config 配置键值对 / Config key-values.
         */
        """
        self.config: Dict[str, Any] = dict(config)

    @classmethod
    def name(cls) -> str:
        return "data_gov_sg.download"

    @classmethod
    def describe(cls) -> Dict[str, str]:
        return {"provider": "data.gov.sg", "family": "download", "transport": "https"}

    def validate(self) -> None:
        cfg = self.config
        download_url = _optional_str(cfg, "download_url")
        job_start_url = _optional_str(cfg, "job_start_url")
        if not download_url and not job_start_url:
            raise ValueError("Require either 'download_url' or 'job_start_url'")

        _default_timeout_s(cfg)
        _default_rate_limit_sleep_s(cfg)
        _default_retry(cfg)

        if job_start_url:
            _require_str(cfg, "job_poll_url_template")
            _require_str(cfg, "job_result_url_key")

    def fetch(self) -> Iterable[Any]:
        cfg = self.config
        api_key = _api_key(cfg)
        timeout_s = _default_timeout_s(cfg)
        rate_sleep = _default_rate_limit_sleep_s(cfg)
        retry = _default_retry(cfg)
        headers = _build_headers(
            api_key, extra={"Accept": "application/json, */*;q=0.8"}
        )

        content_type_hint = (
            _optional_str(cfg, "content_type") or "application/octet-stream"
        )

        download_url = _optional_str(cfg, "download_url")
        if download_url:
            status, resp_headers, payload, diag = _http_request_with_retry(
                method="GET",
                url=download_url,
                headers=headers,
                timeout_s=timeout_s,
                retry=retry,
                rate_limit_sleep_s=rate_sleep,
            )
            content_type = resp_headers.get("Content-Type", content_type_hint)
                        # Allow callers to override encoding explicitly (useful for weird endpoints).
            encoding_override = _optional_str(cfg, "encoding")
            encoding = encoding_override or _infer_text_encoding(content_type)
            _LOG.info(
                "data_gov_sg.download direct: url=%s content_type=%s encoding=%s (override=%s) bytes=%d",
                download_url,
                content_type,
                encoding,
                encoding_override or "",
                len(payload),
            )
            cache_path = _safe_cache_path(
                "data_gov_sg", "download", "direct", "file.bin"
            )
            meta = {
                **self.describe(),
                "phase": "download",
                "url": download_url,
                "http_status": str(status),
                "retries": diag.get("retries", "0"),
            }
            m = make_raw_cache_meta(
                source_name=self.name(),
                fetched_at_iso=_utc_now_iso(),
                content_type=content_type,
                encoding=encoding,
                cache_path=cache_path,
                meta=meta,
            )
            yield make_raw_cache_record(payload=payload, meta=m)
            return

        # Simplified job-based export
        job_start_url = _require_str(cfg, "job_start_url")
        poll_tpl = _require_str(cfg, "job_poll_url_template")
        job_id_key = _optional_str(cfg, "job_id_key") or "jobId"
        job_status_key = _optional_str(cfg, "job_status_key") or "status"
        done_values = cfg.get("job_done_values") or ["completed", "done"]
        if not isinstance(done_values, list) or not all(
            isinstance(x, str) for x in done_values
        ):
            raise ValueError("Invalid 'job_done_values' (expected list[str])")
        result_url_key = _require_str(cfg, "job_result_url_key")
        poll_interval_s = float(cfg.get("poll_interval_s", 2.0))
        poll_timeout_s = float(cfg.get("poll_timeout_s", 120.0))
        if poll_interval_s <= 0 or poll_timeout_s <= 0:
            raise ValueError("Invalid poll interval/timeout")

        # 1) start
        s_status, s_headers, s_payload, s_diag = _http_request_with_retry(
            method="POST",
            url=job_start_url,
            headers=headers,
            timeout_s=timeout_s,
            retry=retry,
            body=b"",
            rate_limit_sleep_s=rate_sleep,
        )
        cache_path_start = _safe_cache_path(
            "data_gov_sg", "download", "job", "start.json"
        )
        meta_start = {
            **self.describe(),
            "phase": "start",
            "url": job_start_url,
            "http_status": str(s_status),
            "retries": s_diag.get("retries", "0"),
        }
        m_start = make_raw_cache_meta(
            source_name=self.name(),
            fetched_at_iso=_utc_now_iso(),
            content_type=s_headers.get("Content-Type", "application/json"),
            encoding="utf-8",
            cache_path=cache_path_start,
            meta=meta_start,
        )
        yield make_raw_cache_record(payload=s_payload, meta=m_start)

        obj = _json_loads_bytes(s_payload)
        if not isinstance(obj, Mapping):
            raise RuntimeError("Job start did not return JSON object")
        job_id = obj.get(job_id_key)
        if not isinstance(job_id, str) or not job_id:
            raise RuntimeError(f"Job id not found in key '{job_id_key}'")

        # 2) poll
        poll_url = poll_tpl.format(jobId=job_id)
        start_ts = time.time()

        while True:
            if time.time() - start_ts > poll_timeout_s:
                raise TimeoutError("Job polling timed out")

            p_status, p_headers, p_payload, p_diag = _http_request_with_retry(
                method="GET",
                url=poll_url,
                headers=headers,
                timeout_s=timeout_s,
                retry=retry,
                rate_limit_sleep_s=rate_sleep,
            )

            cache_path_poll = _safe_cache_path(
                "data_gov_sg",
                "download",
                "job",
                job_id,
                f"poll_{int(time.time())}.json",
            )
            meta_poll = {
                **self.describe(),
                "phase": "poll",
                "job_id": job_id,
                "url": poll_url,
                "http_status": str(p_status),
                "retries": p_diag.get("retries", "0"),
            }
            m_poll = make_raw_cache_meta(
                source_name=self.name(),
                fetched_at_iso=_utc_now_iso(),
                content_type=p_headers.get("Content-Type", "application/json"),
                encoding="utf-8",
                cache_path=cache_path_poll,
                meta=meta_poll,
            )
            yield make_raw_cache_record(payload=p_payload, meta=m_poll)

            pobj = _json_loads_bytes(p_payload)
            if isinstance(pobj, Mapping):
                status_val = pobj.get(job_status_key)
                if isinstance(status_val, str) and status_val.lower() in {
                    x.lower() for x in done_values
                }:
                    result_url = pobj.get(result_url_key)
                    if not isinstance(result_url, str) or not result_url:
                        raise RuntimeError(
                            f"Result url not found in key '{result_url_key}'"
                        )
                    download_url = result_url
                    break

            time.sleep(poll_interval_s)

        # 3) download result
        d_status, d_headers, d_payload, d_diag = _http_request_with_retry(
            method="GET",
            url=download_url,
            headers=headers,
            timeout_s=timeout_s,
            retry=retry,
            rate_limit_sleep_s=rate_sleep,
        )
        content_type = d_headers.get("Content-Type", content_type_hint)
        # Allow callers to override encoding explicitly (useful for weird endpoints).
        encoding_override = _optional_str(cfg, "encoding")
        encoding = encoding_override or _infer_text_encoding(content_type)
        _LOG.info(
            "data_gov_sg.download direct: url=%s content_type=%s encoding=%s (override=%s) bytes=%d",
            download_url,
            content_type,
            encoding,
            encoding_override or "",
            len(payload),
        )
        cache_path_dl = _safe_cache_path(
            "data_gov_sg", "download", "job", job_id, "file.bin"
        )
        meta_dl = {
            **self.describe(),
            "phase": "download",
            "job_id": job_id,
            "url": download_url,
            "http_status": str(d_status),
            "retries": d_diag.get("retries", "0"),
        }
        m_dl = make_raw_cache_meta(
            source_name=self.name(),
            fetched_at_iso=_utc_now_iso(),
            content_type=content_type,
            encoding=encoding,
            cache_path=cache_path_dl,
            meta=meta_dl,
        )
        yield make_raw_cache_record(payload=d_payload, meta=m_dl)


# ============================================================
# DataSource: Catalog / 数据集发现与元信息
# ============================================================


@register_source("data_gov_sg.catalog")
class DataGovSgCatalogSource(DataSource):
    """
    /**
     * @brief data.gov.sg Catalog（数据集发现/元数据）数据源 / data.gov.sg catalog/metadata discovery source.
     *
     * 配置示例 / Example config:
     * {
     *   "source": "data_gov_sg.catalog",
     *   "base_url": "https://api-open.data.gov.sg",   // optional
     *   "path": "/v2/public/api/datasets",           // REQUIRED (example)
     *   "params": {"query": "transport"},           // optional
     *   "api_key": "..."                              // optional
     * }
     */
    """

    def __init__(self, **config: Any) -> None:
        """
        /**
         * @brief 构造函数：封装 **config（不使用 dataclass 配置）/ Ctor: encapsulate **config (no dataclass config).
         * @param config 配置键值对 / Config key-values.
         */
        """
        self.config: Dict[str, Any] = dict(config)

    @classmethod
    def name(cls) -> str:
        return "data_gov_sg.catalog"

    @classmethod
    def describe(cls) -> Dict[str, str]:
        return {"provider": "data.gov.sg", "family": "catalog", "transport": "https"}

    def validate(self) -> None:
        cfg = self.config
        _require_str(cfg, "path")
        params = cfg.get("params")
        if params is not None and not isinstance(params, Mapping):
            raise ValueError("Invalid 'params' (expected mapping)")
        _default_timeout_s(cfg)
        _default_rate_limit_sleep_s(cfg)
        _default_retry(cfg)

    def fetch(self) -> Iterable[Any]:
        cfg = self.config
        base_url = _default_base_url(cfg)
        api_key = _api_key(cfg)
        timeout_s = _default_timeout_s(cfg)
        rate_sleep = _default_rate_limit_sleep_s(cfg)
        retry = _default_retry(cfg)

        path = _require_str(cfg, "path")
        params_in = cfg.get("params")
        params = (
            _canonicalize_params(params_in) if isinstance(params_in, Mapping) else {}
        )

        url = _join_url(base_url, path)
        if params:
            url = url + "?" + urllib.parse.urlencode(params)

        headers = _build_headers(api_key)
        status, resp_headers, payload, diag = _http_request_with_retry(
            method="GET",
            url=url,
            headers=headers,
            timeout_s=timeout_s,
            retry=retry,
            rate_limit_sleep_s=rate_sleep,
        )

        content_type = resp_headers.get("Content-Type", "application/json")
        cache_path = _safe_cache_path("data_gov_sg", "catalog", "response.json")
        meta = {
            **self.describe(),
            "path": path,
            "url": url,
            "http_status": str(status),
            "retries": diag.get("retries", "0"),
        }

        m = make_raw_cache_meta(
            source_name=self.name(),
            fetched_at_iso=_utc_now_iso(),
            content_type=content_type,
            encoding="utf-8",
            cache_path=cache_path,
            meta=meta,
        )
        yield make_raw_cache_record(payload=payload, meta=m)
