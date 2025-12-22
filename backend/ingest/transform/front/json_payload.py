"""
/**
 * @file json_payload.py
 * @brief JSON 前端编译器：Raw(bytes) -> IRModule（通用 JSON 解析 + 轻投影）。
 *        JSON frontend compiler: Raw(bytes) -> IRModule (generic JSON parse + light projection).
 *
 * 设计要点 / Design notes:
 * - 只做 JSON 解析与最小语义包装，不做业务清洗与优化（交给 Optimizer）。
 *   Only parse and wrap JSON minimally; no cleaning/optimization (left to Optimizer).
 * - 输出 IRModule 结构稳定：包含 provenance + data（可选抽取）。
 *   Stable IRModule shape: provenance + data (optional extraction).
 */
"""

from __future__ import annotations

import json
from typing import Any, Mapping, Optional, Sequence

from ingest.transform.interface import (
    FrontendCompiler,
    IRModule,
    JsonValue,
    ParseError,
    SchemaMismatchError,
    UnsupportedInputError,
    RawRecord,
)
from ingest.wiring import register_frontend


def _as_json_value(x: Any, *, what: str) -> JsonValue:
    """
    /**
     * @brief 将 Python 对象保守检查为 JsonValue（递归）/ Validate Python object as JsonValue (recursive).
     *
     * @param x
     *        待检查对象 / Object to validate.
     * @param what
     *        错误上下文 / Error context.
     * @return
     *        JsonValue / JsonValue.
     * @throws SchemaMismatchError
     *        当对象不满足 JSON 兼容形状 / When object is not JSON-compatible.
     */
    """
    if x is None or isinstance(x, (bool, int, float, str)):
        return x
    if isinstance(x, list):
        return [_as_json_value(v, what=what) for v in x]
    if isinstance(x, dict):
        out: dict[str, JsonValue] = {}
        for k, v in x.items():
            if not isinstance(k, str):
                raise SchemaMismatchError(
                    f"{what}: dict key must be str, got {type(k)}"
                )
            out[k] = _as_json_value(v, what=what)
        return out
    raise SchemaMismatchError(f"{what}: value is not JSON-compatible: {type(x)}")


def _normalize_content_type(ct: Optional[str]) -> str:
    """
    /**
     * @brief 规范化 Content-Type（去参数，转小写）/ Normalize Content-Type (strip params, lowercase).
     *
     * @param ct
     *        原 Content-Type / Raw content-type.
     * @return
     *        规范化后的 content-type / Normalized content-type.
     */
    """
    if not ct:
        return ""
    return ct.split(";")[0].strip().lower()


@register_frontend("json_payload")
class JsonPayloadFrontend(FrontendCompiler):
    """
    /**
     * @brief 通用 JSON 前端：解析 payload 为 JSON，并包装成 IRModule。
     *        Generic JSON frontend: parses payload as JSON and wraps into IRModule.
     */
    """

    name: str = "json_payload"
    version: str = "0.1.0"

    # 常见 JSON 类型；注意一些服务会返回 application/json; charset=utf-8（参数会被剥离）
    supported_content_types: Optional[Sequence[str]] = (
        "application/json",
        "text/json",
        "application/ld+json",
    )

    def compile(
        self, record: RawRecord, *, config: Mapping[str, JsonValue]
    ) -> IRModule:
        """
        /**
         * @brief 编译：RawRecord -> IRModule / Compile: RawRecord -> IRModule.
         *
         * @param record
         *        原始记录（bytes + meta）/ Raw record (bytes + meta).
         * @param config
         *        前端配置 / Frontend config.
         *
         * @return
         *        IRModule（稳定结构：provenance + data）/ IRModule (stable: provenance + data).
         *
         * @throws UnsupportedInputError
         *        输入不是 JSON 或 content-type 不支持 / Input not JSON or unsupported content-type.
         * @throws ParseError
         *        JSON 解析失败 / JSON parse failed.
         * @throws SchemaMismatchError
         *        输出不满足 JsonValue / Output violates JsonValue constraints.
         */
        """

        # ----------------------------
        # 0) Input recognition
        # ----------------------------
        ct0 = _normalize_content_type(record.meta.content_type)
        strict_ct = bool(config.get("strict_content_type", False))

        if strict_ct and self.supported_content_types is not None:
            if ct0 and ct0 not in set(self.supported_content_types):
                raise UnsupportedInputError(
                    f"json frontend: unsupported content_type={record.meta.content_type}"
                )

        # ----------------------------
        # 1) Decode bytes -> str
        # ----------------------------
        # 优先使用 meta.encoding，其次 config.encoding，默认 utf-8
        enc = (record.meta.encoding or str(config.get("encoding") or "utf-8")).strip()
        errors = str(config.get("decode_errors") or "strict")

        try:
            text = record.payload.decode(enc, errors=errors)
        except Exception as e:
            raise ParseError(
                f"json frontend: decode failed encoding={enc} errors={errors}: {e}"
            ) from e

        # 常见容错：去 UTF-8 BOM
        if text.startswith("\ufeff"):
            text = text.lstrip("\ufeff")

        # ----------------------------
        # 2) Parse JSON
        # ----------------------------
        try:
            obj = json.loads(text)
        except Exception as e:
            # 若 content-type 明确是 json（或用户不 strict），这里还是给 ParseError
            raise ParseError(f"json frontend: json.loads failed: {e}") from e

        # ----------------------------
        # 3) Optional extraction (e.g. DataMall { "value": [...] })
        # ----------------------------
        extract_key = config.get("extract_key")
        extracted: Any = obj

        if isinstance(extract_key, str) and extract_key:
            # 只在 obj 是 dict 时抽取；否则保持原样
            if isinstance(obj, dict) and extract_key in obj:
                extracted = obj.get(extract_key)

        # ----------------------------
        # 4) Build stable IRModule
        # ----------------------------
        # provenance：尽量带上可追溯信息（来自 RawMeta + extra）
        prov: dict[str, JsonValue] = {
            "source_name": record.meta.source_name,
            "fetched_at_iso": record.meta.fetched_at_iso,
        }

        # 把 meta.extra（通常含 dataset/url/mode/query/skip/http_status 等）打进去
        # 注意：extra 的值类型应当已是 JsonValue（transform driver 也要求这点）
        try:
            extra = dict(record.meta.extra)
            prov["extra"] = _as_json_value(extra, what="meta.extra")
        except Exception as e:
            raise SchemaMismatchError(
                f"json frontend: meta.extra not JsonValue: {e}"
            ) from e

        # data：存 extracted（确保是 JsonValue）
        data = _as_json_value(extracted, what="json.data")

        module: IRModule = {
            "ir_kind": "json_payload",
            "provenance": prov,
            "data": data,
        }

        # 可选：同时保留原始 obj（一般不需要；默认关闭，避免膨胀）
        if bool(config.get("keep_raw_object", False)):
            module["raw_object"] = _as_json_value(obj, what="json.raw_object")

        return module
