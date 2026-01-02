from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    Iterable,
    Mapping,
    Sequence,
    Union,
)
from abc import ABC, abstractmethod


JsonValue = Union[
    None, bool, int, float, str, Sequence["JsonValue"], Mapping[str, "JsonValue"]
]


@dataclass(frozen=True)
class RawArtifact:
    """
    @brief 原始产物（可缓存、可追溯）/ Raw artifact (cacheable & provenance-aware).
    @note Source 只负责产出 raw，不负责语义统一 / Source outputs raw only; semantic unification belongs to transform.
    """

    source_name: str
    fetched_at_iso: str
    content_type: str
    encoding: str
    cache_path: str
    meta: Dict[str, str]


class DataSource(ABC):
    """
    @brief 数据源纯接口（只定义行为契约，不规定实现结构）
           Pure data source interface (behavior contract only; no implementation structure).
    """

    @classmethod
    @abstractmethod
    def name(cls) -> str:
        """
        @brief 数据源稳定名称（用于 registry key）/ Stable source name (registry key).
        """
        ...

    @classmethod
    @abstractmethod
    def describe(cls) -> Dict[str, str]:
        """
        @brief 数据源静态描述（用于 meta.json 的 provenance）/ Static description for provenance in meta.json.
        """
        ...

    @abstractmethod
    def validate(self, config: Mapping[str, Any]) -> None:
        """
        @brief 校验配置（失败抛异常）/ Validate config (raise on failure).
        @param config 配置对象 / Config object.
        """
        ...

    @abstractmethod
    def fetch(self, config: Mapping[str, Any]) -> Iterable[RawArtifact]:
        """
        @brief 拉取数据并产出 RawArtifact 流 / Fetch data and yield a stream of RawArtifact.
        @param config 配置对象 / Config object.
        @return RawArtifact 迭代器 / Iterable of RawArtifact.
        @note fetch 内部可包含分页、重试、二阶段 discovery、限速等任意实现 / Any internal impl allowed.
        """
        ...
