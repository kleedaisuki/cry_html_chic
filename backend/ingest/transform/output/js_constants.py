# backend/ingest/transform/output/js_constants.py
from __future__ import annotations

"""
/**
 * @file js_constants.py
 * @brief IRModule -> JS 常量文件（单文件版）/ Emit IRModule into a JS constants file (single-file).
 *
 * 目标：生成形如
 *   const <variable> = <JSON dumped>;
 * 并按 module_format 追加 export/module.exports。
 */
"""

import json
from typing import Mapping

from ...utils.logger import get_logger
from ...wiring import register_backend
from ..interface import (
    BackendCompiler,
    IRModule,
    JsTargetSpec,
    JsonValue,
)

_LOG = get_logger(__name__)


def _js_identifier(name: str) -> str:
    """
    /**
     * @brief 保守校验 JS 标识符；不合法直接抛异常 / Conservative JS identifier check; raise if invalid.
     *
     * @param name
     *        变量名 / Variable name.
     * @return
     *        原样返回（已校验）/ Same name (validated).
     */
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("variable name must be a non-empty string")
    s = name.strip()

    # 极简校验：字母/下划线/$ 开头，后续可包含数字
    # Minimal check: start with letter/_/$, then alnum/_/$
    first = s[0]
    if not (first.isalpha() or first in ("_", "$")):
        raise ValueError(f"invalid JS identifier: {s!r}")

    for ch in s[1:]:
        if not (ch.isalnum() or ch in ("_", "$")):
            raise ValueError(f"invalid JS identifier: {s!r}")
    return s


def _join_prefix(prefix: str, filename: str) -> str:
    """
    /**
     * @brief 拼接 path_prefix 与 filename / Join path_prefix and filename.
     *
     * @param prefix
     *        目标前缀 / Path prefix.
     * @param filename
     *        文件名 / Filename.
     * @return
     *        拼接后的相对路径 / Joined relative path.
     */
    """
    p = (prefix or "").lstrip("/")
    if p and not p.endswith("/"):
        p += "/"
    return f"{p}{filename}"


@register_backend("js_constants")
class JsConstantsBackend(BackendCompiler):
    """
    /**
     * @brief JS 常量后端编译器：把 IRModule 整体 dump 成一个 JS 变量 / JS constants backend: dump whole IRModule into one JS variable.
     *
     * @note
     * - 默认单文件输出（target.layout=single）。
     * - 仍然返回 Mapping[path, bytes]，保持与 cache/driver 的接口一致。
     */
    """

    name: str = "js_constants"
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
         * @brief 生成 JS artifacts / Emit JS artifacts.
         *
         * @param module
         *        输入 IRModule / Input IRModule.
         * @param target
         *        JS 输出目标规格 / JS target spec.
         * @param config
         *        后端配置 / Backend config.
         * @return
         *        path -> bytes 的产物映射 / Artifacts mapping (path -> bytes).
         */
        """
        # -------- read config --------
        var = _js_identifier(str(config.get("variable", "DATA")))
        filename = str(config.get("filename", "constants.js"))
        sort_keys = bool(config.get("sort_keys", True))

        json_indent_raw = config.get("json_indent", None)
        indent = None
        if isinstance(json_indent_raw, int):
            indent = json_indent_raw
        elif json_indent_raw is None:
            indent = None
        else:
            # 允许 "2" 这种字符串
            try:
                indent = int(str(json_indent_raw))
            except Exception:
                indent = None

        # -------- serialize --------
        dumped = json.dumps(
            module,
            ensure_ascii=False,
            sort_keys=sort_keys,
            indent=indent,
            separators=(",", ":") if indent is None else None,
        )

        lines: list[str] = []
        lines.append(f"const {var} = {dumped};")

        if target.module_format == "esm":
            lines.append(f"export {{ {var} }};")
        elif target.module_format == "cjs":
            lines.append(f"module.exports = {{ {var} }};")
        else:
            # JsTargetSpec.module_format 被限定为 esm/cjs；这里做防御
            raise ValueError(f"unsupported module_format: {target.module_format!r}")

        text = "\n".join(lines) + "\n"
        out_path = _join_prefix(target.path_prefix, filename)

        _LOG.info(
            "js_constants emit: path=%s var=%s bytes=%d format=%s",
            out_path,
            var,
            len(text.encode("utf-8")),
            target.module_format,
        )

        return {out_path: text.encode("utf-8")}
