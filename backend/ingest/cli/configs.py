# backend/ingest/cli/configs.py
"""
/**
 * @file configs.py
 * @brief CLI 配置解析：把 ingest 配置 JSON 解析为强类型规格（Job 列表 + 环境配置）。
 *        CLI config parsing: parse ingest JSON into typed specs (job list + environment config).
 *
 * 设计边界 / Boundaries:
 * - 这里只做“形状解析 + 基础校验 + 路径解析”，不做 registry require，不 import 具体实现。
 *   Shape parsing + basic validation + path resolution only; no registry require, no concrete impl imports.
 * - Job 的语义是：source -> raw cache -> transform -> preprocessed cache。
 *   Job semantics: source -> raw cache -> transform -> preprocessed cache.
 */
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional


# ============================================================
# Exceptions / 异常
# ============================================================

class ConfigError(ValueError):
    """Generic config parsing error."""


class ConfigFileNotFoundError(ConfigError):
    """Config file not found."""


class ConfigSchemaError(ConfigError):
    """Config schema/type mismatch."""


# ============================================================
# Data models / 数据模型
# ============================================================

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True)
class PathsConfig:
    configs_root: str
    data_root: str
    raw_root: str
    preprocessed_root: str


@dataclass(frozen=True)
class ExecutionConfig:
    parallelism: int = 1
    strategy: str = "serial"  # serial | threads | processes
    fail_fast: bool = True


@dataclass(frozen=True)
class ImplConfig:
    name: str
    config: Mapping[str, JsonValue]


@dataclass(frozen=True)
class CacheConfigs:
    raw: ImplConfig
    preprocessed: ImplConfig


@dataclass(frozen=True)
class StageConfig:
    name: str
    config: Mapping[str, JsonValue]


@dataclass(frozen=True)
class TransformConfig:
    ir_version: int
    js_abi_version: int
    module_format: str = "esm"
    layout: str = "single"
    path_prefix: str = "constants/"
    options: Mapping[str, JsonValue] = None  # type: ignore

    def __post_init__(self) -> None:
        if self.options is None:
            object.__setattr__(self, "options", {})


@dataclass(frozen=True)
class SourceConfig:
    name: str
    config: Mapping[str, JsonValue]


@dataclass(frozen=True)
class JobConfig:
    name: str
    source: SourceConfig
    frontend: StageConfig
    optimizer: StageConfig
    backend: StageConfig


@dataclass(frozen=True)
class IngestConfig:
    version: int
    profile: str
    log_level: str
    paths: PathsConfig
    execution: ExecutionConfig
    cache_configs: CacheConfigs
    transform_configs: TransformConfig
    plugins: tuple[str, ...]
    jobs: tuple[JobConfig, ...]


@dataclass(frozen=True)
class ResolvedPaths:
    project_root: Path
    configs_root: Path
    data_root: Path
    raw_root: Path
    preprocessed_root: Path


@dataclass(frozen=True)
class LoadedConfig:
    config: IngestConfig
    paths: ResolvedPaths
    config_path: Path


# ============================================================
# Public API
# ============================================================

def load_config_by_name(
    config_name: str,
    *,
    project_root: Path,
    configs_root: str = "configs/ingest",
) -> LoadedConfig:
    if not isinstance(config_name, str) or not config_name.strip():
        raise ConfigSchemaError("config_name must be a non-empty string")

    cfg_root = (project_root / configs_root).resolve()
    path = (cfg_root / f"{config_name}.json").resolve()
    return load_config_file(path, project_root=project_root)


def load_config_file(path: Path, *, project_root: Path) -> LoadedConfig:
    p = Path(path).resolve()
    if not p.is_file():
        raise ConfigFileNotFoundError(f"config file not found: {p}")

    data = _read_json(p)
    cfg = parse_ingest_config(data)
    rpaths = resolve_paths(cfg.paths, project_root=project_root)
    _check_paths_consistency(cfg.paths)

    return LoadedConfig(config=cfg, paths=rpaths, config_path=p)


def parse_ingest_config(obj: Mapping[str, Any]) -> IngestConfig:
    if not isinstance(obj, Mapping):
        raise ConfigSchemaError("config must be a JSON object")

    version = _require_int(obj, "version")
    profile = _require_str(obj, "profile")
    log_level = _require_str(obj, "log_level")

    paths = _parse_paths(_require_mapping(obj, "paths"))
    execution = _parse_execution(_require_mapping(obj, "execution"))
    cache_cfgs = _parse_cache_configs(_require_mapping(obj, "cache_configs"))
    transform_cfgs = _parse_transform_configs(_require_mapping(obj, "transform_configs"))
    plugins = _parse_plugins(_require_list(obj, "plugins"))
    jobs = _parse_jobs(_require_list(obj, "jobs"))

    _validate_execution(execution)
    _validate_transform_configs(transform_cfgs)

    return IngestConfig(
        version=version,
        profile=profile,
        log_level=log_level,
        paths=paths,
        execution=execution,
        cache_configs=cache_cfgs,
        transform_configs=transform_cfgs,
        plugins=plugins,
        jobs=jobs,
    )


def resolve_paths(paths: PathsConfig, *, project_root: Path) -> ResolvedPaths:
    pr = Path(project_root).resolve()
    return ResolvedPaths(
        project_root=pr,
        configs_root=(pr / paths.configs_root).resolve(),
        data_root=(pr / paths.data_root).resolve(),
        raw_root=(pr / paths.raw_root).resolve(),
        preprocessed_root=(pr / paths.preprocessed_root).resolve(),
    )


# ============================================================
# Parsing helpers
# ============================================================

def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigSchemaError(f"invalid JSON: {e}") from e


def _parse_plugins(items: list[Any]) -> tuple[str, ...]:
    if not items:
        raise ConfigSchemaError("plugins must be a non-empty list")

    seen: set[str] = set()
    out: list[str] = []

    for i, v in enumerate(items):
        if not isinstance(v, str) or not v.strip():
            raise ConfigSchemaError(f"plugins[{i}] must be a non-empty string")
        name = v.strip()
        if name not in seen:
            seen.add(name)
            out.append(name)

    return tuple(out)


def _parse_paths(m: Mapping[str, Any]) -> PathsConfig:
    return PathsConfig(
        configs_root=_require_str(m, "configs_root"),
        data_root=_require_str(m, "data_root"),
        raw_root=_require_str(m, "raw_root"),
        preprocessed_root=_require_str(m, "preprocessed_root"),
    )


def _parse_execution(m: Mapping[str, Any]) -> ExecutionConfig:
    return ExecutionConfig(
        parallelism=_require_int(m, "parallelism"),
        strategy=_require_str(m, "strategy"),
        fail_fast=_require_bool(m, "fail_fast"),
    )


def _parse_cache_configs(m: Mapping[str, Any]) -> CacheConfigs:
    raw = _parse_impl_config(_require_mapping(m, "raw"))
    pre = _parse_impl_config(_require_mapping(m, "preprocessed"))
    return CacheConfigs(raw=raw, preprocessed=pre)


def _parse_transform_configs(m: Mapping[str, Any]) -> TransformConfig:
    ir_version = _require_int(m, "ir_version")
    target = _require_mapping(m, "target")
    return TransformConfig(
        ir_version=ir_version,
        js_abi_version=_require_int(target, "js_abi_version"),
        module_format=_optional_str(target, "module_format", default="esm"),
        layout=_optional_str(target, "layout", default="single"),
        path_prefix=_optional_str(target, "path_prefix", default="constants/"),
        options=_optional_mapping_json_value(target, "options", default={}),
    )


def _parse_jobs(items: list[Any]) -> tuple[JobConfig, ...]:
    if not items:
        raise ConfigSchemaError("jobs must be a non-empty list")

    jobs: list[JobConfig] = []
    seen: set[str] = set()

    for it in items:
        name = _require_str(it, "name")
        if name in seen:
            raise ConfigSchemaError(f"duplicate job name: {name}")
        seen.add(name)

        src = _parse_source(_require_mapping(it, "source"))
        tr = _require_mapping(it, "transform")

        jobs.append(
            JobConfig(
                name=name,
                source=src,
                frontend=_parse_stage(_require_mapping(tr, "frontend")),
                optimizer=_parse_stage(_require_mapping(tr, "optimizer")),
                backend=_parse_stage(_require_mapping(tr, "backend")),
            )
        )

    return tuple(jobs)


def _parse_source(m: Mapping[str, Any]) -> SourceConfig:
    return SourceConfig(
        name=_require_str(m, "name"),
        config=_optional_mapping_json_value(m, "config", default={}),
    )


def _parse_stage(m: Mapping[str, Any]) -> StageConfig:
    return StageConfig(
        name=_require_str(m, "name"),
        config=_optional_mapping_json_value(m, "config", default={}),
    )


def _parse_impl_config(m: Mapping[str, Any]) -> ImplConfig:
    return ImplConfig(
        name=_require_str(m, "name"),
        config=_optional_mapping_json_value(m, "config", default={}),
    )


# ============================================================
# Validation
# ============================================================

def _validate_execution(exe: ExecutionConfig) -> None:
    if exe.parallelism <= 0:
        raise ConfigSchemaError("execution.parallelism must be > 0")
    if exe.strategy.lower() not in ("serial", "threads", "processes"):
        raise ConfigSchemaError("invalid execution.strategy")


def _validate_transform_configs(tc: TransformConfig) -> None:
    if tc.ir_version <= 0:
        raise ConfigSchemaError("ir_version must be > 0")
    if tc.js_abi_version <= 0:
        raise ConfigSchemaError("js_abi_version must be > 0")


def _check_paths_consistency(paths: PathsConfig) -> None:
    for v in (
        paths.configs_root,
        paths.data_root,
        paths.raw_root,
        paths.preprocessed_root,
    ):
        if not isinstance(v, str) or not v.strip():
            raise ConfigSchemaError("path entries must be non-empty strings")


# ============================================================
# Primitive getters
# ============================================================

def _require_mapping(m: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    if key not in m or not isinstance(m[key], Mapping):
        raise ConfigSchemaError(f"field '{key}' must be an object")
    return m[key]


def _require_list(m: Mapping[str, Any], key: str) -> list[Any]:
    if key not in m or not isinstance(m[key], list):
        raise ConfigSchemaError(f"field '{key}' must be a list")
    return m[key]


def _require_str(m: Mapping[str, Any], key: str) -> str:
    if key not in m or not isinstance(m[key], str) or not m[key].strip():
        raise ConfigSchemaError(f"field '{key}' must be a non-empty string")
    return m[key].strip()


def _optional_str(m: Mapping[str, Any], key: str, *, default: str) -> str:
    v = m.get(key, default)
    if not isinstance(v, str):
        raise ConfigSchemaError(f"field '{key}' must be a string")
    return v.strip()


def _require_int(m: Mapping[str, Any], key: str) -> int:
    if key not in m or not isinstance(m[key], int) or isinstance(m[key], bool):
        raise ConfigSchemaError(f"field '{key}' must be an integer")
    return m[key]


def _require_bool(m: Mapping[str, Any], key: str) -> bool:
    if key not in m or not isinstance(m[key], bool):
        raise ConfigSchemaError(f"field '{key}' must be a boolean")
    return m[key]


def _optional_mapping_json_value(
    m: Mapping[str, Any],
    key: str,
    *,
    default: Mapping[str, JsonValue],
) -> Mapping[str, JsonValue]:
    v = m.get(key)
    if v is None:
        return dict(default)
    if not isinstance(v, Mapping):
        raise ConfigSchemaError(f"field '{key}' must be an object")
    return dict(v)
