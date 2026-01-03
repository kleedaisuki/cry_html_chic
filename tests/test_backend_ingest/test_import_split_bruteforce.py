# -*- coding: utf-8 -*-

"""
@brief 模块身份分裂取证脚本：检测同一源码是否被加载为多个模块实例（module identity split）
@brief Module identity split forensic probe: detect whether the same source file is loaded as multiple modules

用法 / Usage:
    1) 推荐（模块方式） / Recommended (module mode):
       python -m tests.test_import_split_bruteforce

    2) 也可（脚本方式） / Also possible (script mode):
       python tests/test_import_split_bruteforce.py

输出重点 / What to look for:
    - 同一 __file__ 对应多个模块名（same __file__ mapped to multiple module names）
    - 同一模块名对应不同 __file__（same module name mapped to different __file__）
    - DataSource 的 identity（id/模块名/文件路径）
"""

from __future__ import annotations

import datetime as _dt
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import DefaultDict, Iterable, List, Optional, Tuple
from collections import defaultdict


@dataclass(frozen=True)
class ModuleRecord:
    """
    @brief 单个模块记录：模块名 + 绝对文件路径（若有）
    @brief A single module record: module name + absolute file path (if any)
    """

    name: str
    file: Optional[str]


def _now_iso() -> str:
    """
    @brief 获取当前时间 ISO 字符串，用于日志头
    @brief Get current time as ISO string for log headers

    @return 当前时间 ISO 字符串 / ISO string of current time
    """
    return _dt.datetime.now().isoformat(timespec="seconds")


def _abs_path(p: Optional[str]) -> Optional[str]:
    """
    @brief 将路径转换为规范化绝对路径，失败则原样返回
    @brief Normalize to absolute path, fallback to original if resolution fails

    @param p 输入路径 / Input path
    @return 规范化绝对路径 / Normalized absolute path
    """
    if not p:
        return None
    try:
        return str(Path(p).resolve())
    except Exception:
        return p


def _collect_modules_by_prefix(prefix: str) -> List[ModuleRecord]:
    """
    @brief 收集 sys.modules 中以 prefix 开头的模块，并记录其 __file__
    @brief Collect modules in sys.modules whose names start with prefix and record their __file__

    @param prefix 模块名前缀 / Module name prefix
    @return 模块记录列表 / List of module records
    """
    records: List[ModuleRecord] = []
    for name, mod in list(sys.modules.items()):
        if not name.startswith(prefix):
            continue
        file = _abs_path(getattr(mod, "__file__", None))
        records.append(ModuleRecord(name=name, file=file))
    records.sort(key=lambda r: (r.file or "", r.name))
    return records


def _group_by_file(
    records: Iterable[ModuleRecord],
) -> DefaultDict[Optional[str], List[str]]:
    """
    @brief 按文件路径将模块记录分组，用于发现“同一文件多模块名”
    @brief Group module records by file path to detect "same file, multiple module names"

    @param records 模块记录 / Module records
    @return file -> [module_names] 映射 / mapping file -> [module_names]
    """
    by_file: DefaultDict[Optional[str], List[str]] = defaultdict(list)
    for r in records:
        by_file[r.file].append(r.name)
    for _, names in by_file.items():
        names.sort()
    return by_file


def _print_header(title: str) -> None:
    """
    @brief 打印分节标题
    @brief Print a section header

    @param title 标题 / Title
    @return 无 / None
    """
    print(f"\n=== {title} ===")


def _print_sys_context() -> None:
    """
    @brief 输出运行时上下文（解释器与 sys.path），用于复现实验环境
    @brief Print runtime context (executable and sys.path) for reproducibility

    @return 无 / None
    """
    _print_header("Context")
    print("time:", _now_iso())
    print("sys.executable:", sys.executable)
    print("sys.argv:", sys.argv)

    _print_header("sys.path")
    for p in sys.path:
        print(" ", p)


def _import_and_report_datasource() -> (
    Tuple[Optional[int], Optional[str], Optional[str]]
):
    """
    @brief 导入 ingest.sources.interface 并报告 DataSource 的 identity 信息
    @brief Import ingest.sources.interface and report DataSource identity info

    @return (DataSource_id, DataSource_module, interface_file) / tuple of identity info
    """
    _print_header("DataSource identity (before importing datamall)")
    import ingest.sources.interface as iface  # noqa: F401

    interface_file = _abs_path(getattr(iface, "__file__", None))
    ds = getattr(iface, "DataSource", None)

    if ds is None:
        print("ERROR: ingest.sources.interface has no attribute 'DataSource'")
        return None, None, interface_file

    ds_id = id(ds)
    ds_mod = getattr(ds, "__module__", None)

    print("interface.__file__:", interface_file)
    print("DataSource:", ds)
    print("DataSource.id:", ds_id)
    print("DataSource.__module__:", ds_mod)

    return ds_id, ds_mod, interface_file


def _try_import_datamall() -> None:
    """
    @brief 尝试导入 ingest.sources.datamall；失败时保留完整异常堆栈
    @brief Try importing ingest.sources.datamall; on failure, preserve full traceback

    @return 无 / None
    """
    _print_header("Import ingest.sources.datamall")
    try:
        import ingest.sources.datamall as _datamall  # noqa: F401

        print("OK: datamall imported successfully.")
    except Exception as e:
        print("FAILED:", repr(e))
        print("--- traceback ---")
        print(traceback.format_exc().rstrip())
        print("--- end traceback ---")


def _dump_identity_anomalies(prefixes: Iterable[str]) -> None:
    """
    @brief 输出模块加载异常：同一文件多模块名 / 同一模块名多文件（通过收集结果间接观察）
    @brief Dump identity anomalies: same file multiple names / same name multiple files (via collected records)

    @param prefixes 要检查的模块名前缀集合 / Module name prefixes to inspect
    @return 无 / None
    """
    for prefix in prefixes:
        records = _collect_modules_by_prefix(prefix)
        by_file = _group_by_file(records)

        _print_header(f"sys.modules snapshot: prefix={prefix!r} (count={len(records)})")

        # 1) 全量列出（用于精确对照）
        for r in records:
            print(f"{r.name:<40} -> {r.file}")

        # 2) 重点异常：同一 file 对应多个 module name
        dup = [
            (f, names)
            for f, names in by_file.items()
            if f is not None and len(names) > 1
        ]
        if dup:
            _print_header(
                f"ANOMALY: same file mapped to multiple module names (prefix={prefix!r})"
            )
            for f, names in sorted(dup, key=lambda x: x[0] or ""):
                print("FILE:", f)
                for n in names:
                    print("  -", n)


def main() -> None:
    """
    @brief 主入口：打印环境、导入 interface、尝试导入 datamall、最后 dump sys.modules 现场
    @brief Entry point: print env, import interface, try import datamall, then dump sys.modules state

    @return 无 / None
    """
    _print_sys_context()

    # 先拿到 DataSource 的身份信息（不依赖 datamall）
    _import_and_report_datasource()

    # 再尝试触发 datamall 的装饰器注册（这一步会复现你的报错）
    _try_import_datamall()

    # 最后把现场所有相关模块列出来，便于判断是否存在“双份加载”
    _dump_identity_anomalies(prefixes=("ingest", "ingest.sources", "ingest.cli"))


if __name__ == "__main__":
    main()
