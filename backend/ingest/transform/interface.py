"""
transform/interface.py

Transform 编译工具链的公共接口定义（Python-IR 版）。

This module defines the public interfaces for the transform compiler toolchain
using Python built-in objects as the IR (Intermediate Representation).

Design principles:
- 前后端分离（Front-end / Optimizer / Back-end）
- IR 使用 Python 内置对象（dict / list / str / int / float）
- 组合优于继承（Transformer has-a stages）
- 确定性（deterministic）与可追溯（provenance）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Dict,
    Mapping,
    Optional,
    Sequence,
    Literal,
)
from abc import ABC, abstractmethod

# ============================================================
# JSON-compatible value types
# ============================================================

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

# ============================================================
# IR type aliases (Python built-ins)
# ============================================================

IRModule = Dict[str, JsonValue]
IRDataset = Dict[str, JsonValue]
IRData = Dict[str, JsonValue]   # e.g. table, timeseries, etc.

# ============================================================
# Raw input (minimal shape, decoupled from cache module)
# ============================================================

@dataclass(frozen=True)
class RawMeta:
    """
    @brief 原始数据元信息（最小契约）
    @brief Raw metadata (minimal contract)
    """

    source_name: str
    fetched_at_iso: str
    content_type: Optional[str] = None
    encoding: Optional[str] = None
    extra: Mapping[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True)
class RawRecord:
    """
    @brief 原始数据记录（payload + meta）
    @brief Raw record (payload + meta)
    """

    payload: bytes
    meta: RawMeta

# ============================================================
# Exceptions
# ============================================================

class TransformError(RuntimeError):
    """Base class for transform-related errors."""


class UnsupportedInputError(TransformError):
    """Input type or source not supported."""


class ParseError(TransformError):
    """Failed to parse raw payload."""


class SchemaMismatchError(TransformError):
    """Schema mismatch or incompatible IR shape."""


class InvariantViolationError(TransformError):
    """IR invariant violated (ordering, missing fields, etc.)."""

# ============================================================
# JS output target specification
# ============================================================

JsModuleFormat = Literal["esm", "cjs"]

@dataclass(frozen=True)
class JsTargetSpec:
    """
    @brief JS 输出目标规格（前端 ABI 契约）
    @brief JS emission target spec (frontend ABI)
    """

    js_abi_version: int
    module_format: JsModuleFormat = "esm"
    layout: Literal["single", "sharded"] = "single"
    path_prefix: str = "constants/"
    options: Mapping[str, JsonValue] = field(default_factory=dict)

# ============================================================
# Stage interfaces
# ============================================================

class FrontendCompiler(ABC):
    """
    @brief Front-end：Raw -> IRModule
    """

    name: str
    version: str
    supported_content_types: Optional[Sequence[str]]

    @abstractmethod
    def compile(
        self,
        record: RawRecord,
        *,
        config: Mapping[str, JsonValue],
    ) -> IRModule:
        """
        @raises UnsupportedInputError, ParseError, SchemaMismatchError
        """
        ...


class Optimizer(ABC):
    """
    @brief Optimizer：IRModule -> IRModule（纯 IR 变换）
    """

    name: str
    version: str

    @abstractmethod
    def optimize(
        self,
        module: IRModule,
        *,
        config: Mapping[str, JsonValue],
    ) -> IRModule:
        """
        @raises SchemaMismatchError, InvariantViolationError
        """
        ...


class BackendCompiler(ABC):
    """
    @brief Back-end：IRModule -> JS artifacts (path -> bytes)
    """

    name: str
    version: str

    @abstractmethod
    def emit(
        self,
        module: IRModule,
        *,
        target: JsTargetSpec,
        config: Mapping[str, JsonValue],
    ) -> Mapping[str, bytes]:
        """
        @raises SchemaMismatchError, InvariantViolationError
        """
        ...

# ============================================================
# Driver-level result
# ============================================================

@dataclass(frozen=True)
class TransformProvenance:
    """
    @brief Transform 溯源信息（写入 preprocessed meta.extra）
    """

    frontend: str
    optimizer: str
    backend: str
    ir_version: int
    js_abi_version: int
    extra: Mapping[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True)
class TransformResult:
    """
    @brief Transform 执行结果
    """

    artifacts: Mapping[str, bytes]
    provenance: TransformProvenance
    diagnostics: Mapping[str, JsonValue] = field(default_factory=dict)

# ============================================================
# Transformer spec (from config / wiring)
# ============================================================

@dataclass(frozen=True)
class TransformerSpec:
    """
    @brief Transformer 工具链规格（由 wiring 层解析）
    """

    frontend_name: str
    optimizer_name: str
    backend_name: str

    ir_version: int
    target: JsTargetSpec

    frontend_config: Mapping[str, JsonValue] = field(default_factory=dict)
    optimizer_config: Mapping[str, JsonValue] = field(default_factory=dict)
    backend_config: Mapping[str, JsonValue] = field(default_factory=dict)
