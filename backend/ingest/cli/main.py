"""
/**
 * @file main.py
 * @brief Ingest CLI 主入口 / Main entry point for ingest CLI.
 *
 * ============================================================
 * 使用方法 / Usage
 * ============================================================
 *
 * 1) 运行配置中的所有 jobs：
 *
 *    $ ingest run <config_name>
 *
 *    例如：
 *    $ ingest run datamall_bus_stops
 *
 * 2) 仅运行指定 job（可重复）：
 *
 *    $ ingest run <config_name> --job <job_name> [--job <job_name> ...]
 *
 * 3) 仅做系统自检（不执行任何 job）：
 *
 *    $ ingest doctor <config_name>
 *
 * 4) 列出当前已注册的插件：
 *
 *    $ ingest list
 *
 * ============================================================
 * 设计原则 / Design principles
 * ============================================================
 *
 * - 本模块只负责：
 *   - CLI 参数解析
 *   - 启动顺序编排（bootstrap → load config → load plugins）
 *   - Task 的创建、执行与结果汇总
 *
 * - 本模块【绝不】：
 *   - 直接 import 任何插件实现
 *   - 处理业务数据
 *   - 管理对象生命周期（由 Task 负责）
 *
 * - 所有可变逻辑都应下沉到：
 *   - configs / runtime / tasks / wiring
 */
"""

from __future__ import annotations

import argparse
import sys
import traceback
# import os
from pathlib import Path
from typing import List, Optional
from pathlib import Path

from ingest.utils.logger import get_logger
from ingest.cli.bootstrap import bootstrap
from ingest.cli.configs import (
    load_config_by_name,
    LoadedConfig,
    find_project_root_by_pyproject,
)
from ingest.cli.runtime import ensure_plugins_loaded
from ingest.cli.tasks.run import RunJobTask
from ingest.cli.tasks.interface import Task
from ingest.wiring import (
    SOURCES,
    RAW_CACHES,
    PREPROCESSED_CACHES,
    FRONTENDS,
    OPTIMIZERS,
    BACKENDS,
)
from ingest.utils.logger import set_log_level

logger = get_logger(__name__)


# ============================================================
# CLI parsing
# ============================================================


def build_parser() -> argparse.ArgumentParser:
    """
    @brief 构建 CLI 参数解析器 / Build CLI argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="ingest",
        description="Offline ingest & transform pipeline",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # --------------------------------------------------------
    # ingest run
    # --------------------------------------------------------
    run_parser = subparsers.add_parser(
        "run",
        help="Run jobs defined in a config",
    )
    run_parser.add_argument(
        "config_name",
        help="Config name (without .json)",
    )
    run_parser.add_argument(
        "--job",
        action="append",
        dest="jobs",
        help="Only run specified job(s)",
    )
    run_parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Fail immediately on first job error",
    )
    run_parser.add_argument(
        "--no-fail-fast",
        action="store_true",
        help="Continue running remaining jobs on error",
    )

    # --------------------------------------------------------
    # ingest doctor
    # --------------------------------------------------------
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Run preflight checks only (no job execution)",
    )
    doctor_parser.add_argument(
        "config_name",
        help="Config name (without .json)",
    )

    # --------------------------------------------------------
    # ingest list
    # --------------------------------------------------------
    subparsers.add_parser(
        "list",
        help="List all registered plugins",
    )

    return parser


# ============================================================
# Command handlers
# ============================================================


def cmd_run(args: argparse.Namespace) -> int:
    """
    @brief 运行配置中的 job / Run jobs defined in config.
    """
    project_root = find_project_root_by_pyproject(Path.cwd())
    loaded: LoadedConfig = load_config_by_name(
        args.config_name,
        project_root=project_root,
    )
    set_log_level(getattr(loaded.config, "log_level", "INFO"))

    # 覆盖 fail_fast（CLI > config）
    execution = loaded.config.execution
    if args.fail_fast:
        loaded.config.execution.fail_fast = True
    if args.no_fail_fast:
        loaded.config.execution.fail_fast = False

    ensure_plugins_loaded(loaded)

    jobs = loaded.config.jobs
    # 使用覆盖后的 execution
    fail_fast = execution.fail_fast
    if args.jobs:
        jobs = [j for j in jobs if j.name in args.jobs]

    if not jobs:
        logger.warning("No jobs to run.")
        return 0

    tasks: List[Task] = [RunJobTask(loaded, job) for job in jobs]

    failures = 0

    for task in tasks:
        try:
            logger.info(f"Running job: {task.job.name}")
            task.prepare()
            task.run()
        except Exception as e:
            failures += 1
            logger.error(f"Job failed: {task.job.name}: {e}")
            import traceback as tb
            logger.error(tb.format_exc())

            if loaded.config.execution.fail_fast:
                break
        finally:
            try:
                task.close()
            except Exception:
                logger.warning(
                    f"Error during task close: {task.job.name}",
                    exc_info=True,
                )

    logger.info(
        "Run finished: %d succeeded, %d failed",
        len(tasks) - failures,
        failures,
    )

    return 0 if failures == 0 else 5


def cmd_doctor(args: argparse.Namespace) -> int:
    """
    @brief 仅做启动与注册表自检 / Preflight check only.
    """
    project_root = find_project_root_by_pyproject(Path.cwd())
    loaded: LoadedConfig = load_config_by_name(
        args.config_name,
        project_root=project_root,
    )
    set_log_level(getattr(loaded.config, "log_level", "INFO"))
    ensure_plugins_loaded(loaded)

    def dump_registry(name: str, reg) -> None:
        logger.info("%s: %s", name, ", ".join(sorted(reg.keys())))

    dump_registry("sources", SOURCES)
    dump_registry("raw_caches", RAW_CACHES)
    dump_registry("preprocessed_caches", PREPROCESSED_CACHES)
    dump_registry("frontends", FRONTENDS)
    dump_registry("optimizers", OPTIMIZERS)
    dump_registry("backends", BACKENDS)

    logger.info("Doctor check passed.")
    return 0


def cmd_list() -> int:
    """
    @brief 列出当前已注册的插件 / List registered plugins.
    """
    print("Sources:", ", ".join(sorted(SOURCES.keys())))
    print("Raw caches:", ", ".join(sorted(RAW_CACHES.keys())))
    print("Preprocessed caches:", ", ".join(sorted(PREPROCESSED_CACHES.keys())))
    print("Frontends:", ", ".join(sorted(FRONTENDS.keys())))
    print("Optimizers:", ", ".join(sorted(OPTIMIZERS.keys())))
    print("Backends:", ", ".join(sorted(BACKENDS.keys())))
    return 0


# ============================================================
# Main entry
# ============================================================


def main(argv: Optional[List[str]] = None) -> int:
    """
    @brief CLI 主入口 / CLI main entry.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # 日志系统必须最早初始化
    bootstrap()

    try:
        if args.command == "run":
            return cmd_run(args)
        if args.command == "doctor":
            return cmd_doctor(args)
        if args.command == "list":
            return cmd_list()
    except Exception as e:
        logger.error("Fatal error: %s", e)
        logger.debug(traceback.format_exc())
        return 4

    return 0


if __name__ == "__main__":
    sys.exit(main())
