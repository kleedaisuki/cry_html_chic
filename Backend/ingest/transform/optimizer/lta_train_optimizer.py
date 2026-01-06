from __future__ import annotations

"""
/**
 * @file lta_train_optimizer.py
 * @brief 将 Train Passenger Volume（CSV with header）记录按 MRT/LRT 分桶，并生成稳定主键 / Bucket train passenger volume (header CSV) into MRT/LRT and generate stable primary keys.
 *
 * 新契约（重要）/ New contract (important):
 * - 本优化器只接受 lta_csv_payload 的输出（带 header 的 rows）；
 *   This optimizer only accepts lta_csv_payload output (header rows).
 *
 * 输入 / Input:
 * - IRModule from lta_csv_payload:
 *   {
 *     "kind": "json_payload",
 *     "payload": {
 *       "kind": "lta_csv",
 *       "meta": {...},
 *       "rows": [ {<col>: <value>, ...}, ... ]
 *     }
 *   }
 *
 * 配置 / Config:
 * - schema (str): "pv_node" | "pv_od"   (required)
 * - fields (dict): column mapping       (required)
 *   - pv_node required keys:
 *     year_month, day_type, pt_type, pt_code, hour
 *   - pv_od required keys:
 *     year_month, day_type, pt_type, origin_pt_code, dest_pt_code, hour
 * - keep_non_train (bool): keep non-TRAIN rows (default False)
 * - lrt_prefixes (list[str]): override LRT prefixes (optional)
 *
 * 输出 / Output:
 * - json_payload:
 *   {
 *     "kind": "json_payload",
 *     "payload": {
 *       "kind": "lta_train_bucketed",
 *       "meta": {...},
 *       "schema": "pv_node"|"pv_od",
 *       "mrt": [...],
 *       "lrt": [...],
 *       "stats": {...}
 *     }
 *   }
 *
 * @note
 * - 该 Optimizer 只做“分流 + 生成主键(pk)”：不聚合、不清洗数值（Good taste）。
 *   This optimizer only buckets + generates pk; no aggregation/cleanup here (Good taste).
 */
"""

import re
from typing import Mapping, MutableMapping, Sequence

from ingest.transform.interface import (
    Optimizer,
    IRModule,
    JsonValue,
    SchemaMismatchError,
    InvariantViolationError,
)
from ingest.wiring import register_optimizer


# ============================================================
# Helpers / 工具函数
# ============================================================

_LRT_PREFIXES: set[str] = {"BP", "SE", "SW", "PE", "PW"}


def _as_str(v: JsonValue, *, default: str = "") -> str:
    """
    /**
     * @brief 保守转字符串 / Conservative string cast.
     * @param v 输入值 / Input value.
     * @param default 默认值 / Default value.
     * @return 字符串 / String.
     */
    """
    return v if isinstance(v, str) else default


def _require_dict(v: JsonValue, *, err: str) -> dict[str, JsonValue]:
    """
    /**
     * @brief 强制要求 dict / Require dict.
     * @param v 输入值 / Input value.
     * @param err 错误信息 / Error message.
     * @return dict / dict.
     */
    """
    if not isinstance(v, dict):
        raise SchemaMismatchError(err)
    return v


def _require_list(v: JsonValue, *, err: str) -> list[JsonValue]:
    """
    /**
     * @brief 强制要求 list / Require list.
     * @param v 输入值 / Input value.
     * @param err 错误信息 / Error message.
     * @return list / list.
     */
    """
    if not isinstance(v, list):
        raise SchemaMismatchError(err)
    return v


def _parse_hour(v: JsonValue) -> int:
    """
    /**
     * @brief 解析小时字段 / Parse hour field.
     *
     * 支持 / Supports:
     * - "7", "07", 7
     * - "07:00", "7:00"
     *
     * @param v 输入 / Input.
     * @return 0..23 / 0..23.
     */
    """
    if isinstance(v, int):
        h = v
    elif isinstance(v, str):
        s = v.strip()
        # Extract leading integer from strings like "07:00"
        m = re.match(r"^\s*(\d{1,2})", s)
        if not m:
            return -1
        h = int(m.group(1))
    else:
        return -1

    if 0 <= h <= 23:
        return h
    return -1


def _extract_prefix(code: str) -> str:
    """
    /**
     * @brief 提取站点码前缀 / Extract station code prefix.
     *
     * 例 / Examples:
     * - "BP1" -> "BP"
     * - "NE1" -> "NE"
     * - "SW5" -> "SW"
     *
     * @param code 站点码 / Station code.
     * @return 前缀 / Prefix.
     */
    """
    m = re.match(r"^([A-Z]+)", code.strip().upper())
    return m.group(1) if m else ""


def _is_lrt_code(pt_code: str) -> bool:
    """
    /**
     * @brief 判断是否为 LRT 站点码 / Decide whether a station code belongs to LRT.
     *
     * 规则 / Rule:
     * - 将复合换乘码按 '-' 拆分，任一 component 前缀属于 LRT 前缀集合即认为是 LRT。
     *   Split by '-', if any component prefix in LRT prefixes, classify as LRT.
     *
     * @param pt_code 站点码（可能含 '-'）/ Station code (may contain '-').
     * @return True=LRT, False=MRT / True=LRT, False=MRT.
     */
    """
    if not pt_code:
        return False
    parts = [p for p in pt_code.strip().upper().split("-") if p]
    for p in parts:
        if _extract_prefix(p) in _LRT_PREFIXES:
            return True
    return False


def _pk_pv_node(year_month: str, day_type: str, hour: int, pt_code: str) -> str:
    """
    /**
     * @brief 生成 pv_node 主键 / Generate pk for pv_node.
     *
     * pk := YEAR_MONTH|DAY_TYPE|HH|TRAIN|PT_CODE
     *
     * @param year_month YYYYMM / YYYYMM.
     * @param day_type DAY_TYPE / DAY_TYPE.
     * @param hour 0..23 / 0..23.
     * @param pt_code 站点码 / Station code.
     * @return 主键 / Primary key.
     */
    """
    return f"{year_month}|{day_type}|{hour:02d}|TRAIN|{pt_code}"


def _pk_pv_od(year_month: str, day_type: str, hour: int, origin: str, dest: str) -> str:
    """
    /**
     * @brief 生成 pv_od 主键 / Generate pk for pv_od.
     *
     * pk := YEAR_MONTH|DAY_TYPE|HH|TRAIN|ORIGIN|DEST
     *
     * @param year_month YYYYMM / YYYYMM.
     * @param day_type DAY_TYPE / DAY_TYPE.
     * @param hour 0..23 / 0..23.
     * @param origin 起点码 / Origin code.
     * @param dest 终点码 / Destination code.
     * @return 主键 / Primary key.
     */
    """
    return f"{year_month}|{day_type}|{hour:02d}|TRAIN|{origin}|{dest}"


def _require_fields(
    fields: Mapping[str, JsonValue], keys: Sequence[str]
) -> dict[str, str]:
    """
    /**
     * @brief 校验并提取字段映射 / Validate and extract field mapping.
     *
     * @param fields 配置里的 fields / fields in config.
     * @param keys 必需键 / required keys.
     * @return str->str mapping / str->str mapping.
     */
    """
    out: dict[str, str] = {}
    for k in keys:
        v = fields.get(k)
        if not isinstance(v, str) or not v.strip():
            raise SchemaMismatchError(
                f"lta_train_optimizer: config.fields['{k}'] must be a non-empty string"
            )
        out[k] = v.strip()
    return out


def _get_cell(row: Mapping[str, JsonValue], col: str) -> JsonValue:
    """
    /**
     * @brief 取列值（支持大小写容错）/ Get column value (case-insensitive fallback).
     *
     * @param row 行 dict / row dict.
     * @param col 列名 / column name.
     * @return 值 / value.
     */
    """
    if col in row:
        return row[col]
    # case-insensitive fallback
    col_u = col.upper()
    for k, v in row.items():
        if isinstance(k, str) and k.upper() == col_u:
            return v
    return None


# ============================================================
# Optimizer / 优化器
# ============================================================


@register_optimizer("lta_train_optimizer")
class LtaTrainOptimizer(Optimizer):
    """
    /**
     * @brief LTA Train 分桶优化器（header CSV）/ LTA train bucketing optimizer (header CSV).
     *
     * @note
     * - 输入必须是 lta_csv_payload 形态（module.kind=json_payload, payload.kind=lta_csv）。
     *   Input must be lta_csv_payload shape (module.kind=json_payload, payload.kind=lta_csv).
     */
    """

    name: str = "lta_train_optimizer"
    version: str = "0.2.0"

    def optimize(
        self, module: IRModule, *, config: Mapping[str, JsonValue]
    ) -> IRModule:
        """
        /**
         * @brief 执行优化：分桶 + pk / Optimize: bucket + pk.
         *
         * @param module 输入 IRModule / Input IRModule.
         * @param config 优化器配置 / Optimizer config.
         * @return 输出 IRModule / Output IRModule.
         *
         * @throws SchemaMismatchError 输入结构不符合预期 / Input structure mismatch.
         * @throws InvariantViolationError 不变量被破坏 / Invariant violation.
         */
        """
        if not isinstance(module, dict):
            raise SchemaMismatchError("lta_train_optimizer: IRModule must be a dict")

        # ---- require lta_csv_payload shape ----
        if module.get("kind") != "json_payload":
            raise SchemaMismatchError(
                "lta_train_optimizer: expected module.kind='json_payload'"
            )

        payload = _require_dict(
            module.get("payload"),
            err="lta_train_optimizer: expected module.payload to be a dict",
        )
        if payload.get("kind") != "lta_csv":
            raise SchemaMismatchError(
                "lta_train_optimizer: expected payload.kind='lta_csv'"
            )

        rows = _require_list(
            payload.get("rows"),
            err="lta_train_optimizer: expected payload.rows to be a list",
        )
        if len(rows) > 0 and not isinstance(rows[0], dict):
            raise SchemaMismatchError(
                "lta_train_optimizer: expected header CSV rows: List[Dict[str, JsonValue]] (not headless)"
            )

        # ---- config knobs ----
        schema = _as_str(config.get("schema"), default="").strip().lower()
        if schema not in ("pv_node", "pv_od"):
            raise SchemaMismatchError(
                "lta_train_optimizer: config.schema must be 'pv_node' or 'pv_od'"
            )

        fields_cfg = _require_dict(
            config.get("fields"),
            err="lta_train_optimizer: config.fields must be a dict",
        )

        if schema == "pv_node":
            f = _require_fields(
                fields_cfg, ["year_month", "day_type", "pt_type", "pt_code", "hour"]
            )
        else:
            f = _require_fields(
                fields_cfg,
                [
                    "year_month",
                    "day_type",
                    "pt_type",
                    "origin_pt_code",
                    "dest_pt_code",
                    "hour",
                ],
            )

        keep_non_train = bool(config.get("keep_non_train", False))

        # Allow overriding prefixes
        lrt_prefixes_cfg = config.get("lrt_prefixes")
        global _LRT_PREFIXES
        if isinstance(lrt_prefixes_cfg, list) and all(
            isinstance(x, str) for x in lrt_prefixes_cfg
        ):
            _LRT_PREFIXES = {x.strip().upper() for x in lrt_prefixes_cfg if x.strip()}

        mrt_out: list[dict[str, JsonValue]] = []
        lrt_out: list[dict[str, JsonValue]] = []

        stats: MutableMapping[str, JsonValue] = {
            "input_rows": len(rows),
            "kept_rows": 0,
            "train_rows": 0,
            "non_train_rows": 0,
            "mrt_rows": 0,
            "lrt_rows": 0,
            "mixed_rows": 0,  # OD only: MRT<->LRT
            "missing_code_rows": 0,
            "bad_hour_rows": 0,
        }

        for r in rows:
            if not isinstance(r, dict):
                # 上游契约不应发生；这里宁可抛错，避免 silent corruption
                raise InvariantViolationError(
                    "lta_train_optimizer: row must be a dict (header CSV)"
                )

            # ---- PT_TYPE gating (optional) ----
            pt_type = _as_str(_get_cell(r, f["pt_type"]), default="").strip().upper()
            if pt_type != "TRAIN":
                stats["non_train_rows"] = int(stats["non_train_rows"]) + 1
                if not keep_non_train:
                    continue

            # ---- common fields ----
            year_month = _as_str(_get_cell(r, f["year_month"]), default="").strip()
            day_type = _as_str(_get_cell(r, f["day_type"]), default="").strip().upper()
            hour = _parse_hour(_get_cell(r, f["hour"]))
            if hour < 0:
                stats["bad_hour_rows"] = int(stats["bad_hour_rows"]) + 1
                continue

            out_row = dict(r)  # shallow copy
            out_row["_mode"] = "TRAIN"
            out_row["_schema"] = schema
            out_row["_hour"] = hour

            if schema == "pv_node":
                pt_code = (
                    _as_str(_get_cell(r, f["pt_code"]), default="").strip().upper()
                )
                if not pt_code:
                    stats["missing_code_rows"] = int(stats["missing_code_rows"]) + 1
                    continue

                out_row["_pt_code"] = pt_code
                out_row["_pk"] = _pk_pv_node(year_month, day_type, hour, pt_code)

                is_lrt = _is_lrt_code(pt_code)
                if is_lrt:
                    lrt_out.append(out_row)
                    stats["lrt_rows"] = int(stats["lrt_rows"]) + 1
                else:
                    mrt_out.append(out_row)
                    stats["mrt_rows"] = int(stats["mrt_rows"]) + 1

            else:
                origin = (
                    _as_str(_get_cell(r, f["origin_pt_code"]), default="")
                    .strip()
                    .upper()
                )
                dest = (
                    _as_str(_get_cell(r, f["dest_pt_code"]), default="").strip().upper()
                )
                if not origin or not dest:
                    stats["missing_code_rows"] = int(stats["missing_code_rows"]) + 1
                    continue

                out_row["_origin"] = origin
                out_row["_dest"] = dest
                out_row["_pk"] = _pk_pv_od(year_month, day_type, hour, origin, dest)

                o_lrt = _is_lrt_code(origin)
                d_lrt = _is_lrt_code(dest)
                if o_lrt != d_lrt:
                    stats["mixed_rows"] = int(stats["mixed_rows"]) + 1

                # Bucket rule: any LRT endpoint => LRT
                if o_lrt or d_lrt:
                    lrt_out.append(out_row)
                    stats["lrt_rows"] = int(stats["lrt_rows"]) + 1
                else:
                    mrt_out.append(out_row)
                    stats["mrt_rows"] = int(stats["mrt_rows"]) + 1

            stats["kept_rows"] = int(stats["kept_rows"]) + 1
            if pt_type == "TRAIN":
                stats["train_rows"] = int(stats["train_rows"]) + 1

        meta = payload.get("meta")
        out_payload: dict[str, JsonValue] = {
            "kind": "lta_train_bucketed",
            "meta": meta if isinstance(meta, dict) else {},
            "schema": schema,
            "mrt": mrt_out,
            "lrt": lrt_out,
            "stats": dict(stats),
            "lrt_prefixes": sorted(list(_LRT_PREFIXES)),
        }

        out_module: IRModule = {"kind": "json_payload", "payload": out_payload}
        return out_module
