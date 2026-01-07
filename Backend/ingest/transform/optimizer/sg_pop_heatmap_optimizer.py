from __future__ import annotations

"""
/**
 * @file sg_pop_heatmap_optimizer.py
 * @brief 新加坡人口热力图数据清洗优化器 / Singapore Population Heatmap Data Cleaning Optimizer.
 *
 * 本优化器将 data.gov.sg 的人口普查数据转换为热力图格式，
 * 使用预定义的规划区域坐标映射。
 * This optimizer converts Singapore census data from data.gov.sg into heatmap format,
 * using a predefined mapping of planning area names to coordinates.
 */
"""

from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

from ingest.transform.interface import IRModule, JsonValue, SchemaMismatchError
from ingest.wiring import register_optimizer


JsonObj = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


def _as_str(x: Any) -> Optional[str]:
    """@brief 安全转字符串 / Safe str cast."""
    if isinstance(x, str):
        return x.strip()
    if x is None:
        return None
    return str(x)


def _as_float(x: Any) -> Optional[float]:
    """@brief 安全转浮点 / Safe float cast."""
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x.replace(",", ""))
        except ValueError:
            return None
    return None


def _normalize_name(s: str) -> str:
    """@brief 规范化区域名称（lowercase + 移除后缀）/ Normalize area name."""
    s = s.strip().lower()
    # 移除常见的区域类型后缀
    for suffix in [" - total", " town centre", " planning area"]:
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    return s


# 新加坡55个规划区域中心坐标映射
# Singapore 55 Planning Area Center Coordinates
SG_PLANNING_AREA_COORDS: Dict[str, Tuple[float, float]] = {
    "ang mo kio": (1.3691, 103.8454),
    "bedok": (1.3236, 103.9273),
    "bishan": (1.3526, 103.8352),
    "bukit batok": (1.3590, 103.7637),
    "bukit merah": (1.2819, 103.8239),
    "bukit panjang": (1.3774, 103.7719),
    "bukit timah": (1.3294, 103.8021),
    "central water catch": (1.3403, 103.7880),
    "changi": (1.3380, 103.9871),
    "changi bay": (1.3362, 104.0037),
    "choa chu kang": (1.3840, 103.7470),
    "clementi": (1.3162, 103.7649),
    "downtown core": (1.2789, 103.8536),
    "geylang": (1.3201, 103.8918),
    "hougang": (1.3612, 103.8863),
    "jurong east": (1.3329, 103.7436),
    "jurong west": (1.3404, 103.7090),
    "kallang": (1.3100, 103.8651),
    "lim chu kang": (1.4305, 103.7174),
    "mandai": (1.4131, 103.8180),
    "marina south": (1.2705, 103.8638),
    "marine parade": (1.3020, 103.9072),
    "museum": (1.2998, 103.8354),
    "newton": (1.3294, 103.8354),
    "north-eastern islands": (1.2915, 103.8495),
    "orchard": (1.3045, 103.8328),
    "outram": (1.2889, 103.8376),
    "pasir ris": (1.3721, 103.9474),
    "paya lebar": (1.3570, 103.9153),
    "pioneer": (1.3254, 103.6782),
    "queenstown": (1.2942, 103.7861),
    "river valley": (1.2892, 103.8458),
    "rochor": (1.3045, 103.8558),
    "seletar": (1.4040, 103.8674),
    "sembawang": (1.4491, 103.8185),
    "sengkang": (1.3868, 103.8914),
    "serangoon": (1.3554, 103.8679),
    "southern islands": (1.2167, 103.8333),
    "straits view": (1.2645, 103.8558),
    "sungei kadut": (1.4230, 103.7645),
    "tampines": (1.3496, 103.9568),
    "tengah": (1.3920, 103.7360),
    "toa payoh": (1.3343, 103.8563),
    "tuas": (1.3060, 103.6350),
    "western islands": (1.2500, 103.8000),
    "western water catch": (1.3333, 103.7167),
    "woodlands": (1.4382, 103.7890),
    "yishun": (1.4304, 103.8354),
}

# 需要跳过的特殊条目
SKIP_NAMES = {"total", "total resident", "total population"}


@register_optimizer("sg_pop_heatmap")
class SingaporePopulationHeatmapOptimizer:
    """
    /**
     * @brief 新加坡人口数据 → 人口热力图优化器 / Singapore Population Data → Population Heatmap Optimizer.
     *
     * 输入：data.gov.sg 人口普查数据（按规划区域/分区的数据）
     * 输出：热力图点数据 [{ name, value, lat, lon }]
     */
    """

    name: str = "sg_pop_heatmap"
    version: str = "0.1.0"

    def optimize(
        self, module: IRModule, *, config: Mapping[str, JsonValue]
    ) -> IRModule:
        """
        /**
         * @brief 优化/清洗人口数据 / Optimize/Clean population data.
         * @param module 输入 IRModule / Input IRModule.
         * @param config 优化器配置 / Optimizer config.
         * @return 输出 heatmap IRModule / Output heatmap IRModule.
         */
        """
        if not isinstance(module, dict):
            raise SchemaMismatchError("sg_pop_heatmap: IRModule must be dict")

        data = module.get("data")
        if data is None:
            raise SchemaMismatchError("sg_pop_heatmap: missing module.data")

        # 适配 datastore_search 的 result.records 结构
        result = data.get("result") if isinstance(data, Mapping) else None
        records = result.get("records") if isinstance(result, Mapping) else None

        # 如果已经是 records 列表，直接使用
        if isinstance(records, list):
            raw_records = records
        elif isinstance(data, list):
            raw_records = data
        else:
            raise SchemaMismatchError(
                "sg_pop_heatmap: cannot find records in data.result.records or data"
            )

        # 字段名配置
        name_field = _as_str(config.get("name_field")) or "Number"
        value_field = _as_str(config.get("value_field")) or "Total_Total"

        points: List[Dict[str, JsonValue]] = []
        vmin: Optional[float] = None
        vmax: Optional[float] = None
        vsum: float = 0.0
        skipped = 0
        matched = 0

        for row in raw_records:
            if not isinstance(row, Mapping):
                continue

            # 提取区域名称和人口值
            name_raw = _as_str(row.get(name_field))
            if not name_raw:
                continue

            name_norm = _normalize_name(name_raw)

            # 跳过汇总行
            if name_norm in SKIP_NAMES:
                skipped += 1
                continue

            # 查找坐标
            coords = SG_PLANNING_AREA_COORDS.get(name_norm)
            if coords is None:
                # 尝试模糊匹配
                coords = self._fuzzy_match(name_norm)
                if coords is None:
                    skipped += 1
                    continue

            value = _as_float(row.get(value_field))
            if value is None:
                continue

            lat, lon = coords
            points.append({
                "name": name_raw,
                "value": value,
                "lat": lat,
                "lon": lon
            })

            vmin = value if vmin is None else min(vmin, value)
            vmax = value if vmax is None else max(vmax, value)
            vsum += value
            matched += 1

        out: IRModule = {
            "ir_kind": "population_heatmap",
            "provenance": module.get("provenance", {}),
            "spec": {
                "geometry": "points",
                "value_unit": "population",
                "value_semantics": "intensity",
                "source_mode": "census_planning_area",
            },
            "data": {
                "points": points,
                "stats": {
                    "count": matched,
                    "min": vmin if vmin is not None else 0,
                    "max": vmax if vmax is not None else 0,
                    "sum": vsum,
                    "skipped": skipped,
                },
            },
        }

        return out

    def _fuzzy_match(self, name: str) -> Optional[Tuple[float, float]]:
        """@brief 模糊匹配区域名称 / Fuzzy match area name."""
        # 尝试部分匹配
        for key in SG_PLANNING_AREA_COORDS:
            if key in name or name in key:
                return SG_PLANNING_AREA_COORDS[key]
        return None
