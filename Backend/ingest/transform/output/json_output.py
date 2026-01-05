from __future__ import annotations

"""
/**
 * @file json_output.py
 * @brief JSON 编译后端：IRModule -> JSON artifacts / JSON backend: IRModule -> JSON artifacts.
 *
 * 设计意图 / Design intent:
 * - 提供最朴素的“可调试产物”：直接把 IR（JsonValue）序列化为 .json。
 *   Provide a debuggable artifact: serialize IR (JsonValue) into .json.
 * - 保持确定性（deterministic）：默认 sort_keys=True，并固定换行结尾。
 *   Keep deterministic output: sort_keys=True by default and add trailing newline.
 */
"""

import json
from typing import Mapping, MutableMapping

from ingest.transform.interface import (
    BackendCompiler,
    IRModule,
    JsTargetSpec,
    JsonValue,
    InvariantViolationError,
    SchemaMismatchError,
)
from ingest.wiring import register_backend


def _as_bool(v: JsonValue, *, default: bool) -> bool:
    """
    /**
     * @brief JsonValue -> bool（保守转换）/ JsonValue -> bool (conservative cast).
     */
    """
    if isinstance(v, bool):
        return v
    return default


def _as_int(v: JsonValue, *, default: int) -> int:
    """
    /**
     * @brief JsonValue -> int（保守转换）/ JsonValue -> int (conservative cast).
     */
    """
    if isinstance(v, int) and not isinstance(v, bool):
        return v
    return default


def _as_str(v: JsonValue, *, default: str) -> str:
    """
    /**
     * @brief JsonValue -> str（保守转换）/ JsonValue -> str (conservative cast).
     */
    """
    if isinstance(v, str):
        return v
    return default


def _join_path(prefix: str, name: str) -> str:
    """
    /**
     * @brief 拼接输出路径（统一使用 '/'）/ Join output path (always use '/').
     */
    """
    p = prefix or ""
    if p and not p.endswith("/"):
        p += "/"
    n = name.lstrip("/")

    return f"{p}{n}"


@register_backend("json_output")
class JsonOutputBackend(BackendCompiler):
    """
    /**
     * @brief JSON 编译后端 / JSON emission backend.
     *
     * 输出规则 / Output rules:
     * - 默认输出单文件：<target.path_prefix>/<stem>.json
     * - 可选输出 meta 文件：<stem>.meta.json（用于调试/溯源）
     *
     * @note
     * - 不做“字段清洗/裁剪”：那是 Optimizer 的职责（Good taste）。
     *   No field cleaning/trimming here: that's Optimizer's job (Good taste).
     */
    """

    #: @brief 后端名字 / Backend name.
    #: @brief Backend name.
    name: str = "json_output"

    #: @brief 版本号 / Version string.
    #: @brief Version string.
    version: str = "1.0.0"

    def emit(
        self,
        module: IRModule,
        *,
        target: JsTargetSpec,
        config: Mapping[str, JsonValue],
    ) -> Mapping[str, bytes]:
        """
        /**
         * @brief IRModule -> JSON artifacts / IRModule -> JSON artifacts.
         *
         * @param module
         *        输入 IRModule / Input IRModule.
         * @param target
         *        目标规格（仅使用 path_prefix）/ Target spec (only path_prefix used).
         * @param config
         *        后端配置 / Backend config.
         *
         * @return
         *        artifacts: path -> bytes / artifacts: path -> bytes.
         *
         * @throws SchemaMismatchError
         *         输入不是 dict 或缺少关键字段 / input is not dict or missing key fields.
         * @throws InvariantViolationError
         *         JSON 序列化失败（理论上不该发生）/ JSON serialization failed (should be rare).
         */
        """
        if not isinstance(module, dict):
            raise SchemaMismatchError("json_output: IRModule must be a dict")

        # ---- config ----
        filename = _as_str(config.get("filename"), default="")
        stem = _as_str(config.get("stem"), default="")
        if not filename:
            if not stem:
                # fallback: try ir_kind; else "module"
                ir_kind = module.get("ir_kind")
                stem = ir_kind if isinstance(ir_kind, str) and ir_kind else "module"
            filename = f"{stem}.json"

        indent = _as_int(config.get("indent"), default=2)
        sort_keys = _as_bool(config.get("sort_keys"), default=True)
        ensure_ascii = _as_bool(config.get("ensure_ascii"), default=False)
        emit_meta_file = _as_bool(config.get("emit_meta_file"), default=False)

        # ---- dump main ----
        try:
            text = json.dumps(
                module,
                ensure_ascii=ensure_ascii,
                sort_keys=sort_keys,
                indent=indent,
                separators=(",", ": ") if indent else (",", ":"),
            )
        except TypeError as e:
            # 说明 IR 里混入了非 JsonValue（违反契约）
            raise InvariantViolationError(
                f"json_output: module is not JSON-serializable: {e}"
            ) from e
        except Exception as e:
            raise InvariantViolationError(f"json_output: json.dumps failed: {e}") from e

        # 固定以 '\n' 结尾，便于 unix 工具链与 diff
        payload = (text + "\n").encode("utf-8")

        artifacts: MutableMapping[str, bytes] = {}
        out_path = _join_path(target.path_prefix, filename)
        artifacts[out_path] = payload

        # ---- optional meta ----
        if emit_meta_file:
            meta_obj = {
                "backend": {"name": self.name, "version": self.version},
                "target": {
                    "js_abi_version": target.js_abi_version,
                    "module_format": target.module_format,
                    "layout": target.layout,
                    "path_prefix": target.path_prefix,
                },
                "summary": {
                    "ir_kind": module.get("ir_kind"),
                    "top_keys": sorted(list(module.keys())),
                },
            }
            meta_text = json.dumps(
                meta_obj,
                ensure_ascii=ensure_ascii,
                sort_keys=True,
                indent=2,
            )
            meta_name = (
                filename[:-5] + ".meta.json"
                if filename.endswith(".json")
                else filename + ".meta.json"
            )
            meta_path = _join_path(target.path_prefix, meta_name)
            artifacts[meta_path] = (meta_text + "\n").encode("utf-8")

        return artifacts
