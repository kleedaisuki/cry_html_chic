"""
/**
 * @file bus_route_optimizer.py
 * @brief 公交线路优化器：从原始数据生成公交线路数据。
 *        Bus route optimizer: Generate bus route data from raw data.
 *
 * 功能 / Features:
 * - 读取公交线路数据（ServiceNo, Direction, StopSequence, BusStopCode）
 * - 读取公交站点数据（BusStopCode, Latitude, Longitude）
 * - 按线路和方向分组，生成前端路由格式
 * - 输出 routes.js 格式的数据
 *
 * 配置项 / Config options:
 * - bus_routes_dataset: 公交线路数据集名称
 * - bus_stops_dataset: 公交站点数据集名称
 * - output_path: 输出文件路径（可选）
 * - output_format: 输出格式 ("routes_js" | "json")
 */
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Set

from ingest.utils.logger import get_logger
from ingest.wiring import register_optimizer
from ingest.transform.interface import IRModule, JsonValue, Optimizer

_LOG = get_logger(__name__)

# 全局缓存
_bus_stops_cache: Optional[Dict[str, Dict[str, Any]]] = None


def _load_bus_stops_from_module(
    routes_module: Optional[IRModule],
    stops_module: Optional[IRModule],
) -> Dict[str, Dict[str, Any]]:
    """
    @brief 从 IRModule 加载公交站点数据 / Load bus stops from IRModule.
    """
    global _bus_stops_cache
    if _bus_stops_cache is not None:
        return _bus_stops_cache

    bus_stops: Dict[str, Dict[str, Any]] = {}

    # 从 routes_module 加载
    if routes_module and isinstance(routes_module.get("data"), list):
        for record in routes_module["data"]:
            if isinstance(record, dict):
                bus_stop_code = record.get("BusStopCode")
                if bus_stop_code:
                    bus_stops[bus_stop_code] = {
                        "code": bus_stop_code,
                        "description": record.get("Description", ""),
                        "latitude": record.get("Latitude"),
                        "longitude": record.get("Longitude"),
                        "road_name": record.get("RoadName", ""),
                    }

    # 从 stops_module 加载（覆盖或补充）
    if stops_module and isinstance(stops_module.get("data"), list):
        for record in stops_module["data"]:
            if isinstance(record, dict):
                bus_stop_code = record.get("BusStopCode")
                if bus_stop_code and bus_stop_code not in bus_stops:
                    bus_stops[bus_stop_code] = {
                        "code": bus_stop_code,
                        "description": record.get("Description", ""),
                        "latitude": record.get("Latitude"),
                        "longitude": record.get("Longitude"),
                        "road_name": record.get("RoadName", ""),
                    }

    _LOG.info("bus_route: loaded %d bus stops", len(bus_stops))
    _bus_stops_cache = bus_stops
    return bus_stops


def _build_bus_routes(
    route_data: List[Dict[str, Any]],
    bus_stops: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    @brief 构建公交线路数据 / Build bus route data.
    """
    # 按 (ServiceNo, Direction) 分组
    route_groups: Dict[str, List[Dict[str, Any]]] = {}

    for record in route_data:
        if not isinstance(record, dict):
            continue

        service_no = record.get("ServiceNo")
        direction = record.get("Direction", 1)

        if not service_no:
            continue

        key = f"{service_no}_{direction}"
        if key not in route_groups:
            route_groups[key] = []

        route_groups[key].append(record)

    # 构建线路数据
    bus_routes: Dict[str, Dict[str, Any]] = {}

    for key, records in route_groups.items():
        # 按 StopSequence 排序
        sorted_records = sorted(records, key=lambda x: x.get("StopSequence", 0))

        # 生成线路 ID
        service_no = sorted_records[0].get("ServiceNo", "") if sorted_records else ""
        direction = sorted_records[0].get("Direction", 1) if sorted_records else 1
        route_id = f"BUS_{service_no}_{direction}"

        # 构建站点列表
        stations = []
        coordinates = []

        for record in sorted_records:
            stop_code = record.get("BusStopCode")
            if not stop_code:
                continue

            stop_info = bus_stops.get(stop_code, {})
            latitude = stop_info.get("latitude") or record.get("Latitude")
            longitude = stop_info.get("longitude") or record.get("Longitude")

            if latitude and longitude:
                station = {
                    "id": stop_code,
                    "name": stop_info.get("description", record.get("Description", f"Stop {stop_code}")),
                    "position": [longitude, latitude],  # [lng, lat] for GeoJSON
                }
                stations.append(station)
                coordinates.append([longitude, latitude])

        if len(stations) < 2:
            _LOG.warning("bus_route: %s has fewer than 2 stops, skipping", route_id)
            continue

        # 确定运营者
        operator = sorted_records[0].get("Operator", "Unknown") if sorted_records else "Unknown"

        bus_routes[route_id] = {
            "name": f"Bus {service_no}",
            "type": "bus",
            "color": "#e6550d",  # 默认橙色
            "description": f"Bus {service_no} - {operator}",
            "operator": operator,
            "direction": direction,
            "stations": stations,
            "coordinates": coordinates,
        }

        _LOG.info("bus_route: built route %s with %d stations", route_id, len(stations))

    return bus_routes


def _generate_routes_js(bus_routes: Dict[str, Dict[str, Any]]) -> str:
    """
    @brief 生成 routes.js 格式的内容 / Generate routes.js format content.
    """
    lines = [
        "/**",
        " * 新加坡公交线路数据（自动生成）",
        " * Singapore Bus Routes Data (Auto-generated)",
        " * Generated by bus_route_optimizer",
        " */",
        "",
        "window.ROUTES = {",
    ]

    for route_id, route_info in bus_routes.items():
        lines.append(f'    "{route_id}": {{')
        lines.append(f'        "name": "{route_info["name"]}",')
        lines.append(f'        "type": "{route_info["type"]}",')
        lines.append(f'        "color": "{route_info["color"]}",')
        lines.append(f'        "description": "{route_info["description"]}",')

        # 坐标
        coords = route_info.get("coordinates", [])
        if coords:
            lines.append('        "coordinates": [')
            for i, coord in enumerate(coords):
                comma = "," if i < len(coords) - 1 else ""
                lines.append(f'            [{coord[0]}, {coord[1]}]{comma}')
            lines.append('        ],')

        # 站点
        stations = route_info.get("stations", [])
        if stations:
            lines.append('        "stations": [')
            for i, station in enumerate(stations):
                comma = "," if i < len(stations) - 1 else ""
                lines.append(
                    f'            {{"id": "{station["id"]}", "name": "{station["name"]}", "position": [{station["position"][0]}, {station["position"][1]}]}}{comma}'
                )
            lines.append('        ]')

        lines.append('    },')

    lines.append("};")
    lines.append("")
    lines.append("// 导出（用于模块系统）")
    lines.append("if (typeof module !== 'undefined' && module.exports) {")
    lines.append("    module.exports = window.ROUTES;")
    lines.append("}")

    return "\n".join(lines)


@register_optimizer("bus_route_processing")
class BusRouteOptimizer(Optimizer):
    """
    @brief 公交线路优化器 / Bus route optimizer.

    功能 / Features:
    - 从原始公交数据生成线路数据
    - 关联站点坐标
    - 输出前端可用格式
    """

    name: str = "bus_route_processing"
    version: str = "0.1.0"

    def optimize(
        self, module: IRModule, *, config: Mapping[str, JsonValue]
    ) -> IRModule:
        """
        @brief 执行公交线路处理 / Perform bus route processing.

        @param module 输入 IRModule / Input IRModule.
        @param config 优化器配置 / Optimizer config.
        @return 处理后的 IRModule / Processed IRModule.
        """
        output_format = str(config.get("output_format", "routes_js"))
        output_path = config.get("output_path")

        # 提取数据
        data = module.get("data")
        if not isinstance(data, list):
            _LOG.warning("bus_route: module.data is not a list")
            return dict(module)

        # 加载公交站点数据
        bus_stops = _load_bus_stops_from_module(module, None)

        if not bus_stops:
            _LOG.warning("bus_route: no bus stops found, cannot build routes")
            return dict(module)

        # 构建公交线路
        bus_routes = _build_bus_routes(data, bus_stops)

        _LOG.info("bus_route: built %d bus routes", len(bus_routes))

        # 生成输出
        if output_format == "routes_js":
            output_content = _generate_routes_js(bus_routes)

            # 如果指定了输出路径，写入文件
            if output_path:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(output_content)
                _LOG.info("bus_route: wrote routes.js to %s", output_path)

            output: IRModule = {
                "ir_kind": "bus_routes",
                "provenance": dict(module.get("provenance", {})),
                "data": {
                    "routes": bus_routes,
                    "routes_js": output_content,
                },
            }
        else:
            # JSON 格式输出
            output = {
                "ir_kind": "bus_routes",
                "provenance": dict(module.get("provenance", {})),
                "data": bus_routes,
            }

        # 添加处理信息到 provenance
        output["provenance"]["bus_route_processing"] = {
            "optimizer": f"{self.name}@{self.version}",
            "output_format": output_format,
            "route_count": len(bus_routes),
        }

        return output


if __name__ == "__main__":
    # 测试
    print("Bus Route Optimizer - Test")
    print("This optimizer is designed to be run within the data pipeline.")
