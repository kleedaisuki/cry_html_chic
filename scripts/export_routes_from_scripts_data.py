#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
/**
 * @file export_routes_from_scripts_data.py
 * @brief 从 scripts/data 下读取 routes_*.json，导出前端可用 routes.js（对齐 export_routes_data.py）/
 *        Export routes.js from scripts/data routes json files (aligned with export_routes_data.py).
 *
 * 设计原则 / Design principles:
 * - 同一 Frontend ABI（window.ROUTES schema + route_id 规则 + 输出格式）/ Same Frontend ABI
 * - 仅输入源不同（scripts/data vs preprocessed）/ Only data source differs
 * - Geometry 展平支持多种 GeoJSON 类型 / Flatten multiple GeoJSON geometry types
 */
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# Paths / 路径
# ============================================================

"""
/**
 * @brief 计算项目根目录 / Compute project root.
 * @note 假设脚本位于 <repo>/scripts/ 下（或类似层级）。/ Assumes script is under <repo>/scripts/.
 */
"""
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "scripts" / "data"
FRONTEND_DATA_DIR = PROJECT_ROOT / "Frontend" / "data"
OUTPUT_PATH = FRONTEND_DATA_DIR / "routes.js"


# ============================================================
# Frontend ABI constants / 前端协议常量
# （对齐 export_routes_data.py）
# ============================================================

"""
/**
 * @brief 交通类型默认色 / Default colours by transport type.
 * @note 对齐 export_routes_data.py（subway/light_rail/bus 语义）。/ Aligned with export_routes_data.py.
 */
"""
TRANSPORT_COLORS: Dict[str, str] = {
    "subway": "#e41a1c",  # Red - MRT
    "light_rail": "#ff7f00",  # Orange - LRT
    "bus": "#4daf4a",  # Green - Bus
}

"""
/**
 * @brief 线路名映射（OSM relation name -> 前端 route_id）/
 *        Route name mapping (OSM relation name -> frontend route_id).
 */
"""
ROUTE_NAME_MAP: Dict[str, str] = {
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

"""
/**
 * @brief 输入文件列表（route_type, filename）/ Input files list (route_type, filename).
 * @note route_type 取值保持与 export_routes_data.py 一致：subway/light_rail/bus。
 */
"""
INPUT_FILES: List[Tuple[str, str]] = [
    ("subway", "routes_mrt.json"),
    ("light_rail", "routes_lrt.json"),
    ("bus", "routes_bus.json"),  # 可选：如果存在就导出
]


# ============================================================
# Schema helpers / 数据结构辅助
# ============================================================

def extract_feature_collection(doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    /**
     * @brief 从 IRModule 或纯 GeoJSON 中提取 FeatureCollection /
     *        Extract FeatureCollection from IRModule or pure GeoJSON.
     *
     * @param doc 输入 JSON 文档 / Input JSON document
     * @return FeatureCollection dict 或 None / FeatureCollection dict or None
     */
    """
    if not isinstance(doc, dict):
        return None

    # IRModule: {"ir_kind":"geojson","data":{FeatureCollection}}
    if doc.get("ir_kind") == "geojson":
        fc = doc.get("data")
        if isinstance(fc, dict) and fc.get("type") == "FeatureCollection":
            return fc

    # Pure GeoJSON FeatureCollection
    if doc.get("type") == "FeatureCollection":
        return doc

    # 兼容某些包装：{"data": {"type":"FeatureCollection", ...}}
    maybe = doc.get("data")
    if isinstance(maybe, dict) and maybe.get("type") == "FeatureCollection":
        return maybe

    return None


def flatten_geometry(geom: Dict[str, Any], limit: int = 5000) -> List[List[float]]:
    """
    /**
     * @brief 拉平 GeoJSON geometry 为点序列 / Flatten GeoJSON geometry into coordinate list.
     *
     * @param geom GeoJSON geometry / GeoJSON geometry
     * @param limit 最大点数限制 / Max number of points
     * @return 坐标列表 [[lon, lat], ...] / Coordinate list [[lon, lat], ...]
     */
    """
    out: List[List[float]] = []

    def push(pt: Any) -> None:
        if len(out) >= limit:
            return
        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
            out.append([float(pt[0]), float(pt[1])])

    gtype = geom.get("type")
    coords = geom.get("coordinates")

    if gtype == "LineString":
        for pt in coords or []:
            push(pt)

    elif gtype == "MultiLineString":
        for line in coords or []:
            for pt in line or []:
                push(pt)

    elif gtype == "Polygon":
        if coords:
            ring0 = coords[0] if isinstance(coords, list) and len(coords) > 0 else []
            for pt in ring0 or []:
                push(pt)

    elif gtype == "MultiPolygon":
        # 取第一个 polygon 的外环
        if coords and isinstance(coords, list) and len(coords) > 0:
            poly0 = coords[0]
            if poly0 and isinstance(poly0, list) and len(poly0) > 0:
                ring0 = poly0[0]
                for pt in ring0 or []:
                    push(pt)

    elif gtype == "GeometryCollection":
        for g in geom.get("geometries", []) or []:
            if not isinstance(g, dict):
                continue
            out.extend(flatten_geometry(g, limit - len(out)))

    return out


# ============================================================
# Route ID + type normalization / 路由 ID 与类型归一化
# ============================================================

def normalize_route_type(route_type: str) -> str:
    """
    /**
     * @brief 归一化 route_type（与 export_routes_data.py 对齐）/
     *        Normalize route_type aligned with export_routes_data.py.
     *
     * @param route_type 输入类型 / Input type
     * @return 标准类型：subway/light_rail/bus / Normalized type
     */
    """
    rt = (route_type or "").strip().lower()
    if rt in ("mrt", "subway"):
        return "subway"
    if rt in ("lrt", "light_rail", "lightrail"):
        return "light_rail"
    if rt in ("bus",):
        return "bus"
    return rt or "bus"


def generate_route_id(name: str, ref: str, route_type: str) -> str:
    """
    /**
     * @brief 生成前端 route_id（完全复用 export_routes_data.py 语义）/
     *        Generate frontend route_id (same semantics as export_routes_data.py).
     *
     * @param name 线路名 / Route name
     * @param ref 线路编号 / Route ref
     * @param route_type 线路类型 / Route type
     * @return 前端 route_id / Frontend route_id
     */
    """
    # 优先使用已知映射 / Prefer known mapping
    for osm_name, frontend_id in ROUTE_NAME_MAP.items():
        if name and osm_name.lower() in name.lower():
            return frontend_id

    # 尝试从 ref 推断 / Infer from ref
    if ref:
        prefix = "".join([c for c in ref.upper() if c.isalpha()])[:2]
        if prefix in ["NS", "EW", "CC", "NE", "DT", "TE", "BP", "SK", "PG"]:
            return f"{prefix}_LINE"

    # fallback: name -> ROUTE_XXX
    safe_name = "".join(c for c in (name or "") if c.isalnum() or c in " -").strip()
    safe_name = safe_name.replace(" ", "_").upper()[:20]
    return f"ROUTE_{safe_name}"


def generate_routes_js(routes: Dict[str, Any]) -> str:
    """
    /**
     * @brief 生成 routes.js 内容（紧凑格式，匹配 export_routes_data.py）/
     *        Generate routes.js content (compact format, matching export_routes_data.py).
     *
     * @param routes routes dict / routes dict
     * @return routes.js 文本 / routes.js text
     */
    """
    lines = [
        "/**",
        " * 新加坡公共交通线路数据",
        " * Singapore Transit Routes Data",
        " * Auto-generated from scripts/data",
        " */",
        "",
        "window.ROUTES = {",
    ]

    for route_id, route in sorted(routes.items()):
        coords_json = json.dumps(route["coordinates"], separators=(",", ":"))

        lines.append(f'    "{route_id}":{{')
        lines.append(f'        "name":"{route["name"]}",')
        lines.append(f'        "type":"{route["type"]}",')
        lines.append(f'        "colour":"{route["colour"]}",')
        lines.append(f'        "coordinates":{coords_json},')
        lines.append('        "stations":[]')
        lines.append("    },")  # keep trailing comma to match existing style

    lines.append("};")
    lines.append("")
    return "\n".join(lines)


# ============================================================
# Main / 主流程
# ============================================================

def main() -> int:
    """
    /**
     * @brief 脚本入口 / Script entry.
     * @return 进程退出码 / Process exit code
     */
    """
    routes: Dict[str, Dict[str, Any]] = {}

    if not DATA_DIR.exists():
        print(f"[error] scripts/data not found: {DATA_DIR}")
        return 2

    for input_route_type, filename in INPUT_FILES:
        input_route_type = normalize_route_type(input_route_type)
        path = DATA_DIR / filename
        if not path.exists():
            print(f"[skip] {filename} not found under {DATA_DIR}")
            continue

        doc = json.loads(path.read_text(encoding="utf-8"))
        fc = extract_feature_collection(doc)
        if not fc:
            print(f"[skip] {filename} is not GeoJSON FeatureCollection (or IRModule geojson)")
            continue

        feats = fc.get("features", []) or []
        for feat in feats:
            if not isinstance(feat, dict):
                continue

            props = feat.get("properties") or {}
            tags = props.get("tags") or {}

            # 与 export_routes_data.py 一致：若标明 osm_type，优先只处理 relation
            osm_type = props.get("osm_type")
            if osm_type is not None and osm_type != "relation":
                continue

            name = (tags.get("name") or props.get("name") or "").strip()
            ref = (tags.get("ref") or props.get("ref") or "").strip()

            # route_type：优先 tags.route，否则用输入文件给定类型
            tags_route = (tags.get("route") or "").strip().lower()
            route_type = normalize_route_type(tags_route) if tags_route else input_route_type

            geom = feat.get("geometry")
            if not isinstance(geom, dict):
                continue

            coords = flatten_geometry(geom, limit=5000)
            if len(coords) < 2:
                continue

            # 生成前端稳定 route_id（关键对齐点）
            route_id = generate_route_id(name=name, ref=ref, route_type=route_type)
            if not route_id:
                continue

            # 颜色：优先 tags.colour / tags.color，否则用默认色表
            colour = (tags.get("colour") or tags.get("color") or "").strip()
            if not colour:
                colour = TRANSPORT_COLORS.get(route_type, TRANSPORT_COLORS["bus"])

            route = routes.get(route_id)
            if route is None:
                route = {
                    "name": name or ref or route_id,
                    "type": route_type,
                    "colour": colour,
                    "coordinates": [],
                    "stations": [],
                }
                routes[route_id] = route

            route["coordinates"].extend(coords)

    FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = generate_routes_js(routes)
    OUTPUT_PATH.write_text(out, encoding="utf-8")

    print(f"[ok] routes.js generated: {OUTPUT_PATH}")
    print(f"[ok] routes={len(routes)} size={os.path.getsize(OUTPUT_PATH)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
