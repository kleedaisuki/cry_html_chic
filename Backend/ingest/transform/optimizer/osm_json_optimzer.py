# backend/ingest/transform/optimizer/osm_json_optimzer.py
from __future__ import annotations

"""
/**
 * @file osm_json_optimzer.py
 * @brief OSM/Overpass GeoJSON IR 优化器：字段裁剪（tags 白名单）/ OSM/Overpass GeoJSON IR optimizer: tag whitelisting.
 *
 * 设计目标 / Design goals:
 * - 输入来自 osm_json_payload 前端：ir_kind="geojson" 的 FeatureCollection。
 *   Input comes from osm_json_payload frontend: FeatureCollection with ir_kind="geojson".
 * - 仅保留“路线渲染”推荐字段：减少体积，降低前端扫描成本。
 *   Keep only recommended fields for route rendering: reduce size & scanning cost.
 *
 * 注意 / Notes:
 * - 本优化器不改变几何（geometry）形态，只裁剪 properties.tags。
 *   This optimizer does NOT change geometry; it only prunes properties.tags.
 * - “We don't break userspace”：保持输出仍是合法 GeoJSON FeatureCollection。
 *   Keep output as valid GeoJSON FeatureCollection.
 */
"""

import logging
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Set

from ingest.transform.interface import (
    IRModule,
    JsonValue,
    Optimizer,
    SchemaMismatchError,
)
from ingest.wiring import register_optimizer

_LOG = logging.getLogger(__name__)


# ============================================================
# Public optimizer
# ============================================================


@register_optimizer("osm_json_optimzer")
class OsmJsonOptimzer(Optimizer):
    """
    /**
     * @brief OSM JSON 优化器（tags 白名单裁剪）/ OSM JSON optimizer (tag whitelist pruning).
     *
     * 默认白名单 / Default whitelist:
     * - 线路语义 / Route semantics:
     *   type, route, ref, name, network, operator, colour/color
     * - 几何层级 / Layering:
     *   layer, level, bridge, tunnel
     * - 站点/交通语义 / Stops & transport semantics:
     *   highway, railway, public_transport
     *
     * 配置项 / Config keys:
     * - allow_tag_keys: list[str]
     *   额外允许的 tags key / extra allowed tag keys.
     * - drop_empty_tags: bool (default True)
     *   若裁剪后 tags 为空则删除 tags 字段 / drop tags when empty.
     * - keep_raw_element: bool (default False)
     *   若 properties 中有 _raw，则是否保留 / whether to keep _raw inside properties.
     */
    """

    name: str = "osm_json_optimzer"
    version: str = "1.0.0"

    _DEFAULT_ALLOW_KEYS: Set[str] = {
        # route semantics
        "type",
        "route",
        "ref",
        "name",
        "network",
        "operator",
        "colour",
        "color",  # alias of colour
        # layering
        "layer",
        "level",
        "bridge",
        "tunnel",
        # stops & transport
        "highway",
        "railway",
        "public_transport",
    }

    def optimize(
        self, module: IRModule, *, config: Mapping[str, JsonValue]
    ) -> IRModule:
        """
        /**
         * @brief 对 GeoJSON IR 进行 tags 白名单裁剪 / Prune tags in GeoJSON IR using a whitelist.
         * @param module 输入 IRModule / Input IRModule.
         * @param config 优化器配置 / Optimizer config.
         * @return 裁剪后的 IRModule / Pruned IRModule.
         * @throws SchemaMismatchError 当输入不是预期 GeoJSON IR / if input schema mismatches.
         */
        """
        if module.get("ir_kind") != "geojson":
            raise SchemaMismatchError(
                f"{self.name}: expected ir_kind='geojson', got {module.get('ir_kind')!r}"
            )

        data = module.get("data")
        if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
            raise SchemaMismatchError(
                f"{self.name}: expected GeoJSON FeatureCollection"
            )

        features = data.get("features")
        if not isinstance(features, list):
            raise SchemaMismatchError(f"{self.name}: data.features must be a list")

        allow_keys = set(self._DEFAULT_ALLOW_KEYS)
        allow_extra = _as_str_iterable(config.get("allow_tag_keys"))
        allow_keys.update(allow_extra)

        drop_empty_tags = _as_bool(config.get("drop_empty_tags"), default=True)
        keep_raw_element = _as_bool(config.get("keep_raw_element"), default=False)

        out_features = []
        dropped_tags_count = 0
        dropped_raw_count = 0

        for f in features:
            if not isinstance(f, dict) or f.get("type") != "Feature":
                # Be liberal: pass through unknown items (but don't crash).
                out_features.append(f)
                continue

            props = f.get("properties")
            if not isinstance(props, dict):
                out_features.append(f)
                continue

            # Copy-on-write to avoid mutating upstream module.
            new_f = dict(f)
            new_props: MutableMapping[str, Any] = dict(props)

            # Optionally drop _raw (debug heavy).
            if not keep_raw_element and "_raw" in new_props:
                new_props.pop("_raw", None)
                dropped_raw_count += 1

            tags = new_props.get("tags")
            if isinstance(tags, dict):
                new_tags = _filter_tags(tags, allow_keys=allow_keys)

                # normalize color key: prefer "colour" if both absent/present
                if "color" in new_tags and "colour" not in new_tags:
                    new_tags["colour"] = new_tags["color"]

                if drop_empty_tags and not new_tags:
                    new_props.pop("tags", None)
                else:
                    new_props["tags"] = new_tags

                dropped_tags_count += max(0, len(tags) - len(new_tags))

            new_f["properties"] = new_props
            out_features.append(new_f)

        out_module: IRModule = dict(module)
        out_module["data"] = dict(data)
        out_module["data"]["features"] = out_features

        diag = dict(module.get("diagnostics") or {})
        diag.update(
            {
                "optimizer": self.name,
                "allow_tag_keys_count": len(allow_keys),
                "dropped_tags_entries_est": dropped_tags_count,
                "dropped_raw_elements": dropped_raw_count,
                "features_count": len(out_features),
            }
        )
        out_module["diagnostics"] = diag

        _LOG.info(
            "%s optimized: features=%d allow_keys=%d dropped_tag_entries~=%d dropped_raw=%d",
            self.name,
            len(out_features),
            len(allow_keys),
            dropped_tags_count,
            dropped_raw_count,
        )

        return out_module


# ============================================================
# Helpers
# ============================================================


def _filter_tags(
    tags: Mapping[str, Any],
    *,
    allow_keys: Set[str],
) -> Dict[str, JsonValue]:
    """
    /**
     * @brief 按白名单裁剪 tags / Prune tags by whitelist.
     * @param tags 原始 tags / original tags.
     * @param allow_keys 允许的 key 集合 / allowed key set.
     * @return 裁剪后的 tags / pruned tags.
     * @note 仅保留 JSON 兼容值（str/int/float/bool/null）/ Keep JSON-compatible scalars only.
     */
    """
    out: Dict[str, JsonValue] = {}
    for k, v in tags.items():
        if not isinstance(k, str):
            continue
        if k not in allow_keys:
            continue

        if v is None or isinstance(v, (str, int, float, bool)):
            out[k] = v
            continue

        # Some OSM exports may contain non-scalar values; stringify conservatively.
        try:
            out[k] = str(v)
        except Exception:
            # Drop un-stringifiable values.
            continue
    return out


def _as_str_iterable(v: JsonValue) -> Iterable[str]:
    """
    /**
     * @brief 将 JsonValue 解析为字符串列表 / Parse JsonValue into iterable[str].
     * @param v JsonValue 输入 / input JsonValue.
     * @return 可迭代字符串 / iterable of strings.
     */
    """
    if v is None:
        return ()
    if isinstance(v, str):
        return (v,)
    if isinstance(v, list):
        return (x for x in v if isinstance(x, str))
    return ()


def _as_bool(v: JsonValue, *, default: bool) -> bool:
    """
    /**
     * @brief 将 JsonValue 解析为 bool / Parse JsonValue into bool.
     * @param v JsonValue 输入 / input JsonValue.
     * @param default 默认值 / default value.
     * @return bool 结果 / bool result.
     */
    """
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"1", "true", "yes", "y", "on"}:
            return True
        if s in {"0", "false", "no", "n", "off"}:
            return False
    if isinstance(v, (int, float)):
        return bool(v)
    return default
