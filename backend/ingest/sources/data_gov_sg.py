from __future__ import annotations

"""
/**
 * @file data_gov_sg.py
 * @brief data.gov.sg 数据源集合：Realtime / Datastore Search / Download / Catalog。
 *        data.gov.sg sources bundle: Realtime / Datastore Search / Download / Catalog.
 *
 * 设计要点 / Design notes:
 * - 本文件内包含多个 DataSource 实现，但共享同一套轻量 HTTP/重试/限流/规范化工具。
 *   Multiple DataSource implementations live in one file, sharing a small HTTP/retry/rate-limit core.
 * - Source 只负责产出 raw bytes + provenance meta；语义清洗交给 Transformers。
 *   Sources output raw bytes + provenance meta; semantic normalization belongs to transformers.
 * - 注册采用 wiring.register_source 装饰器，在 import 时完成显式注册。
 *   Registration is performed via wiring.register_source decorator at import time.
 */
"""

import json
import random
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

from ingest.sources.interface import RawArtifact
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
     * @param params
     *        原始参数 / Raw params.
     * @return
     *        规范化后的参数（string->string）/ Canonical params (string->string).
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
            # 对 dict/list 等用稳定 JSON 表达
            out[str(k)] = json.dumps(
                v, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
    return out


@dataclass(frozen=True)
class _Retry:
    """
    /**
     * @brief 重试策略 / Retry policy.
     *
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
     * @param attempt
     *        第几次重试（从 1 开始）/ Retry attempt number (starting at 1).
     * @param retry_after_s
     *        服务器建议等待秒数 / Server-provided wait seconds.
     * @param retry
     *        重试策略 / Retry policy.
     */
    """

    if retry_after_s is not None and retry_after_s > 0:
        delay = min(float(retry_after_s), retry.max_backoff_s)
    else:
        # 2^(attempt-1) * base, capped, plus jitter
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
    # urllib lowercases? We'll be defensive.
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
        "User-Agent": "DataMall-Ingest/0.1 (+https://example.invalid)",
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

        # 2xx success
        if 200 <= status < 300:
            return status, resp_headers, payload, diag

        # retryable statuses
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

        # non-retryable
        return status, resp_headers, payload, diag

    # Should not reach
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


def _build_artifact(
    *,
    source_name: str,
    cache_path: str,
    content_type: str,
    encoding: str,
    meta: Mapping[str, str],
) -> RawArtifact:
    """
    /**
     * @brief 组装 RawArtifact / Build RawArtifact.
     * @param source_name 数据源名 / Source name.
     * @param cache_path 缓存路径（相对路径字符串）/ Cache path string.
     * @param content_type 内容类型 / Content type.
     * @param encoding 编码 / Encoding.
     * @param meta 元数据 / Meta.
     * @return RawArtifact / RawArtifact.
     */
    """

    # cache_path: 若上层不使用 RawCache，也可直接用该相对路径落盘。
    return RawArtifact(
        source_name=source_name,
        fetched_at_iso=_utc_now_iso(),
        content_type=content_type,
        encoding=encoding,
        cache_path=cache_path,
        meta=dict(meta),
    )


def _save_payload_bytes(
    *, save_dir: str | Path, cache_path: str, payload: bytes
) -> str:
    """
    /**
     * @brief 将 payload 写入本地文件（便于在没有 RawCache 的情况下直接使用）。
     *        Write payload to a local file (usable even without RawCache).
     *
     * @param save_dir
     *        根目录 / Root directory.
     * @param cache_path
     *        相对路径（RawArtifact.cache_path）/ Relative path (RawArtifact.cache_path).
     * @param payload
     *        原始字节 / Raw bytes.
     * @return
     *        写入后的绝对路径字符串 / Absolute path of written file.
     *
     * @note
     *        若项目后续接入 RawCache，本函数可以被替换/移除；现在先保证 Source 端“可独立运行”。
     *        If RawCache is used later, this can be replaced/removed; for now make sources standalone.
     */
    """

    root = Path(save_dir)
    out = root / cache_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(payload)
    return str(out.resolve())


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


def _save_dir(config: Mapping[str, Any]) -> str:
    """
    /**
     * @brief 读取保存目录（可选）/ Read optional save_dir.
     * @param config 配置 / Config.
     * @return 保存目录 / Save directory.
     *
     * @note
     *   - 若接入 RawCache，上层可忽略此字段；当前实现默认把 payload 写到本地文件，便于独立运行。
     *     If RawCache is used, upper layer can ignore this; current impl writes payload to local file.
     */
    """

    return _optional_str(config, "save_dir") or "."


# ============================================================
# DataSource: Realtime / 实时接口
# ============================================================


@register_source("data_gov_sg.realtime")
class DataGovSgRealtimeSource:
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

    @classmethod
    def name(cls) -> str:
        """@brief 数据源名称 / Source name."""

        return "data_gov_sg.realtime"

    @classmethod
    def describe(cls) -> Dict[str, str]:
        """@brief 静态描述 / Static description."""

        return {
            "provider": "data.gov.sg",
            "family": "realtime",
            "transport": "https",
        }

    def validate(self, config: Mapping[str, Any]) -> None:
        _require_str(config, "endpoint")
        d = _optional_str(config, "date")
        if d is not None and not d:
            raise ValueError("Invalid 'date'")
        # Common knobs
        _default_timeout_s(config)
        _default_rate_limit_sleep_s(config)
        _default_retry(config)

    def fetch(self, config: Mapping[str, Any]) -> Iterable[RawArtifact]:
        base_url = _default_base_url(config)
        api_key = _api_key(config)
        endpoint = _require_str(config, "endpoint")
        date = _optional_str(config, "date")
        timeout_s = _default_timeout_s(config)
        rate_sleep = _default_rate_limit_sleep_s(config)
        retry = _default_retry(config)
        save_dir = _save_dir(config)

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
        meta = {
            **self.describe(),
            "endpoint": endpoint,
            "date": date or "",
            "url": url,
            "http_status": str(status),
            "retries": diag.get("retries", "0"),
        }

        cache_path = _safe_cache_path(
            "data_gov_sg",
            "realtime",
            endpoint,
            date or "latest",
            "response.json",
        )

        saved_path = _save_payload_bytes(
            save_dir=save_dir, cache_path=cache_path, payload=payload
        )
        meta["saved_path"] = saved_path
        yield _build_artifact(
            source_name=self.name(),
            cache_path=cache_path,
            content_type=content_type,
            encoding="utf-8",
            meta=meta,
        )


# ============================================================
# DataSource: Datastore Search / CKAN 查询
# ============================================================


@register_source("data_gov_sg.datastore_search")
class DataGovSgDatastoreSearchSource:
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

    def validate(self, config: Mapping[str, Any]) -> None:
        _require_str(config, "resource_id")
        page_size = _optional_int(config, "page_size", min_value=1) or 500
        if page_size > 5000:
            raise ValueError("'page_size' too large; please keep <= 5000")

        max_pages = _optional_int(config, "max_pages", min_value=1)
        max_rows = _optional_int(config, "max_rows", min_value=1)
        if max_pages is None and max_rows is None:
            raise ValueError(
                "For safety, require at least one of 'max_pages' or 'max_rows'"
            )

        # Common knobs
        _default_timeout_s(config)
        _default_rate_limit_sleep_s(config)
        _default_retry(config)

    def fetch(self, config: Mapping[str, Any]) -> Iterable[RawArtifact]:
        # Note: datastore_search is hosted on data.gov.sg, not api-open.data.gov.sg.
        base_url = _optional_str(config, "base_url") or "https://data.gov.sg"
        api_key = _api_key(config)
        timeout_s = _default_timeout_s(config)
        rate_sleep = _default_rate_limit_sleep_s(config)
        retry = _default_retry(config)
        save_dir = _save_dir(config)

        resource_id = _require_str(config, "resource_id")
        page_size = _optional_int(config, "page_size", min_value=1) or 500
        max_pages = _optional_int(config, "max_pages", min_value=1)
        max_rows = _optional_int(config, "max_rows", min_value=1)

        filters = config.get("filters")
        if filters is not None and not isinstance(filters, Mapping):
            raise ValueError("Invalid 'filters' (expected mapping)")
        q = _optional_str(config, "q")
        sort = _optional_str(config, "sort")
        fields = config.get("fields")
        if fields is not None and not isinstance(fields, list):
            raise ValueError("Invalid 'fields' (expected list)")

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
            meta = {
                **self.describe(),
                "resource_id": resource_id,
                "offset": str(offset),
                "limit": str(page_size),
                "url": url,
                "http_status": str(status),
                "retries": diag.get("retries", "0"),
            }
            cache_path = _safe_cache_path(
                "data_gov_sg",
                "datastore_search",
                resource_id,
                f"offset_{offset}",
                "page.json",
            )
            saved_path = _save_payload_bytes(
                save_dir=save_dir, cache_path=cache_path, payload=payload
            )
            meta["saved_path"] = saved_path
            yield _build_artifact(
                source_name=self.name(),
                cache_path=cache_path,
                content_type=content_type,
                encoding="utf-8",
                meta=meta,
            )

            yielded_pages += 1

            # Determine page size from payload to decide termination.
            try:
                obj = _json_loads_bytes(payload)
                # CKAN: result.records is list
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
class DataGovSgDownloadSource:
    """
    /**
     * @brief data.gov.sg 下载型数据源 / data.gov.sg download-like source.
     *
     * 说明 / Notes:
     * - data.gov.sg 的下载/导出流程可能是“发起任务 -> 轮询 -> 下载”的状态机。
     *   The download/export flow may be a state machine: start job -> poll -> download.
     * - 为了不把实现绑定到单一接口，这里先提供两种路径：
     *   1) 若 config 提供 download_url，则直接下载。
     *   2) 若提供 job_start_url + job_poll_url_template + job_result_url_key，则执行简化状态机。
     *
     * 配置示例 A（直接下载）/ Example A (direct download):
     * {
     *   "source": "data_gov_sg.download",
     *   "download_url": "https://...",
     *   "content_type": "text/csv"              // optional
     * }
     *
     * 配置示例 B（简化任务）/ Example B (simplified job):
     * {
     *   "source": "data_gov_sg.download",
     *   "job_start_url": "https://.../start",
     *   "job_poll_url_template": "https://.../job/{jobId}",
     *   "job_id_key": "jobId",                  // default: jobId
     *   "job_status_key": "status",             // default: status
     *   "job_done_values": ["completed"],        // default: ["completed","done"]
     *   "job_result_url_key": "downloadUrl",
     *   "poll_interval_s": 2,
     *   "poll_timeout_s": 120
     * }
     */
    """

    @classmethod
    def name(cls) -> str:
        return "data_gov_sg.download"

    @classmethod
    def describe(cls) -> Dict[str, str]:
        return {
            "provider": "data.gov.sg",
            "family": "download",
            "transport": "https",
        }

    def validate(self, config: Mapping[str, Any]) -> None:
        download_url = _optional_str(config, "download_url")
        job_start_url = _optional_str(config, "job_start_url")
        if not download_url and not job_start_url:
            raise ValueError("Require either 'download_url' or 'job_start_url'")
        _default_timeout_s(config)
        _default_rate_limit_sleep_s(config)
        _default_retry(config)

        if job_start_url:
            _require_str(config, "job_poll_url_template")
            _require_str(config, "job_result_url_key")

    def fetch(self, config: Mapping[str, Any]) -> Iterable[RawArtifact]:
        api_key = _api_key(config)
        timeout_s = _default_timeout_s(config)
        rate_sleep = _default_rate_limit_sleep_s(config)
        retry = _default_retry(config)
        save_dir = _save_dir(config)
        headers = _build_headers(
            api_key, extra={"Accept": "application/json, */*;q=0.8"}
        )

        content_type_hint = (
            _optional_str(config, "content_type") or "application/octet-stream"
        )

        download_url = _optional_str(config, "download_url")
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
            meta = {
                **self.describe(),
                "url": download_url,
                "http_status": str(status),
                "retries": diag.get("retries", "0"),
            }
            cache_path = _safe_cache_path(
                "data_gov_sg", "download", "direct", "file.bin"
            )
            saved_path = _save_payload_bytes(
                save_dir=save_dir, cache_path=cache_path, payload=payload
            )
            meta["saved_path"] = saved_path
            yield _build_artifact(
                source_name=self.name(),
                cache_path=cache_path,
                content_type=content_type,
                encoding="binary",
                meta=meta,
            )
            return

        # Simplified job-based export
        job_start_url = _require_str(config, "job_start_url")
        poll_tpl = _require_str(config, "job_poll_url_template")
        job_id_key = _optional_str(config, "job_id_key") or "jobId"
        job_status_key = _optional_str(config, "job_status_key") or "status"
        done_values = config.get("job_done_values") or ["completed", "done"]
        if not isinstance(done_values, list) or not all(
            isinstance(x, str) for x in done_values
        ):
            raise ValueError("Invalid 'job_done_values' (expected list[str])")
        result_url_key = _require_str(config, "job_result_url_key")
        poll_interval_s = float(config.get("poll_interval_s", 2.0))
        poll_timeout_s = float(config.get("poll_timeout_s", 120.0))
        if poll_interval_s <= 0 or poll_timeout_s <= 0:
            raise ValueError("Invalid poll interval/timeout")

        # 1) start
        s_status, s_headers, s_payload, s_diag = _http_request_with_retry(
            method="POST",
            url=job_start_url,
            headers=headers,
            timeout_s=timeout_s,
            retry=retry,
            body=b"",  # simple POST
            rate_limit_sleep_s=rate_sleep,
        )
        meta_start = {
            **self.describe(),
            "phase": "start",
            "url": job_start_url,
            "http_status": str(s_status),
            "retries": s_diag.get("retries", "0"),
        }
        cache_path_start = _safe_cache_path(
            "data_gov_sg", "download", "job", "start.json"
        )
        saved_path_start = _save_payload_bytes(
            save_dir=save_dir, cache_path=cache_path_start, payload=s_payload
        )
        meta_start["saved_path"] = saved_path_start
        yield _build_artifact(
            source_name=self.name(),
            cache_path=cache_path_start,
            content_type=s_headers.get("Content-Type", "application/json"),
            encoding="utf-8",
            meta=meta_start,
        )

        obj = _json_loads_bytes(s_payload)
        if not isinstance(obj, Mapping):
            raise RuntimeError("Job start did not return JSON object")
        job_id = obj.get(job_id_key)
        if not isinstance(job_id, str) or not job_id:
            raise RuntimeError(f"Job id not found in key '{job_id_key}'")

        # 2) poll
        poll_url = poll_tpl.format(jobId=job_id)
        start_ts = time.time()
        last_payload: bytes = b""
        last_headers: Dict[str, str] = {}
        last_status: int = 0
        last_diag: Dict[str, str] = {}

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
            last_payload, last_headers, last_status, last_diag = (
                p_payload,
                p_headers,
                p_status,
                p_diag,
            )

            meta_poll = {
                **self.describe(),
                "phase": "poll",
                "job_id": job_id,
                "url": poll_url,
                "http_status": str(p_status),
                "retries": p_diag.get("retries", "0"),
            }
            # 每次 poll 都产出 raw，便于排障（可被 cache 去重/去频）。
            yield _build_artifact(
                source_name=self.name(),
                cache_path=_safe_cache_path(
                    "data_gov_sg",
                    "download",
                    "job",
                    job_id,
                    f"poll_{int(time.time())}.json",
                ),
                content_type=p_headers.get("Content-Type", "application/json"),
                encoding="utf-8",
                meta=meta_poll,
            )

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
        meta_dl = {
            **self.describe(),
            "phase": "download",
            "job_id": job_id,
            "url": download_url,
            "http_status": str(d_status),
            "retries": d_diag.get("retries", "0"),
        }
        cache_path_dl = _safe_cache_path(
            "data_gov_sg", "download", "job", job_id, "file.bin"
        )
        saved_path_dl = _save_payload_bytes(
            save_dir=save_dir, cache_path=cache_path_dl, payload=d_payload
        )
        meta_dl["saved_path"] = saved_path_dl
        yield _build_artifact(
            source_name=self.name(),
            cache_path=cache_path_dl,
            content_type=content_type,
            encoding="binary",
            meta=meta_dl,
        )


# ============================================================
# DataSource: Catalog / 数据集发现与元信息（可选，但已实现）
# ============================================================


@register_source("data_gov_sg.catalog")
class DataGovSgCatalogSource:
    """
    /**
     * @brief data.gov.sg Catalog（数据集发现/元数据）数据源 / data.gov.sg catalog/metadata discovery source.
     *
     * 说明 / Notes:
     * - data.gov.sg 的 catalog API 形式可能会演进；因此这里以“可配置 endpoint”方式实现。
     *   data.gov.sg catalog APIs may evolve; thus this source is endpoint-configurable.
     * - 你可以用它做：
     *   - list datasets / collections
     *   - fetch dataset metadata
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

    @classmethod
    def name(cls) -> str:
        return "data_gov_sg.catalog"

    @classmethod
    def describe(cls) -> Dict[str, str]:
        return {
            "provider": "data.gov.sg",
            "family": "catalog",
            "transport": "https",
        }

    def validate(self, config: Mapping[str, Any]) -> None:
        # We keep this generic: require a path.
        _require_str(config, "path")
        params = config.get("params")
        if params is not None and not isinstance(params, Mapping):
            raise ValueError("Invalid 'params' (expected mapping)")
        _default_timeout_s(config)
        _default_rate_limit_sleep_s(config)
        _default_retry(config)

    def fetch(self, config: Mapping[str, Any]) -> Iterable[RawArtifact]:
        base_url = _default_base_url(config)
        api_key = _api_key(config)
        timeout_s = _default_timeout_s(config)
        rate_sleep = _default_rate_limit_sleep_s(config)
        retry = _default_retry(config)
        save_dir = _save_dir(config)

        path = _require_str(config, "path")
        params_in = config.get("params")
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
        meta = {
            **self.describe(),
            "path": path,
            "url": url,
            "http_status": str(status),
            "retries": diag.get("retries", "0"),
        }
        cache_path = _safe_cache_path("data_gov_sg", "catalog", "response.json")
        saved_path = _save_payload_bytes(
            save_dir=save_dir, cache_path=cache_path, payload=payload
        )
        meta["saved_path"] = saved_path
        yield _build_artifact(
            source_name=self.name(),
            cache_path=cache_path,
            content_type=content_type,
            encoding="utf-8",
            meta=meta,
        )
