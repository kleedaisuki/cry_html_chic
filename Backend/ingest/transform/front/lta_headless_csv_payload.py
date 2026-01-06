from __future__ import annotations

"""
/**
 * @file lta_headless_csv_payload.py
 * @brief LTA “headless CSV” 前端编译器：Raw(bytes) -> IRModule（解析无表头 CSV 变体）。
 *        LTA headless CSV frontend: Raw(bytes) -> IRModule (parse headerless CSV variant).
 *
 * 背景 / Background:
 * - LTA DataMall 的 Passenger Volume 批量文件是“无表头 CSV 变体”（每行一条记录）。
 *   Passenger Volume batch files are a headerless CSV variant (one record per line).
 *
 * 典型两类 schema / Two common schemas:
 * - PV Node (Bus/Train by stops/stations):
 *   YEAR_MONTH, DAY_TYPE, TIME_PER_HOUR, PT_TYPE, PT_CODE, TOTAL_TAP_IN_VOLUME, TOTAL_TAP_OUT_VOLUME
 * - PV OD (Origin-Destination):
 *   YEAR_MONTH, DAY_TYPE, TIME_PER_HOUR, PT_TYPE, ORIGIN_PT_CODE, DESTINATION_PT_CODE, TOTAL_TRIPS
 *
 * 设计要点 / Design notes:
 * - 只做“解析 + 最小语义包装”，不做聚合/清洗（交给 Optimizer）。
 *   Only parse + minimal semantic wrapping; no business cleaning/aggregation (Optimizer does it).
 * - 输出 IRModule 结构稳定：ir_kind + provenance + data。
 *   Stable IRModule shape: ir_kind + provenance + data.
 */
"""

import csv
import io
from typing import Any, Mapping, Optional, Sequence, Literal

from ..interface import (
    FrontendCompiler,
    IRModule,
    JsonValue,
    ParseError,
    SchemaMismatchError,
    UnsupportedInputError,
    RawRecord,
)
from ...wiring import register_frontend


# ============================================================
# Helpers / 工具函数
# ============================================================

SchemaName = Literal["auto", "pv_node", "pv_od"]


def _normalize_content_type(ct: Optional[str]) -> str:
    """
    /**
     * @brief 规范化 Content-Type（去参数，转小写）/ Normalize Content-Type (strip params, lowercase).
     */
    """
    if not ct:
        return ""
    return ct.split(";")[0].strip().lower()


def _as_str(v: Any, *, default: str = "") -> str:
    """
    /**
     * @brief 保守转字符串 / Conservative string cast.
     */
    """
    return v if isinstance(v, str) else default


def _as_bool(v: Any, *, default: bool = False) -> bool:
    """
    /**
     * @brief 保守转布尔 / Conservative bool cast.
     */
    """
    return v if isinstance(v, bool) else default


def _as_int_field(s: str, *, what: str, line_no: int) -> int:
    """
    /**
     * @brief 解析整数字段 / Parse an integer field.
     *
     * @throws ParseError 当字段不是整数 / When field is not an integer.
     */
    """
    try:
        # LTA 文件里通常是纯数字，偶尔会有空格：strip
        return int(s.strip())
    except Exception as e:
        raise ParseError(f"{what}: invalid int at line {line_no}: {s!r}") from e


def _strip_bom(text: str) -> str:
    """
    /**
     * @brief 去 UTF-8 BOM / Strip UTF-8 BOM if present.
     */
    """
    if text.startswith("\ufeff"):
        return text.lstrip("\ufeff")
    return text


def _infer_schema_from_meta(record: RawRecord) -> SchemaName:
    """
    /**
     * @brief 从 meta.extra 推断 schema / Infer schema from meta.extra.
     *
     * 约定 / Convention:
     * - datamall_linkfile 的 dataset: pv_bus/pv_train/pv_odbus/pv_odtrain
     */
    """
    extra = dict(record.meta.extra or {})
    dataset = _as_str(extra.get("dataset"), default="").lower()
    if dataset in ("pv_odbus", "pv_odtrain"):
        return "pv_od"
    if dataset in ("pv_bus", "pv_train"):
        return "pv_node"
    return "auto"


def _build_provenance(record: RawRecord) -> dict[str, JsonValue]:
    """
    /**
     * @brief 构造 provenance / Build provenance.
     */
    """
    prov: dict[str, JsonValue] = {
        "source_name": record.meta.source_name,
        "fetched_at_iso": record.meta.fetched_at_iso,
    }

    # meta.extra 应该已经是 JsonValue 兼容（由上游保证）；这里保守放入
    extra = dict(record.meta.extra or {})
    # 仅接受 JSON 兼容标量；若出现复杂类型，上游应修
    safe_extra: dict[str, JsonValue] = {}
    for k, v in extra.items():
        if isinstance(k, str) and (v is None or isinstance(v, (str, int, float, bool))):
            safe_extra[k] = v
        else:
            # 不抛错：把不可序列化的东西砍掉（保持鲁棒性）
            safe_extra[str(k)] = _as_str(v, default=str(v))
    prov["extra"] = safe_extra
    return prov


# ============================================================
# Frontend / 前端编译器
# ============================================================


@register_frontend("lta_headless_csv_payload")
class LtaHeadlessCsvPayloadFrontend(FrontendCompiler):
    """
    /**
     * @brief LTA 无表头 CSV 前端 / LTA headless CSV frontend compiler.
     *
     * 支持 / Supports:
     * - PV Node: 7 列（tap-in/tap-out）
     * - PV OD  : 7 列（total_trips）
     *
     * 输出 IR / Output IR:
     * {
     *   "ir_kind": "lta_headless_csv_payload",
     *   "provenance": {...},
     *   "data": {
     *      "schema": "pv_node" | "pv_od",
     *      "records": [ { ... }, ... ],
     *      "stats": { "rows": N, "skipped_empty": M }
     *   }
     * }
     */
    """

    name: str = "lta_headless_csv_payload"
    version: str = "0.1.0"

    supported_content_types: Optional[Sequence[str]] = (
        "text/csv",
        "application/csv",
        "application/octet-stream",  # zip 解压后有时没法可靠标注
    )

    def compile(
        self, record: RawRecord, *, config: Mapping[str, JsonValue]
    ) -> IRModule:
        """
        /**
         * @brief 编译：RawRecord -> IRModule / Compile: RawRecord -> IRModule.
         *
         * config 参数 / Config knobs:
         * - schema: "auto" | "pv_node" | "pv_od"（默认 auto，会尝试从 meta.extra.dataset 推断）
         * - encoding: 解码编码（默认优先 meta.encoding，其次 utf-8）
         * - strict_content_type: 是否严格校验 content-type（默认 False）
         * - delimiter: CSV 分隔符（默认 ","）
         * - skip_invalid_lines: 遇到坏行是否跳过（默认 False；默认直接 ParseError）
         *
         * @throws UnsupportedInputError, ParseError, SchemaMismatchError
         */
        """

        # ----------------------------
        # 0) Content-Type recognition
        # ----------------------------
        ct0 = _normalize_content_type(record.meta.content_type)
        strict_ct = _as_bool(config.get("strict_content_type"), default=False)
        if strict_ct and self.supported_content_types is not None:
            if ct0 and ct0 not in set(self.supported_content_types):
                raise UnsupportedInputError(
                    f"lta_headless_csv: unsupported content_type={record.meta.content_type}"
                )

        # ----------------------------
        # 1) Decode bytes -> text
        # ----------------------------
        enc = (
            _as_str(record.meta.encoding, default="").strip()
            or _as_str(config.get("encoding"), default="utf-8").strip()
        )
        if not enc:
            enc = "utf-8"

        errors = _as_str(config.get("decode_errors"), default="strict") or "strict"
        try:
            text = record.payload.decode(enc, errors=errors)
        except Exception as e:
            raise ParseError(
                f"lta_headless_csv: decode failed encoding={enc} errors={errors}: {e}"
            ) from e

        text = _strip_bom(text)

        # ----------------------------
        # 2) Decide schema
        # ----------------------------
        schema_cfg = _as_str(config.get("schema"), default="auto").strip().lower()
        if schema_cfg not in ("auto", "pv_node", "pv_od"):
            raise SchemaMismatchError(
                f"lta_headless_csv: unknown schema={schema_cfg!r} (expected auto|pv_node|pv_od)"
            )

        schema: SchemaName = schema_cfg  # type: ignore[assignment]
        if schema == "auto":
            schema = _infer_schema_from_meta(record)
            if schema == "auto":
                # 实在推不出：默认 node（更常见），但把不确定性写进 provenance
                schema = "pv_node"

        # ----------------------------
        # 3) Parse CSV (headerless)
        # ----------------------------
        delimiter = _as_str(config.get("delimiter"), default=",")
        if not delimiter:
            delimiter = ","

        skip_invalid = _as_bool(config.get("skip_invalid_lines"), default=False)

        f = io.StringIO(text)
        reader = csv.reader(f, delimiter=delimiter)

        records: list[dict[str, JsonValue]] = []
        skipped_empty = 0

        for idx, row in enumerate(reader, start=1):
            # 空行 / blank line
            if not row or all((c.strip() == "" for c in row)):
                skipped_empty += 1
                continue

            # 允许出现 "a, b, c" 这种：csv 会保留空格，所以逐项 strip
            row2 = [c.strip() for c in row]

            # LTA 两类 schema 都是 7 列
            if len(row2) != 7:
                msg = f"lta_headless_csv: expected 7 columns, got {len(row2)} at line {idx}: {row2!r}"
                if skip_invalid:
                    continue
                raise ParseError(msg)

            try:
                year_month = row2[0]  # "2018-05" 或 "201803"（文档里两种写法都出现过）
                day_type = row2[1]  # "WEEKDAY" / "WEEKENDS/HOLIDAY"
                hour = _as_int_field(row2[2], what="TIME_PER_HOUR", line_no=idx)
                pt_type = row2[3]  # "BUS" / "TRAIN"
            except Exception:
                if skip_invalid:
                    continue
                raise

            if schema == "pv_node":
                pt_code = row2[4]
                tap_in = _as_int_field(row2[5], what="TOTAL_TAP_IN_VOLUME", line_no=idx)
                tap_out = _as_int_field(
                    row2[6], what="TOTAL_TAP_OUT_VOLUME", line_no=idx
                )

                rec: dict[str, JsonValue] = {
                    "year_month": year_month,
                    "day_type": day_type,
                    "hour": hour,
                    "pt_type": pt_type,
                    "pt_code": pt_code,
                    "tap_in": tap_in,
                    "tap_out": tap_out,
                }
                records.append(rec)
                continue

            if schema == "pv_od":
                origin = row2[4]
                dest = row2[5]
                total_trips = _as_int_field(row2[6], what="TOTAL_TRIPS", line_no=idx)

                rec2: dict[str, JsonValue] = {
                    "year_month": year_month,
                    "day_type": day_type,
                    "hour": hour,
                    "pt_type": pt_type,
                    "origin_pt_code": origin,
                    "destination_pt_code": dest,
                    "total_trips": total_trips,
                }
                records.append(rec2)
                continue

            # 理论上不可达
            raise SchemaMismatchError(
                f"lta_headless_csv: unreachable schema={schema!r}"
            )

        # ----------------------------
        # 4) Emit stable IRModule
        # ----------------------------
        prov = _build_provenance(record)
        prov["detected_schema"] = schema

        module: IRModule = {
            "ir_kind": "lta_headless_csv_payload",
            "provenance": prov,
            "data": {
                "schema": schema,
                "records": records,
                "stats": {
                    "rows": len(records),
                    "skipped_empty": skipped_empty,
                },
            },
        }

        return module
