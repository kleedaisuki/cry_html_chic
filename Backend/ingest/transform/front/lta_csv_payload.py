# backend/ingest/transform/front/lta_csv_payload.py
from __future__ import annotations

import csv
import io
from typing import Any, List, Mapping, Optional, Sequence, Union

from ingest.transform.interface import (
    FrontendCompiler,
    IRModule,
    JsonValue,
    ParseError,
    RawRecord,
)
from ingest.wiring import register_frontend


def _decode_payload(payload: Union[bytes, str], encoding: str = "utf-8") -> str:
    """
    /**
     * @brief 解码 payload 为文本（并处理 UTF-8 BOM）/ Decode payload to text (strip UTF-8 BOM).
     * @param payload: 原始 payload（bytes 或 str）/ Raw payload (bytes or str).
     * @param encoding: 解码编码 / Text encoding.
     * @return 解码后的文本 / Decoded text.
     */
    """
    if isinstance(payload, str):
        return payload
    text = payload.decode(encoding, errors="replace")
    # UTF-8 BOM strip
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    return text


def _sniff_dialect(sample: str) -> csv.Dialect:
    """
    /**
     * @brief 尝试自动探测 CSV 方言（分隔符等）/ Try sniff CSV dialect (delimiter, etc).
     * @param sample: 文本样本 / Text sample.
     * @return 探测到的 dialect（失败则回退 excel/comma）/ Detected dialect (fallback to excel/comma).
     */
    """
    sniffer = csv.Sniffer()
    try:
        return sniffer.sniff(sample, delimiters=[",", ";", "\t", "|"])
    except Exception:
        return csv.get_dialect("excel")


def _looks_like_header(row: Sequence[str]) -> bool:
    """
    /**
     * @brief 粗略判断第一行是否表头 / Heuristic to detect whether the first row is a header.
     * @param row: 第一行字段 / First row fields.
     * @return 是否像表头 / Whether it looks like a header.
     *
     * @note 这是启发式（heuristic），宁可“误判为表头”也不要把表头当数据炸掉。
     *       This is heuristic; better to skip a header than to parse it as data.
     */
    """
    joined = ",".join(cell.strip().upper() for cell in row)
    keywords = ["TIME_PER_HOUR", "DAY_TYPE", "PT_CODE", "TOTAL_TAP_IN_VOLUME"]
    if any(k in joined for k in keywords):
        return True
    alpha = sum(any(c.isalpha() for c in cell) for cell in row)
    return alpha >= max(1, len(row) // 2)


@register_frontend("lta_csv_payload")
class LTACSVPayloadFrontend(FrontendCompiler):
    """
    /**
     * @brief LTA CSV 前端编译器：CSV payload -> IRModule / LTA CSV frontend: CSV payload -> IRModule.
     *
     * 支持：
     * - has_header: "auto" | true | false
     * - delimiter: 手动指定分隔符（否则自动 sniff）
     * - encoding: 解码编码
     */
    """

    # （可选）这些字段在 interface 里是“约定存在”的属性；不强制但放上更稳。
    name = "lta_csv_payload"
    version = "1"
    supported_content_types = None  # type: ignore[assignment]

    @staticmethod
    def describe() -> str:
        """@brief 编译器描述 / Compiler description."""
        return "Parse LTA CSV (header or headless) into structured JSON payload."

    def compile(
        self, record: RawRecord, *, config: Mapping[str, JsonValue]
    ) -> IRModule:
        """
        /**
         * @brief 编译 CSV payload 为 IR / Compile CSV payload to IR.
         * @param record: RawRecord（payload + meta）/ RawRecord (payload + meta).
         * @param config: 前端配置 / Frontend config.
         * @return IRModule: 输出 IR / Output IR.
         * @throws ParseError: CSV 为空或缺 payload / Empty CSV or missing payload.
         */
        """
        cfg: Mapping[str, JsonValue] = config or {}

        has_header = cfg.get("has_header", "auto")  # "auto" | True | False
        encoding = str(cfg.get("encoding", "utf-8"))
        delimiter_val = cfg.get("delimiter", None)
        delimiter: Optional[str] = None if delimiter_val is None else str(delimiter_val)
        dataset = cfg.get("dataset", None)

        if record.payload is None:
            raise ParseError("record.payload is missing")

        text = _decode_payload(record.payload, encoding=encoding)
        sample = text[:4096]

        if delimiter is not None:
            # 轻量 override：复用 excel dialect，只改 delimiter
            dialect = csv.get_dialect("excel")
            # dialect.delimiter 在类型上是只读的，但运行时可用 set attribute；不行就用 sniff fallback。
            try:
                dialect.delimiter = delimiter  # type: ignore[attr-defined]
            except Exception:
                dialect = _sniff_dialect(sample)
        else:
            dialect = _sniff_dialect(sample)

        reader = csv.reader(io.StringIO(text), dialect=dialect)
        rows_raw: List[List[str]] = [
            list(r) for r in reader if r and any(cell.strip() for cell in r)
        ]

        if not rows_raw:
            raise ParseError("empty csv")

        first = rows_raw[0]
        if has_header == "auto":
            header_flag = _looks_like_header(first)
        else:
            header_flag = bool(has_header)

        columns: Optional[List[str]] = None
        rows_out: List[Any] = []

        if header_flag:
            columns = [c.strip() for c in first]
            for r in rows_raw[1:]:
                rr = (r + [""] * len(columns))[: len(columns)]
                rows_out.append({columns[i]: rr[i] for i in range(len(columns))})
        else:
            rows_out = rows_raw

        ir_payload: dict[str, JsonValue] = {
            "kind": "lta_csv",
            "meta": {
                "has_header": header_flag,
                "columns": columns,
                "dataset": dataset,
                "dialect": {"delimiter": getattr(dialect, "delimiter", ",")},
                "source_name": record.meta.source_name,
                "fetched_at": record.meta.fetched_at_iso,
            },
            "rows": rows_out,  # type: ignore[assignment]
        }

        # 按 interface：IRModule 就是“普通 dict”
        return {
            "kind": "json_payload",
            "payload": ir_payload,
        }
