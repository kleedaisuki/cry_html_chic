# backend/ingest/transform/front/osm_json_payload.py
from __future__ import annotations

"""
/**
 * @file osm_json_payload.py
 * @brief OSM JSON 前端编译器：OSM(Overpass) JSON -> IR
 *        OSM JSON frontend compiler: OSM(Overpass) JSON -> IR
 */
"""

import json
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from ingest.transform.interface import (
    FrontendCompiler,
    IRModule,
    JsonValue,
    ParseError,
    RawRecord,
    SchemaMismatchError,
    UnsupportedInputError,
)
from ingest.wiring import register_frontend

# ============================================================
# Helpers / 工具函数
# ============================================================


def _json_loads_bytes(payload: bytes, *, encoding: Optional[str]) -> Any:
    """
    /**
     * @brief 解析 bytes 为 JSON 对象 / Parse bytes into JSON object.
     * @param payload 原始 bytes / raw bytes payload.
     * @param encoding 字符编码（可选）/ encoding (optional).
     * @return JSON 解析结果 / parsed JSON.
     * @throws ParseError JSON 解析失败 / JSON parse error.
     */
    """
    try:
        text = payload.decode(encoding or "utf-8")
    except Exception as e:
        raise ParseError(f"osm_json: failed to decode payload: {e}") from e

    try:
        return json.loads(text)
    except Exception as e:
        raise ParseError(f"osm_json: failed to parse JSON: {e}") from e


def _as_bool(v: JsonValue, *, default: bool) -> bool:
    """
    /**
     * @brief JsonValue -> bool（保守转换）/ JsonValue -> bool (conservative cast).
     */
    """
    if isinstance(v, bool):
        return v
    return default


def _as_str_list(v: JsonValue) -> List[str]:
    """
    /**
     * @brief JsonValue -> List[str] / JsonValue -> List[str].
     */
    """
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        out: List[str] = []
        for x in v:
            if isinstance(x, str):
                out.append(x)
        return out
    return []


def _tags_allow(
    tags: Dict[str, Any], *, allow_keys: Sequence[str], allow_prefixes: Sequence[str]
) -> bool:
    """
    /**
     * @brief tags 过滤判定（key 白名单或前缀）/ tags filter predicate (key allowlist/prefixes).
     */
    """
    if not allow_keys and not allow_prefixes:
        return True
    for k in tags.keys():
        if k in allow_keys:
            return True
        for p in allow_prefixes:
            if k.startswith(p):
                return True
    return False


def _geom_point(lon: float, lat: float) -> Dict[str, Any]:
    return {"type": "Point", "coordinates": [lon, lat]}


def _geom_linestring(coords: List[Tuple[float, float]]) -> Dict[str, Any]:
    # coords: [(lon,lat), ...]
    return {"type": "LineString", "coordinates": [[lon, lat] for lon, lat in coords]}


def _geom_polygon(coords: List[Tuple[float, float]]) -> Dict[str, Any]:
    # GeoJSON polygon: [ [ [lon,lat], ... closed ], ... rings]
    ring = [[lon, lat] for lon, lat in coords]
    if len(ring) >= 2 and ring[0] != ring[-1]:
        ring.append(ring[0])
    return {"type": "Polygon", "coordinates": [ring]}


def _is_closed_ring(coords: List[Tuple[float, float]]) -> bool:
    if len(coords) < 4:
        return False
    return coords[0] == coords[-1]


def _safe_id(elem: Dict[str, Any], *, id_prefix: str) -> str:
    """
    /**
     * @brief 生成稳定 feature_id / Generate stable feature_id.
     */
    """
    t = elem.get("type")
    i = elem.get("id")
    return f"{id_prefix}{t}/{i}"


def _extract_way_coords(
    elem: Dict[str, Any], *, nodes_index: Dict[int, Tuple[float, float]]
) -> List[Tuple[float, float]]:
    """
    /**
     * @brief 提取 way 的坐标序列 / Extract coordinate sequence from a way.
     * @note 优先使用 Overpass 的 geometry 字段；否则用 refs + nodes_index 拼。
     */
    """
    geom = elem.get("geometry")
    if isinstance(geom, list) and geom:
        coords: List[Tuple[float, float]] = []
        for p in geom:
            if not isinstance(p, dict):
                continue
            lat = p.get("lat")
            lon = p.get("lon")
            if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                coords.append((float(lon), float(lat)))
        return coords

    refs = elem.get("nodes")
    if isinstance(refs, list) and refs:
        coords2: List[Tuple[float, float]] = []
        for r in refs:
            if not isinstance(r, int):
                continue
            pt = nodes_index.get(r)
            if pt is not None:
                coords2.append(pt)
        return coords2

    return []


def _extract_relation_members_geoms(
    elem: Dict[str, Any],
    *,
    ways_index: Dict[int, Dict[str, Any]],
    nodes_index: Dict[int, Tuple[float, float]],
) -> List[Dict[str, Any]]:
    """
    /**
     * @brief 从 relation.members 抽取子几何（粗粒度）/ Extract member geometries from relation.members (coarse).
     * @note 这里只做“能用就行”的策略：member way -> LineString/Polygon, member node -> Point.
     */
    """
    out: List[Dict[str, Any]] = []
    members = elem.get("members")
    if not isinstance(members, list):
        return out

    for m in members:
        if not isinstance(m, dict):
            continue
        mtype = m.get("type")
        mid = m.get("ref")
        if mtype == "node" and isinstance(mid, int):
            pt = nodes_index.get(mid)
            if pt is not None:
                out.append(_geom_point(pt[0], pt[1]))
        elif mtype == "way" and isinstance(mid, int):
            way = ways_index.get(mid)
            if way is None:
                continue
            coords = _extract_way_coords(way, nodes_index=nodes_index)
            if len(coords) >= 2:
                # polygon if closed or tagged as area
                tags = way.get("tags") if isinstance(way.get("tags"), dict) else {}
                is_area = tags.get("area") == "yes" or tags.get("building") is not None
                if _is_closed_ring(coords) or is_area:
                    out.append(_geom_polygon(coords))
                else:
                    out.append(_geom_linestring(coords))
    return out


# ============================================================
# Frontend / 前端编译器
# ============================================================


@register_frontend("osm_json_payload")
class OsmJsonFrontendCompiler(FrontendCompiler):
    """
    /**
     * @brief OSM JSON -> IR(GeoJSON) / OSM JSON -> IR(GeoJSON).
     *
     * IR 约定（本编译器输出）/ IR contract (emitted by this frontend):
     * - module["ir_kind"] == "geojson"
     * - module["data"] is a GeoJSON FeatureCollection
     * - module["meta"] includes minimal provenance copied from RawMeta
     *
     * @note
     *   这是“边界清晰”的前端：只做 parse + shape normalize，
     *   复杂的清洗/简化交给 Optimizer 做（Good taste）。
     */
    """

    name = "osm_json"
    version = "1.0.0"
    supported_content_types: Optional[Sequence[str]] = (
        "application/json",
        "application/geo+json",  # 有时上游会这么标
        "text/json",
    )

    def compile(
        self, record: RawRecord, *, config: Mapping[str, JsonValue]
    ) -> IRModule:
        """ """
        # -------- 0) content-type gate / 输入门禁 --------
        ct = record.meta.content_type
        if ct is not None and self.supported_content_types is not None:
            if all((ct != x) for x in self.supported_content_types):
                # 允许上游 content-type 不靠谱：若用户显式允许，则继续
                allow_unknown = _as_bool(
                    config.get("allow_unknown_content_type"), default=True
                )
                if not allow_unknown:
                    raise UnsupportedInputError(
                        f"osm_json: unsupported content_type={ct}"
                    )

        # -------- 1) parse JSON / 解析 JSON --------
        obj = _json_loads_bytes(record.payload, encoding=record.meta.encoding)

        if not isinstance(obj, dict):
            raise SchemaMismatchError("osm_json: top-level JSON must be an object")

        elements = obj.get("elements")
        if not isinstance(elements, list):
            raise SchemaMismatchError(
                "osm_json: expected Overpass-style JSON with 'elements' list"
            )

        # -------- 2) config / 配置读取 --------
        id_prefix = str(config.get("id_prefix") or "osm:")
        keep_tags = _as_bool(config.get("keep_tags"), default=True)
        keep_raw_element = _as_bool(
            config.get("keep_raw_element"), default=False
        )  # 调试用：会让 IR 变大
        force_linestring = _as_bool(config.get("force_linestring"), default=False)

        only_types = set(
            _as_str_list(config.get("only_types"))
        )  # e.g. ["way","relation"]
        if not only_types:
            only_types = {"node", "way", "relation"}

        # tags filter (allowlist/prefixes)
        allow_tag_keys = _as_str_list(
            config.get("allow_tag_keys")
        )  # e.g. ["route","highway","name"]
        allow_tag_prefixes = _as_str_list(
            config.get("allow_tag_prefixes")
        )  # e.g. ["route:", "railway:"]

        # relation strategy
        relation_mode = str(config.get("relation_mode") or "multigeom")
        # - "multigeom": relation -> GeometryCollection
        # - "skip": ignore relations
        # - "only": only relations

        # -------- 3) build indices / 建索引（node/way） --------
        nodes_index: Dict[int, Tuple[float, float]] = {}
        ways_index: Dict[int, Dict[str, Any]] = {}

        for e in elements:
            if not isinstance(e, dict):
                continue
            et = e.get("type")
            eid = e.get("id")
            if not isinstance(et, str) or not isinstance(eid, int):
                continue
            if et == "node":
                lat = e.get("lat")
                lon = e.get("lon")
                if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                    nodes_index[eid] = (float(lon), float(lat))
            elif et == "way":
                ways_index[eid] = e

        # -------- 4) convert to GeoJSON Features / 转 GeoJSON Feature --------
        features: List[Dict[str, Any]] = []

        def _props(elem: Dict[str, Any]) -> Dict[str, Any]:
            tags = elem.get("tags") if isinstance(elem.get("tags"), dict) else {}
            if not isinstance(tags, dict):
                tags = {}
            # filter tags
            if not _tags_allow(
                tags, allow_keys=allow_tag_keys, allow_prefixes=allow_tag_prefixes
            ):
                tags = {}
            props: Dict[str, Any] = {
                "osm_type": elem.get("type"),
                "osm_id": elem.get("id"),
            }
            if keep_tags and tags:
                props["tags"] = tags
            if keep_raw_element:
                props["_raw"] = elem
            return props

        for e in elements:
            if not isinstance(e, dict):
                continue
            et = e.get("type")
            eid = e.get("id")
            if not isinstance(et, str) or not isinstance(eid, int):
                continue

            if relation_mode == "only" and et != "relation":
                continue
            if relation_mode == "skip" and et == "relation":
                continue

            if et not in only_types:
                continue

            # Node -> Point
            if et == "node":
                pt = nodes_index.get(eid)
                if pt is None:
                    continue
                geom = _geom_point(pt[0], pt[1])
                features.append(
                    {
                        "type": "Feature",
                        "id": _safe_id(e, id_prefix=id_prefix),
                        "geometry": geom,
                        "properties": _props(e),
                    }
                )
                continue

            # Way -> LineString/Polygon
            if et == "way":
                coords = _extract_way_coords(e, nodes_index=nodes_index)
                if len(coords) < 2:
                    continue

                tags = e.get("tags") if isinstance(e.get("tags"), dict) else {}
                is_area = isinstance(tags, dict) and (
                    tags.get("area") == "yes" or tags.get("building") is not None
                )
                closed = _is_closed_ring(coords)

                if force_linestring:
                    geom = _geom_linestring(coords)
                else:
                    geom = (
                        _geom_polygon(coords)
                        if (closed or is_area)
                        else _geom_linestring(coords)
                    )

                features.append(
                    {
                        "type": "Feature",
                        "id": _safe_id(e, id_prefix=id_prefix),
                        "geometry": geom,
                        "properties": _props(e),
                    }
                )
                continue

            # Relation -> GeometryCollection (coarse)
            if et == "relation":
                if relation_mode == "multigeom":
                    geoms = _extract_relation_members_geoms(
                        e, ways_index=ways_index, nodes_index=nodes_index
                    )
                    if not geoms:
                        continue
                    geom = {"type": "GeometryCollection", "geometries": geoms}
                else:
                    # unknown mode -> be conservative
                    geoms = _extract_relation_members_geoms(
                        e, ways_index=ways_index, nodes_index=nodes_index
                    )
                    if not geoms:
                        continue
                    geom = {"type": "GeometryCollection", "geometries": geoms}

                features.append(
                    {
                        "type": "Feature",
                        "id": _safe_id(e, id_prefix=id_prefix),
                        "geometry": geom,
                        "properties": _props(e),
                    }
                )
                continue

        # -------- 5) Build IRModule / 组装 IR --------
        # 你们的 Optimizer/Backend 只要求 IRModule 是 Dict[str, JsonValue]（JSON-compatible），这里严格保持可 JSON 化
        fc: Dict[str, Any] = {
            "type": "FeatureCollection",
            "features": features,
        }

        module: IRModule = {
            "ir_kind": "geojson",
            "data": fc,
            "meta": {
                "source_name": record.meta.source_name,
                "fetched_at_iso": record.meta.fetched_at_iso,
                "content_type": record.meta.content_type,
                "encoding": record.meta.encoding,
                "extra": dict(record.meta.extra),
            },
            "diagnostics": {
                "features_count": len(features),
                "nodes_index_count": len(nodes_index),
                "ways_index_count": len(ways_index),
            },
        }

        return module
