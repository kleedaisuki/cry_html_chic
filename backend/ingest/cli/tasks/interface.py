from __future__ import annotations

"""
/**
 * @file interface.py
 * @brief Task 接口：Job 生命周期与结果载体的最小协议。
 *
 * Task 的语义：
 * - Task 表示一个 job
 * - Task 是对象生命周期的所有者
 * - Task 必须显式管理 prepare / run / close
 * - Task 统一携带产物、元信息、错误与诊断信息
 *
 * 本模块不：
 * - 规定 lifecycle 调用顺序
 * - 捕获或吞掉异常
 * - 管理调度或并发
 * - 引入任何 base / template 行为
 */
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, MutableMapping, Optional


# ============================================================
# Task state
# ============================================================


class TaskState(str, Enum):
    """
    @brief Task 生命周期状态
           Task lifecycle states.
    """

    CREATED = "created"
    PREPARED = "prepared"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    CLOSED = "closed"


# ============================================================
# Unified result containers
# ============================================================


@dataclass(frozen=True)
class Artifact:
    """
    @brief Task 产物引用
           Task artifact reference.
    """

    kind: str
    path: str
    summary: Optional[str] = None


@dataclass
class TaskError:
    """
    @brief Task 错误信息（可序列化）
           Serializable task error.
    """

    type: str
    message: str
    traceback: Optional[str] = None


@dataclass
class Diagnostics:
    """
    @brief Task 诊断信息容器
           Diagnostics container.
    """

    data: MutableMapping[str, Any] = field(default_factory=dict)


# ============================================================
# Task interface
# ============================================================


class Task(ABC):
    """
    @brief Task 抽象接口（唯一核心抽象）
           Abstract Task interface.

    约定（contract）：
    - Task 是 job 的生命周期所有者
    - Task 持有执行结果与诊断信息
    - Task 的调用顺序由上层决定
    """

    # -----------------------
    # lifecycle
    # -----------------------

    @abstractmethod
    def prepare(self) -> None:
        """
        @brief 准备阶段：构造对象、校验依赖
               Prepare phase.
        """
        raise NotImplementedError

    @abstractmethod
    def run(self) -> None:
        """
        @brief 执行阶段：核心业务逻辑
               Run phase.
        """
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """
        @brief 清理阶段：释放资源（必须幂等）
               Close phase (must be idempotent).
        """
        raise NotImplementedError

    # -----------------------
    # state & results
    # -----------------------

    @property
    @abstractmethod
    def state(self) -> TaskState:
        """
        @brief 当前生命周期状态
               Current lifecycle state.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def artifacts(self) -> list[Artifact]:
        """
        @brief 产物列表
               Produced artifacts.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def meta(self) -> MutableMapping[str, Any]:
        """
        @brief 元数据（可序列化）
               Metadata.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def diagnostics(self) -> Diagnostics:
        """
        @brief 诊断信息
               Diagnostics.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def error(self) -> Optional[TaskError]:
        """
        @brief 错误信息（失败时）
               Error info on failure.
        """
        raise NotImplementedError
