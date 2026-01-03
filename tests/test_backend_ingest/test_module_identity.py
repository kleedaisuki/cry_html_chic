# tests/test_backend_ingest/test_module_identity.py
"""
@brief 模块身份探针：检测同一源码是否被加载为多个模块实例
@brief Module identity probe: detect duplicate module loading

运行方式（非常重要）：
    1 python -m tests.test_module_identity
    2 python tests/test_module_identity.py

请分别跑两次，对比输出。
"""

import sys
from collections import defaultdict
from pathlib import Path


def dump_duplicate_modules():
    """
    @brief 枚举 sys.modules，找出“同一文件对应多个模块名”的情况
    @brief Enumerate sys.modules and find duplicated file-backed modules
    """
    by_file = defaultdict(list)

    for name, mod in sys.modules.items():
        file = getattr(mod, "__file__", None)
        if file:
            try:
                file = str(Path(file).resolve())
            except Exception:
                pass
            by_file[file].append(name)

    print("\n=== Duplicate module files (same file, multiple module names) ===")
    for file, names in sorted(by_file.items()):
        if len(names) > 1:
            print(f"\nFILE: {file}")
            for n in names:
                print(f"  - {n}")


def inspect_datasource_identity():
    """
    @brief 检查 DataSource / DataMallSource 的 identity 是否分裂
    @brief Inspect identity split of DataSource and implementations
    """
    print("\n=== Inspect DataSource identity ===")

    # 强制导入你真实使用的路径
    import ingest.sources.interface as iface
    import ingest.sources.datamall as datamall

    DataSource = iface.DataSource
    DataMallSource = datamall.DataMallSource

    print("DataSource:")
    print("  object:", DataSource)
    print("  id:", id(DataSource))
    print("  module:", DataSource.__module__)
    print("  file:", sys.modules[DataSource.__module__].__file__)

    print("\nDataMallSource:")
    print("  object:", DataMallSource)
    print("  id:", id(DataMallSource))
    print("  module:", DataMallSource.__module__)
    print("  file:", sys.modules[DataMallSource.__module__].__file__)

    print(
        "\nissubclass(DataMallSource, DataSource) =",
        issubclass(DataMallSource, DataSource),
    )

    print("\nMRO:")
    for cls in DataMallSource.__mro__:
        print(f"  {cls}  id={id(cls)}  module={cls.__module__}")


def inspect_runtime_singleton():
    """
    @brief 检查 runtime.py 是否被加载成多份
    @brief Check whether runtime module is duplicated
    """
    print("\n=== Inspect runtime module identity ===")

    import ingest.cli.runtime as rt

    runtime_file = Path(rt.__file__).resolve()
    print("runtime file:", runtime_file)

    keys = [
        name
        for name, mod in sys.modules.items()
        if getattr(mod, "__file__", None)
        and Path(mod.__file__).resolve() == runtime_file
    ]

    print("runtime module keys:")
    for k in keys:
        print("  -", k)


def main():
    print("=== sys.executable ===")
    print(sys.executable)

    print("\n=== sys.path ===")
    for p in sys.path:
        print(" ", p)

    inspect_runtime_singleton()
    inspect_datasource_identity()
    dump_duplicate_modules()


if __name__ == "__main__":
    main()
