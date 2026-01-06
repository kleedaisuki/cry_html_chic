from __future__ import annotations

"""
/**
 * @file data_gov_sg_heatmap_optimizer.py
 * @brief data.gov.sg 热力图归一化优化器 / Heatmap normalization optimizer for data.gov.sg.
 *
 * 本优化器把 data.gov.sg 的常见 JSON schema 归一化为 heatmap(points) IR，
 * 以便前端用 Leaflet/D3 直接渲染。
 * This optimizer normalizes common data.gov.sg JSON schemas into a heatmap(points) IR
 * that can be rendered directly by Leaflet/D3 on the frontend.
 */
"""

from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

from ingest.transform.interface import IRModule, JsonValue, SchemaMismatchError
from ingest.wiring import register_optimizer


JsonObj = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


def _as_str(x: Any) -> Optional[str]:
    """@brief 安全转字符串 / Safe str cast."""
    return x if isinstance(x, str) else None


def _as_float(x: Any) -> Optional[float]:
    """@brief 安全转浮点 / Safe float cast."""
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    return None


def _get_path(obj: Any, path: List[Union[str, int]]) -> Any:
    """
    /**
     * @brief 通过 path 访问嵌套字段 / Access nested field by a path.
     * @param obj 根对象 / Root object.
     * @param path 路径（str key 或 int index）/ Path (str keys or int indexes).
     * @return 取到的值或 None / Value or None.
     */
    """
    cur = obj
    for p in path:
        if isinstance(p, str):
            if not isinstance(cur, Mapping) or p not in cur:
                return None
            cur = cur.get(p)
        else:
            if not isinstance(cur, list) or p < 0 or p >= len(cur):
                return None
            cur = cur[p]
    return cur


def _norm_region_key(s: str) -> str:
    """@brief 规范化 region key（lowercase + strip）/ Normalize region key."""
    return s.strip().lower()


@register_optimizer("data_gov_sg_heatmap")
class DataGovSgHeatmapOptimizer:
    """
    /**
     * @brief data.gov.sg → heatmap(points) 归一化优化器 / data.gov.sg → heatmap(points) normalizer.
     *
     * 支持两种模式 / Supports two modes:
     * 1) realtime_region_readings: 适配 /v2/real-time/api/*（regionMetadata + readings）
     * 2) datastore_points: 适配 datastore_search（records + field mapping）
     */
    """

    name: str = "data_gov_sg_heatmap"
    version: str = "0.1.0"

    def optimize(
        self, module: IRModule, *, config: Mapping[str, JsonValue]
    ) -> IRModule:
        """
        /**
         * @brief 优化/归一化 / Optimize/Normalize.
         * @param module 输入 IRModule / Input IRModule.
         * @param config 优化器配置 / Optimizer config.
         * @return 输出 heatmap IRModule / Output heatmap IRModule.
         */
        """
        if not isinstance(module, dict):
            raise SchemaMismatchError("data_gov_sg_heatmap: IRModule must be dict")

        data = module.get("data")
        if data is None:
            raise SchemaMismatchError("data_gov_sg_heatmap: missing module.data")

        mode = (
            config.get("mode")
            if isinstance(config.get("mode"), str)
            else "realtime_region_readings"
        )

        if mode == "realtime_region_readings":
            return self._from_realtime(module, data, config)
        if mode == "datastore_points":
            return self._from_datastore(module, data, config)

        raise SchemaMismatchError(f"data_gov_sg_heatmap: unknown mode={mode}")

    def _from_realtime(
        self, module: IRModule, data: Any, config: Mapping[str, JsonValue]
    ) -> IRModule:
        """
        /**
         * @brief 处理 realtime schema / Handle realtime schema.
         */
        """
        # 默认 path 基于官方示例：{code, errorMsg, data:{regionMetadata, items}}
        root_data = _get_path(data, ["data"]) if isinstance(data, Mapping) else None
        if root_data is None:
            # 有些情况下 frontend 可能已经 extract 了 data，这里做容错
            root_data = data

        region_meta = _get_path(root_data, ["regionMetadata"])
        items = _get_path(root_data, ["items"])

        if (
            not isinstance(region_meta, list)
            or not isinstance(items, list)
            or not items
        ):
            raise SchemaMismatchError(
                "data_gov_sg_heatmap: realtime schema mismatch (regionMetadata/items)"
            )

        # item 选择策略：默认取最后一个（最新）
        item_index = (
            int(config.get("item_index", -1))
            if isinstance(config.get("item_index"), int)
            else -1
        )
        item = (
            items[item_index] if (-len(items) <= item_index < len(items)) else items[-1]
        )
        if not isinstance(item, Mapping):
            raise SchemaMismatchError("data_gov_sg_heatmap: items[*] must be object")

        # timestamp：优先 timestamp，其次 date，再其次 updatedTimestamp
        ts = (
            _as_str(item.get("timestamp"))
            or _as_str(item.get("date"))
            or _as_str(item.get("updatedTimestamp"))
            or ""
        )

        readings = item.get("readings")
        if not isinstance(readings, Mapping):
            raise SchemaMismatchError("data_gov_sg_heatmap: readings must be object")

        # reading_key：比如 pm25_one_hourly / psi_twenty_four_hourly / etc.
        reading_key = config.get("reading_key")
        if not isinstance(reading_key, str) or not reading_key:
            # 如果没给，就在 readings 里挑第一个 key（保守但可用）
            reading_key = next(iter(readings.keys()), "")
        series = readings.get(reading_key)
        if not isinstance(series, Mapping):
            raise SchemaMismatchError(
                f"data_gov_sg_heatmap: readings[{reading_key}] must be object"
            )

        # 建 region -> (lat, lon, name)
        loc: Dict[str, Tuple[float, float, str]] = {}
        for r in region_meta:
            if not isinstance(r, Mapping):
                continue
            name = _as_str(r.get("name")) or ""
            ll = r.get("labelLocation")
            if not isinstance(ll, Mapping):
                continue
            lat = _as_float(ll.get("latitude"))
            lon = _as_float(ll.get("longitude"))
            if lat is None or lon is None or not name:
                continue
            loc[_norm_region_key(name)] = (lat, lon, name)

        points: List[Dict[str, JsonValue]] = []
        vmin: Optional[float] = None
        vmax: Optional[float] = None
        vsum: float = 0.0

        for k, v in series.items():
            rk = _norm_region_key(str(k))
            vv = _as_float(v)
            if vv is None:
                continue
            if rk not in loc:
                # 坐标缺失就跳过（或你也可以选择输出但标记 missing_location）
                continue
            lat, lon, disp = loc[rk]
            points.append({"id": rk, "name": disp, "lat": lat, "lon": lon, "value": vv})

            vmin = vv if vmin is None else min(vmin, vv)
            vmax = vv if vmax is None else max(vmax, vv)
            vsum += vv

        out: IRModule = {
            "ir_kind": "heatmap",
            "provenance": module.get("provenance", {}),
            "spec": {
                "geometry": "points",
                "value_unit": (
                    config.get("value_unit")
                    if isinstance(config.get("value_unit"), str)
                    else "unknown"
                ),
                "value_semantics": (
                    config.get("value_semantics")
                    if isinstance(config.get("value_semantics"), str)
                    else "intensity"
                ),
                "source_mode": "realtime_region_readings",
                "reading_key": reading_key,
            },
            "data": {
                "timestamp": ts,
                "points": points,
                "stats": {
                    "count": len(points),
                    "min": vmin if vmin is not None else 0,
                    "max": vmax if vmax is not None else 0,
                    "sum": vsum,
                },
            },
        }
        return out

    def _from_datastore(
        self, module: IRModule, data: Any, config: Mapping[str, JsonValue]
    ) -> IRModule:
        """
        /**
         * @brief 处理 datastore_search schema / Handle datastore_search schema.
         */
        """
        # 期望：{success, result:{records:[...]}}
        result = _get_path(data, ["result"]) if isinstance(data, Mapping) else None
        records = (
            _get_path(result, ["records"]) if isinstance(result, Mapping) else None
        )
        if not isinstance(records, list):
            raise SchemaMismatchError(
                "data_gov_sg_heatmap: datastore schema mismatch (result.records)"
            )

        lat_f = config.get("lat_field")
        lon_f = config.get("lon_field")
        val_f = config.get("value_field")
        ts_f = config.get("timestamp_field")

        if not all(
            isinstance(x, str) and x for x in [lat_f, lon_f, val_f]
        ):  # timestamp 可选
            raise SchemaMismatchError(
                "data_gov_sg_heatmap: require lat_field/lon_field/value_field"
            )

        points: List[Dict[str, JsonValue]] = []
        for row in records:
            if not isinstance(row, Mapping):
                continue
            lat = _as_float(row.get(lat_f))  # type: ignore[arg-type]
            lon = _as_float(row.get(lon_f))  # type: ignore[arg-type]
            val = _as_float(row.get(val_f))  # type: ignore[arg-type]
            if lat is None or lon is None or val is None:
                continue
            p: Dict[str, JsonValue] = {"lat": lat, "lon": lon, "value": val}
            if isinstance(ts_f, str) and ts_f:
                tsv = row.get(ts_f)
                if isinstance(tsv, str):
                    p["timestamp"] = tsv
            points.append(p)

        out: IRModule = {
            "ir_kind": "heatmap",
            "provenance": module.get("provenance", {}),
            "spec": {
                "geometry": "points",
                "value_unit": (
                    config.get("value_unit")
                    if isinstance(config.get("value_unit"), str)
                    else "unknown"
                ),
                "value_semantics": (
                    config.get("value_semantics")
                    if isinstance(config.get("value_semantics"), str)
                    else "intensity"
                ),
                "source_mode": "datastore_points",
            },
            "data": {"points": points, "stats": {"count": len(points)}},
        }
        return out
