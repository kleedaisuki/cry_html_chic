# backend/ingest/sources/osm_overpass.py
from __future__ import annotations

import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, Mapping, Optional

from ingest.sources.interface import (
    DataSource,
    make_raw_cache_meta,
    make_raw_cache_record,
)
from ingest.cache.interface import RawCacheRecord
from ingest.wiring import register_source


def _utc_now_iso() -> str:
    """
    /**
     * @brief 生成 UTC 当前时间的 ISO 字符串 / Build current UTC time ISO string.
     * @return UTC ISO 时间字符串 / UTC ISO timestamp string.
     */
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ensure_str(d: Mapping[str, object], key: str) -> str:
    """
    /**
     * @brief 从 dict 中取字符串字段并校验 / Get a str field from dict with validation.
     * @param d 输入映射 / Input mapping.
     * @param key 键名 / Key.
     * @return 字符串值 / String value.
     * @throws ValueError 若字段缺失或非字符串 / If missing or not a string.
     */
    """
    v = d.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"config.{key} must be a non-empty string")
    return v.strip()


def _ensure_int(d: Mapping[str, object], key: str, *, min_v: int, max_v: int) -> int:
    """
    /**
     * @brief 从 dict 中取整数并校验范围 / Get an int field and validate range.
     * @param d 输入映射 / Input mapping.
     * @param key 键名 / Key.
     * @param min_v 最小值 / Min.
     * @param max_v 最大值 / Max.
     * @return 整数值 / Int value.
     * @throws ValueError 若字段缺失/非整数/越界 / If missing/not int/out of range.
     */
    """
    v = d.get(key)
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValueError(f"config.{key} must be an int")
    if v < min_v or v > max_v:
        raise ValueError(f"config.{key} must be in [{min_v}, {max_v}]")
    return v


def _ensure_bool(d: Mapping[str, object], key: str, *, default: bool) -> bool:
    """
    /**
     * @brief 从 dict 中取布尔值或使用默认值 / Get a bool field or use default.
     * @param d 输入映射 / Input mapping.
     * @param key 键名 / Key.
     * @param default 默认值 / Default.
     * @return 布尔值 / Bool value.
     * @throws ValueError 若字段存在但非布尔 / If exists but not bool.
     */
    """
    if key not in d:
        return default
    v = d.get(key)
    if not isinstance(v, bool):
        raise ValueError(f"config.{key} must be a bool")
    return v


@dataclass(frozen=True)
class _OverpassConfig:
    """
    /**
     * @brief OverpassSource 配置（内部结构）/ OverpassSource config (internal).
     *
     * @note
     * - 对外仍然走 **dict 注入（你们的约束）；
     *   Internally we normalize config for safety, but external init remains **dict.
     */
    """

    endpoint_url: str
    query: str
    timeout_sec: int
    user_agent: str
    accept_gzip: bool
    sleep_sec: float


@register_source("osm_overpass")
class OSMOverpassSource(DataSource):
    """
    /**
     * @brief 从 OpenStreetMap Overpass API 拉取原始 OSM JSON / Fetch raw OSM JSON from OSM Overpass API.
     *
     * 这是“几何抓取层”（geometry fetch），不做 GeoJSON 转换。
     * This is geometry fetch only; GeoJSON conversion is left to compilers.
     */
    """

    def __init__(self, **config: object) -> None:
        """
        /**
         * @brief 构造函数：保持 **dict 参数模式 / Ctor: keep **dict config style.
         * @param config 运行时配置字典 / Runtime config dict.
         */
        """
        # 保留原始 config 以便 debug/provenance
        self._raw_config: Dict[str, object] = dict(config)
        self._cfg: Optional[_OverpassConfig] = None

    @classmethod
    def name(cls) -> str:
        """
        /**
         * @brief 数据源稳定名称 / Stable source name.
         */
        """
        return "osm_overpass"

    @classmethod
    def describe(cls) -> Dict[str, str]:
        """
        /**
         * @brief 静态描述 / Static description.
         */
        """
        return {
            "provider": "OpenStreetMap",
            "api": "Overpass API",
            "kind": "raw_osm_json",
        }

    def validate(self) -> None:
        """
        /**
         * @brief 校验配置 / Validate config.
         *
         * 必填字段 / Required:
         * - endpoint_url: Overpass interpreter URL
         * - query: Overpass QL string
         *
         * 可选字段 / Optional:
         * - timeout_sec: int, default 60 (5~600)
         * - user_agent: str, default "SG-TRANSIT-VIS/ingest"
         * - accept_gzip: bool, default True
         * - sleep_sec: float, default 0.0 (用于友好限速 / friendly throttling)
         */
        """
        endpoint_url = _ensure_str(self._raw_config, "endpoint_url")
        query = _ensure_str(self._raw_config, "query")

        timeout_sec = self._raw_config.get("timeout_sec", 60)
        if isinstance(timeout_sec, bool) or not isinstance(timeout_sec, int):
            raise ValueError("config.timeout_sec must be an int")
        if timeout_sec < 5 or timeout_sec > 600:
            raise ValueError("config.timeout_sec must be in [5, 600]")

        user_agent = str(
            self._raw_config.get("user_agent", "SG-TRANSIT-VIS/ingest")
        ).strip()
        if not user_agent:
            raise ValueError("config.user_agent must be a non-empty string")

        accept_gzip = _ensure_bool(self._raw_config, "accept_gzip", default=True)

        sleep_sec = self._raw_config.get("sleep_sec", 0.0)
        if isinstance(sleep_sec, bool) or not isinstance(sleep_sec, (int, float)):
            raise ValueError("config.sleep_sec must be a number")
        if sleep_sec < 0.0 or sleep_sec > 10.0:
            raise ValueError("config.sleep_sec must be in [0.0, 10.0]")

        # 轻量 sanity check：endpoint 看起来像 interpreter
        if "interpreter" not in endpoint_url:
            raise ValueError(
                "config.endpoint_url should point to an Overpass 'interpreter' endpoint"
            )

        self._cfg = _OverpassConfig(
            endpoint_url=endpoint_url,
            query=query,
            timeout_sec=int(timeout_sec),
            user_agent=user_agent,
            accept_gzip=accept_gzip,
            sleep_sec=float(sleep_sec),
        )

    def fetch(self) -> Iterable[RawCacheRecord]:
        """
        /**
         * @brief 发起 Overpass 请求并产出单个 RawCacheRecord / Issue Overpass request and yield one RawCacheRecord.
         *
         * @return RawCacheRecord 流 / Stream of RawCacheRecord.
         *
         * @note
         * - 这里不做分页；Overpass 查询应尽量限定 scope（例如 bbox/area/name）。
         *   No paging here; keep queries scoped (bbox/area/name).
         */
        """
        if self._cfg is None:
            self.validate()
        assert self._cfg is not None

        if self._cfg.sleep_sec > 0:
            time.sleep(self._cfg.sleep_sec)

        # Overpass API: POST form field "data" is common and robust
        form = urllib.parse.urlencode({"data": self._cfg.query}).encode("utf-8")

        req = urllib.request.Request(
            self._cfg.endpoint_url,
            data=form,
            method="POST",
        )
        req.add_header(
            "Content-Type", "application/x-www-form-urlencoded; charset=utf-8"
        )
        req.add_header("User-Agent", self._cfg.user_agent)
        if self._cfg.accept_gzip:
            req.add_header("Accept-Encoding", "gzip")

        try:
            with urllib.request.urlopen(req, timeout=self._cfg.timeout_sec) as resp:
                raw = resp.read()
                encoding = resp.headers.get("Content-Encoding", "").lower().strip()
                content_type = (
                    resp.headers.get("Content-Type", "application/json")
                    .split(";")[0]
                    .strip()
                )

                if encoding == "gzip":
                    raw = gzip.decompress(raw)

                # 轻量校验：保证是 JSON（不解析语义，只保证可 json.loads）
                try:
                    json.loads(raw.decode("utf-8"))
                except Exception as e:  # noqa: BLE001
                    raise RuntimeError(
                        f"overpass response is not valid UTF-8 JSON: {e}"
                    ) from e

        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")[:800]
            except Exception:  # noqa: BLE001
                body = "<failed to read error body>"
            raise RuntimeError(f"overpass HTTPError {e.code}: {body}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"overpass URLError: {e}") from e

        fetched_at_iso = _utc_now_iso()
        meta = make_raw_cache_meta(
            source_name=self.name(),
            fetched_at_iso=fetched_at_iso,
            content_type=content_type or "application/json",
            encoding="utf-8",
            cache_path="",  # 我们不依赖 staging path
            meta={
                "endpoint_url": self._cfg.endpoint_url,
                "user_agent": self._cfg.user_agent,
                "query_len": str(len(self._cfg.query)),
            },
        )
        yield make_raw_cache_record(payload=raw, meta=meta)
