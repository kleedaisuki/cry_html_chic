from __future__ import annotations

"""
/**
 * @file lta_train_optimizer.py
 * @brief 将 Train Passenger Volume 记录按 MRT/LRT 分桶，并生成稳定主键 / Bucket Train PV records into MRT/LRT and generate stable primary keys.
 *
 * 输入 / Input:
 * - IRModule from lta_headless_csv_payload:
 *   {
 *     "ir_kind": "lta_headless_csv_payload",
 *     "provenance": {...},
 *     "data": { "schema": "pv_node"|"pv_od", "records": [ ... ] }
 *   }
 *
 * 输出 / Output:
 * - IRModule:
 *   {
 *     "ir_kind": "lta_train_bucketed",
 *     "provenance": {...},
 *     "data": {
 *        "schema": "...",
 *        "mrt": [ ... ],
 *        "lrt": [ ... ],
 *        "stats": {...}
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


def _as_int(v: JsonValue, *, default: int = 0) -> int:
    """
    /**
     * @brief 保守转整数 / Conservative int cast.
     * @param v 输入值 / Input value.
     * @param default 默认值 / Default value.
     * @return 整数 / Integer.
     */
    """
    if isinstance(v, int) and not isinstance(v, bool):
        return v
    return default


def _extract_prefix(code: str) -> str:
    """
    /**
     * @brief 提取站点 code 的字母前缀 / Extract alphabetic prefix of a station code.
     *
     * 例 / Examples:
     * - "EW14" -> "EW"
     * - "NS26" -> "NS"
     * - "BP1"  -> "BP"
     *
     * @param code 站点码片段 / Code component.
     * @return 前缀（大写）/ Prefix (uppercased).
     */
    """
    s = (code or "").strip().upper()
    m = re.match(r"^([A-Z]+)", s)
    return m.group(1) if m else ""


def _is_lrt_station(pt_code: str) -> bool:
    """
    /**
     * @brief 判断 PT_CODE 是否属于 LRT / Decide whether a PT_CODE belongs to LRT.
     *
     * 规则 / Rule:
     * - 将复合换乘码按 '-' 拆分，任一 component 前缀属于 {BP, SE, SW, PE, PW} 即认为是 LRT。
     *   Split by '-', if any component prefix in {BP, SE, SW, PE, PW}, classify as LRT.
     *
     * @param pt_code 站点码（可能含 '-'）/ Station code (may contain '-').
     * @return True= LRT, False= MRT / True=LRT, False=MRT.
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
     */
    """
    return f"{year_month}|{day_type}|{hour:02d}|TRAIN|{pt_code}"


def _pk_pv_od(year_month: str, day_type: str, hour: int, origin: str, dest: str) -> str:
    """
    /**
     * @brief 生成 pv_od 主键 / Generate pk for pv_od.
     *
     * pk := YEAR_MONTH|DAY_TYPE|HH|TRAIN|ORIGIN->DEST
     */
    """
    return f"{year_month}|{day_type}|{hour:02d}|TRAIN|{origin}->{dest}"


# ============================================================
# Optimizer / 优化器
# ============================================================


@register_optimizer("lta_train_optimizer")
class LtaTrainOptimizer(Optimizer):
    """
    /**
     * @brief LTA Train 分桶优化器 / LTA train bucketing optimizer.
     *
     * @note
     * - 输入必须是 lta_headless_csv_payload 的 IR。
     *   Input must be IR from lta_headless_csv_payload.
     */
    """

    name: str = "lta_train_optimizer"
    version: str = "0.1.0"

    def optimize(
        self, module: IRModule, *, config: Mapping[str, JsonValue]
    ) -> IRModule:
        """
        /**
         * @brief 执行优化：分桶 + pk / Optimize: bucket + pk.
         *
         * @param module 输入 IRModule / Input IRModule.
         * @param config 优化器配置 / Optimizer config.
         *        - keep_non_train (bool): 是否保留非 TRAIN 记录（默认 False）
         *          Keep non-TRAIN records (default False).
         *        - lrt_prefixes (list[str]): 覆盖默认 LRT 前缀集合（可选）
         *          Override LRT prefixes (optional).
         *
         * @return 输出 IRModule / Output IRModule.
         *
         * @throws SchemaMismatchError 输入结构不符合预期 / Input structure mismatch.
         */
        """
        if not isinstance(module, dict):
            raise SchemaMismatchError("lta_train_optimizer: IRModule must be a dict")

        if module.get("ir_kind") != "lta_headless_csv_payload":
            raise SchemaMismatchError(
                f"lta_train_optimizer: expected ir_kind='lta_headless_csv_payload', got {module.get('ir_kind')!r}"
            )

        data = module.get("data")
        if not isinstance(data, dict):
            raise SchemaMismatchError("lta_train_optimizer: module.data must be a dict")

        schema = _as_str(data.get("schema"), default="").strip().lower()
        if schema not in ("pv_node", "pv_od"):
            raise SchemaMismatchError(
                f"lta_train_optimizer: expected schema in ('pv_node','pv_od'), got {schema!r}"
            )

        records = data.get("records")
        if not isinstance(records, list):
            raise SchemaMismatchError(
                "lta_train_optimizer: data.records must be a list"
            )

        # --- config knobs ---
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
            "input_rows": len(records),
            "kept_rows": 0,
            "train_rows": 0,
            "non_train_rows": 0,
            "mrt_rows": 0,
            "lrt_rows": 0,
            "missing_pt_code_rows": 0,
        }

        for r in records:
            if not isinstance(r, dict):
                # 上游契约不应发生；这里宁可抛错，避免 silent corruption
                raise InvariantViolationError(
                    "lta_train_optimizer: record must be a dict"
                )

            pt_type = _as_str(r.get("pt_type"), default="").strip().upper()

            if pt_type != "TRAIN":
                stats["non_train_rows"] = (
                    _as_int(stats["non_train_rows"], default=0) + 1
                )
                if keep_non_train:
                    # 保留原样，但不分桶；统一塞到 mrt（避免下游意外缺 key）
                    mrt_out.append(dict(r))
                    stats["kept_rows"] = _as_int(stats["kept_rows"], default=0) + 1
                continue

            stats["train_rows"] = _as_int(stats["train_rows"], default=0) + 1

            year_month = _as_str(r.get("year_month"), default="")
            day_type = _as_str(r.get("day_type"), default="")
            hour = _as_int(r.get("hour"), default=-1)

            if schema == "pv_node":
                pt_code = _as_str(r.get("pt_code"), default="").strip().upper()
                if not pt_code:
                    stats["missing_pt_code_rows"] = (
                        _as_int(stats["missing_pt_code_rows"], default=0) + 1
                    )
                    # 没 code 无法分桶：默认归 mrt（保守）
                    out = dict(r)
                    out["pk"] = _pk_pv_node(
                        year_month, day_type, hour if hour >= 0 else 0, pt_code
                    )
                    mrt_out.append(out)
                    stats["mrt_rows"] = _as_int(stats["mrt_rows"], default=0) + 1
                    stats["kept_rows"] = _as_int(stats["kept_rows"], default=0) + 1
                    continue

                out2 = dict(r)
                out2["pk"] = _pk_pv_node(
                    year_month, day_type, hour if hour >= 0 else 0, pt_code
                )

                if _is_lrt_station(pt_code):
                    lrt_out.append(out2)
                    stats["lrt_rows"] = _as_int(stats["lrt_rows"], default=0) + 1
                else:
                    mrt_out.append(out2)
                    stats["mrt_rows"] = _as_int(stats["mrt_rows"], default=0) + 1

                stats["kept_rows"] = _as_int(stats["kept_rows"], default=0) + 1
                continue

            # schema == "pv_od"
            origin = _as_str(r.get("origin_pt_code"), default="").strip().upper()
            dest = _as_str(r.get("destination_pt_code"), default="").strip().upper()

            out3 = dict(r)
            out3["pk"] = _pk_pv_od(
                year_month, day_type, hour if hour >= 0 else 0, origin, dest
            )

            # OD：只要 origin 或 dest 任一为 LRT，就归 LRT（保守，避免 LRT OD 被分到 MRT）
            if _is_lrt_station(origin) or _is_lrt_station(dest):
                lrt_out.append(out3)
                stats["lrt_rows"] = _as_int(stats["lrt_rows"], default=0) + 1
            else:
                mrt_out.append(out3)
                stats["mrt_rows"] = _as_int(stats["mrt_rows"], default=0) + 1

            stats["kept_rows"] = _as_int(stats["kept_rows"], default=0) + 1

        # provenance：继承上游，并标注本优化器
        prov_in = module.get("provenance")
        prov: dict[str, JsonValue] = dict(prov_in) if isinstance(prov_in, dict) else {}
        prov["optimizer"] = {"name": self.name, "version": self.version}
        prov["lrt_prefixes"] = sorted(list(_LRT_PREFIXES))

        out_module: IRModule = {
            "ir_kind": "lta_train_bucketed",
            "provenance": prov,
            "data": {
                "schema": schema,
                "mrt": mrt_out,
                "lrt": lrt_out,
                "stats": dict(stats),
            },
        }
        return out_module
