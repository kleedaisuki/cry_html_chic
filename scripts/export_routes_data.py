#!/usr/bin/env python3
"""
导出 OSM 数据到前端格式
将 preprocessed 的 routes_*.json 转换为 Frontend/data/*.js 格式
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
FRONTEND_DATA_DIR = PROJECT_ROOT / "Frontend" / "data"
PREPROCESSED_DIR = PROJECT_ROOT / "Backend" / "data" / "preprocessed"

# 颜色配置（根据 route 类型）
TRANSPORT_COLORS = {
    "subway": "#e41a1c",  # 红色 - MRT
    "light_rail": "#ff7f00",  # 橙色 - LRT
    "bus": "#4daf4a",  # 绿色 - Bus
}

# 线路名称映射（OSM relation name -> 前端 ID）
ROUTE_NAME_MAP = {
    "North South Line": "NS_LINE",
    "East West Line": "EW_LINE",
    "Circle Line": "CC_LINE",
    "North East Line": "NE_LINE",
    "Downtown Line": "DT_LINE",
    "Thomson-East Coast Line": "TE_LINE",
    "Circle Line Extension": "CCE_LINE",
    "Bukit Panjang LRT": "BP_LRT",
    "Sengkang LRT": "SK_LRT",
    "Punggol LRT": "PG_LRT",
    "Changi Airport Branch": "CA_BRANCH",
}


def find_latest_preprocessed(config_name: str) -> Path | None:
    """找到指定配置的最新 preprocessed 目录"""
    if not PREPROCESSED_DIR.exists():
        return None

    dirs = sorted(
        [d for d in PREPROCESSED_DIR.iterdir() if d.is_dir() and config_name in d.name],
        key=lambda d: d.name,
        reverse=True,
    )
    return dirs[0] if dirs else None


def load_geojson_featurecollection(path: Path) -> Dict[str, Any]:
    """加载 GeoJSON FeatureCollection"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_route_info_from_relation(feature: Dict[str, Any]) -> Dict[str, Any]:
    """从 GeoJSON Feature 中提取线路信息"""
    props = feature.get("properties", {})
    tags = props.get("tags", {})

    # 获取线路名称
    route_name = tags.get("name", "")
    route_ref = tags.get("ref", "")
    route_type = tags.get("route", "bus")  # subway, light_rail, bus
    operator = tags.get("operator", "")
    network = tags.get("network", "")

    # 生成前端 ID
    route_id = _generate_route_id(route_name, route_ref, route_type)

    # 获取颜色
    colour = tags.get("colour") or tags.get("color", "")

    # 获取几何
    geom = feature.get("geometry", {})
    if geom.get("type") == "GeometryCollection":
        coordinates = _extract_geometry_coords(geom)
    else:
        coordinates = _extract_simple_geom_coords(geom)

    return {
        "id": route_id,
        "name": route_name,
        "ref": route_ref,
        "type": route_type,
        "colour": colour or TRANSPORT_COLORS.get(route_type, "#4daf4a"),
        "operator": operator,
        "network": network,
        "coordinates": coordinates,
        "stations": [],  # OSM 数据没有站点信息，需要单独获取
    }


def _generate_route_id(name: str, ref: str, route_type: str) -> str:
    """生成路由 ID"""
    # 优先使用已知映射
    for osm_name, frontend_id in ROUTE_NAME_MAP.items():
        if osm_name.lower() in name.lower():
            return frontend_id

    # 尝试从 ref 生成（如 "NS1" -> "NS_LINE"）
    if ref:
        prefix = "".join([c for c in ref.upper() if c.isalpha()])[:2]
        if prefix in ["NS", "EW", "CC", "NE", "DT", "TE", "BP", "SK", "PG"]:
            return f"{prefix}_LINE"

    # 使用 name 生成
    safe_name = "".join(c for c in name if c.isalnum() or c in " -").strip()
    safe_name = safe_name.replace(" ", "_").upper()[:20]
    return f"ROUTE_{safe_name}"


def _extract_geometry_coords(geom: Dict[str, Any]) -> list:
    """从 GeometryCollection 提取坐标（简化版：只取前500个点）"""
    coords = []
    max_points = 500  # 限制每个线路的坐标点数量

    for g in geom.get("geometries", [])[:20]:  # 最多20个几何对象
        if len(coords) >= max_points:
            break
        if g.get("type") == "LineString":
            coords.extend(g.get("coordinates", [])[:max_points - len(coords)])
        elif g.get("type") == "Polygon":
            rings = g.get("coordinates", [])
            if rings:
                coords.extend(rings[0][:max_points - len(coords)])
    return coords[:max_points]


def _extract_simple_geom_coords(geom: Dict[str, Any]) -> list:
    """从简单几何提取坐标"""
    if geom.get("type") == "LineString":
        return geom.get("coordinates", [])
    elif geom.get("type") == "Polygon":
        rings = geom.get("coordinates", [])
        return rings[0] if rings else []
    return []


def convert_routes_geojson_to_frontend(geojson_path: Path) -> Dict[str, Any]:
    """将 GeoJSON 转换为前端格式"""
    data = load_geojson_featurecollection(geojson_path)

    features = data.get("data", {}).get("features", [])
    routes = {}

    for feature in features:
        # 只处理 relation
        osm_type = feature.get("properties", {}).get("osm_type", "")
        if osm_type != "relation":
            continue

        route_info = extract_route_info_from_relation(feature)
        route_id = route_info["id"]

        if route_id not in routes:
            routes[route_id] = route_info

    return routes


def generate_routes_js(routes: Dict[str, Any]) -> str:
    """生成 routes.js 文件内容（紧凑格式）"""
    lines = [
        "/**",
        " * 新加坡公共交通线路数据",
        " * Singapore Transit Routes Data",
        " * Auto-generated from OSM data",
        " */",
        "",
        "window.ROUTES = {",
    ]

    for route_id, route in sorted(routes.items()):
        # 使用紧凑的 JSON 格式
        coords_json = json.dumps(route["coordinates"], separators=(",", ":"))

        lines.append(f'    "{route_id}":{{')
        lines.append(f'        "name":"{route["name"]}",')
        lines.append(f'        "type":"{route["type"]}",')
        lines.append(f'        "colour":"{route["colour"]}",')
        lines.append(f'        "coordinates":{coords_json},')
        lines.append('        "stations":[]')
        lines.append("    }},")

    lines.append("};")
    lines.append("")

    return "\n".join(lines)


def main():
    """主函数"""
    print("=== OSM Routes 数据导出工具 ===\n")

    # 查找最新的 routes 数据
    latest_pp = find_latest_preprocessed("routes-geo-osm")
    if not latest_pp:
        print("错误: 未找到 preprocessed 数据")
        print(f"请先运行: python -m ingest.cli.main run routes_geo_osm")
        return 1

    print(f"使用 preprocessed 目录: {latest_pp.name}\n")

    # 加载 MRT 数据
    mrt_path = latest_pp / "artifacts" / "constants" / "routes_mrt.json"
    if mrt_path.exists():
        print("处理 MRT 数据...")
        mrt_routes = convert_routes_geojson_to_frontend(mrt_path)
        print(f"  找到 {len(mrt_routes)} 条 MRT 线路")
    else:
        print(f"  MRT 数据不存在: {mrt_path}")
        mrt_routes = {}

    # 加载 LRT 数据
    lrt_path = latest_pp / "artifacts" / "constants" / "routes_lrt.json"
    if lrt_path.exists():
        print("处理 LRT 数据...")
        lrt_routes = convert_routes_geojson_to_frontend(lrt_path)
        print(f"  找到 {len(lrt_routes)} 条 LRT 线路")
    else:
        print(f"  LRT 数据不存在: {lrt_path}")
        lrt_routes = {}

    # 加载 Bus 数据
    bus_path = latest_pp / "artifacts" / "constants" / "routes_bus.json"
    if bus_path.exists():
        print("处理 Bus 数据...")
        bus_routes = convert_routes_geojson_to_frontend(bus_path)
        print(f"  找到 {len(bus_routes)} 条 Bus 线路")
    else:
        print(f"  Bus 数据不存在: {bus_path}")
        bus_routes = {}

    # 合并所有线路
    all_routes = {**mrt_routes, **lrt_routes, **bus_routes}
    print(f"\n总计: {len(all_routes)} 条线路")

    # 生成 routes.js
    routes_js = generate_routes_js(all_routes)

    # 写入文件
    output_path = FRONTEND_DATA_DIR / "routes.js"
    FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(routes_js)

    print(f"\n已生成: {output_path}")
    print(f"文件大小: {os.path.getsize(output_path)} bytes")

    return 0


if __name__ == "__main__":
    exit(main())
