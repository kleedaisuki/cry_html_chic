# backend/ingest/cli/bootstrap.py
"""
/**
 * @file bootstrap.py
 * @brief CLI 启动自检与初始化（无业务逻辑）/ CLI bootstrap: preflight checks & initialization (no business logic).
 *
 * 设计目标 / Goals:
 * - 只做“让系统进入可运行状态”的事：路径、目录、logging、最小依赖自检。
 *   Only make the system runnable: paths, directories, logging, minimal dependency checks.
 * - 不 import 具体实现模块（source/cache/transform/task implementations）。
 *   Do NOT import concrete implementations (sources/caches/transforms/tasks).
 * - 不执行任何任务，不触碰数据内容。
 *   Do not execute tasks; do not parse/transform domain data.
 */
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


# ============================================================
# Exceptions / 异常
# ============================================================


class BootstrapError(RuntimeError):
    """/**
    * @brief 启动阶段通用异常 / Generic bootstrap error.
    */"""


class ProjectRootNotFoundError(BootstrapError):
    """/**
    * @brief 无法定位项目根目录 / Cannot locate project root.
    */"""


class PreflightCheckError(BootstrapError):
    """/**
    * @brief 自检失败 / Preflight check failed.
    */"""


# ============================================================
# Data models / 数据模型
# ============================================================


@dataclass(frozen=True)
class BootstrapConfig:
    """/**
    * @brief 启动配置：日志等级、是否严格检查注册表、是否强制创建目录。
    *        Bootstrap config: log level, strict registry check, force-create dirs.
    */"""

    log_level: str = "INFO"
    strict_registry: bool = False
    ensure_dirs: bool = True


@dataclass(frozen=True)
class BootstrapPaths:
    """/**
    * @brief 项目路径集合（均为绝对路径）/ Project paths (all absolute).
    */"""

    project_root: Path
    configs_ingest_dir: Path
    data_dir: Path
    raw_dir: Path
    preprocessed_dir: Path


@dataclass(frozen=True)
class BootstrapResult:
    """/**
    * @brief bootstrap 输出：路径 + 诊断信息 / Bootstrap output: paths + diagnostics.
    */"""

    paths: BootstrapPaths
    diagnostics: dict[str, str]


# ============================================================
# Helpers / 工具函数
# ============================================================


def _iter_parents_inclusive(p: Path) -> Iterable[Path]:
    """/**
    * @brief 迭代 p 及其所有父目录 / Iterate p and all its parents.
    *
    * @param p 输入路径 / Input path.
    * @return 目录序列 / Sequence of directories.
    */"""

    cur = p
    while True:
        yield cur
        if cur.parent == cur:
            break
        cur = cur.parent


def _looks_like_project_root(p: Path) -> bool:
    """/**
    * @brief 判断目录是否像项目根：优先 pyproject.toml，其次 configs/ingest。
    *        Heuristic project root detection: prefer pyproject.toml, fallback to configs/ingest.
    */"""

    if (p / "pyproject.toml").is_file():
        return True
    if (p / "configs" / "ingest").is_dir():
        return True
    return False


def find_project_root(*, start: Optional[Path] = None) -> Path:
    """/**
    * @brief 从 start（默认 CWD）向上查找项目根目录 / Find project root by walking upwards from start (default CWD).
    *
    * @param start 起点目录（可选）/ Starting directory (optional).
    * @return project root 的绝对路径 / Absolute project root path.
    * @throws ProjectRootNotFoundError
    *         找不到可识别的根目录 / If no recognizable root is found.
    */"""

    s = (start or Path.cwd()).resolve()
    for d in _iter_parents_inclusive(s):
        if _looks_like_project_root(d):
            return d
    raise ProjectRootNotFoundError(
        f"cannot locate project root from start={s}. expected pyproject.toml or configs/ingest/"
    )


def _ensure_dir(path: Path) -> None:
    """/**
    * @brief 确保目录存在（必要时创建）/ Ensure a directory exists (create if needed).
    *
    * @param path 目录路径 / Directory path.
    */"""

    path.mkdir(parents=True, exist_ok=True)


def _check_python_version(*, min_major: int = 3, min_minor: int = 11) -> None:
    """/**
    * @brief 校验 Python 版本下限 / Check minimum Python version.
    */"""

    import sys

    v = sys.version_info
    if (v.major, v.minor) < (min_major, min_minor):
        raise PreflightCheckError(
            f"Python>={min_major}.{min_minor} required, got {v.major}.{v.minor}"
        )


def _configure_logging(level: str) -> None:
    """/**
    * @brief 配置 logging（stdout/stderr 分流）/ Configure logging (stdout/stderr split).
    *
    * @note
    *        唯一允许进行全局 logging 初始化的地方。
    *        The only place allowed to initialize global logging.
    */"""

    # 延迟 import：避免 import-time 副作用扩散
    from ingest.utils.logger import configure_logging

    configure_logging(level=level, force=False)


def _preflight_registry(*, strict: bool) -> dict[str, str]:
    """/**
    * @brief 自检 wiring registries 是否存在/可用；strict 模式下要求已被填充。
    *        Preflight check wiring registries; in strict mode require they are populated.
    *
    * @param strict 是否严格要求 registry 非空 / Whether to require non-empty registries.
    * @return 诊断信息 / Diagnostics.
    */"""

    # 注意：这里允许 import wiring，因为 wiring 只声明 registry，不 import 实现。
    from ingest import wiring

    diags: dict[str, str] = {}

    registries = {
        "sources": wiring.SOURCES,
        "raw_caches": wiring.RAW_CACHES,
        "preprocessed_caches": wiring.PREPROCESSED_CACHES,
        "frontends": wiring.FRONTENDS,
        "optimizers": wiring.OPTIMIZERS,
        "backends": wiring.BACKENDS,
    }

    for name, reg in registries.items():
        try:
            count = len(reg)  # Registry implements __len__
        except Exception as e:  # pragma: no cover
            raise PreflightCheckError(f"registry '{name}' is not usable: {e}") from e

        diags[f"registry.{name}.count"] = str(count)

        if strict and count == 0:
            raise PreflightCheckError(
                f"registry '{name}' is empty. did you forget to import implementation modules in the selected task?"
            )

    return diags


def build_paths(project_root: Path) -> BootstrapPaths:
    """/**
    * @brief 基于 project_root 计算关键路径 / Build key paths from project_root.
    */"""

    pr = project_root.resolve()
    configs_ingest = pr / "configs" / "ingest"
    data_dir = pr / "data"
    raw_dir = data_dir / "raw"
    pre_dir = data_dir / "preprocessed"
    return BootstrapPaths(
        project_root=pr,
        configs_ingest_dir=configs_ingest,
        data_dir=data_dir,
        raw_dir=raw_dir,
        preprocessed_dir=pre_dir,
    )


# ============================================================
# Public API / 对外 API
# ============================================================


def bootstrap(
    *, cfg: Optional[BootstrapConfig] = None, start_dir: Optional[Path] = None
) -> BootstrapResult:
    """/**
    * @brief CLI 启动入口：定位根目录、配置 logging、创建目录、做最小自检。
    *        CLI bootstrap entry: locate root, configure logging, ensure dirs, run minimal checks.
    *
    * @param cfg 启动配置（可选）/ Bootstrap config (optional).
    * @param start_dir 查找根目录的起点（默认 CWD）/ Start dir for root search (default CWD).
    * @return BootstrapResult / BootstrapResult.
    */"""

    cfg0 = cfg or BootstrapConfig()

    # 1) 版本检查（尽早失败）
    _check_python_version(min_major=3, min_minor=11)

    # 2) 定位项目根目录
    root = find_project_root(start=start_dir)
    paths = build_paths(root)

    # 3) 配置日志（必须在后续 import 之前尽量早）
    _configure_logging(cfg0.log_level)

    # 4) 目录准备
    if cfg0.ensure_dirs:
        _ensure_dir(paths.data_dir)
        _ensure_dir(paths.raw_dir)
        _ensure_dir(paths.preprocessed_dir)

    # 5) 最小 preflight：wiring registries 可用性
    diagnostics: dict[str, str] = {
        "project_root": str(paths.project_root),
        "configs_ingest_dir": str(paths.configs_ingest_dir),
        "data_dir": str(paths.data_dir),
        "raw_dir": str(paths.raw_dir),
        "preprocessed_dir": str(paths.preprocessed_dir),
    }
    diagnostics.update(_preflight_registry(strict=cfg0.strict_registry))

    return BootstrapResult(paths=paths, diagnostics=diagnostics)
