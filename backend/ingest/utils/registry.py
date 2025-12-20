# backend/ingest/utils/registry.py
from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    Iterator,
    Optional,
    Type,
    TypeVar,
)


TBase = TypeVar("TBase")


@dataclass(frozen=True)
class RegistryItem(Generic[TBase]):
    """
    /**
     * @brief 注册表条目：记录名字与类，并保留少量元信息 / Registry item: maps name to class with minimal metadata.
     *
     * @note 只存“类”（class），不存“对象”（instance），避免 state 泄漏 / Store classes only, not instances, to avoid state leakage.
     */
    """

    name: str
    cls: Type[TBase]
    module: str
    qualname: str


class RegistryError(RuntimeError):
    """
    /**
     * @brief 注册表通用异常 / Generic registry error.
     */
    """


class DuplicateRegistrationError(RegistryError):
    """
    /**
     * @brief 重复注册异常：同名被注册到不同类 / Duplicate registration: same name mapped to different classes.
     */
    """


class NotFoundError(RegistryError):
    """
    /**
     * @brief 未找到异常：名字未注册 / Not found: name is not registered.
     */
    """


class InvalidRegistrationError(RegistryError):
    """
    /**
     * @brief 非法注册异常：注册的不是 class 或不满足基类约束 / Invalid registration: not a class or violates base constraint.
     */
    """


def _normalize_name(name: str) -> str:
    """
    /**
     * @brief 规范化 name：去空白、转小写 / Normalize name: strip and lowercase.
     *
     * @param name
     *        注册名 / Registry name.
     * @return
     *        规范化后的名字 / Normalized name.
     */
    """
    if not isinstance(name, str):
        raise InvalidRegistrationError(
            f"registry name must be str, got {type(name).__name__}"
        )
    n = name.strip()
    if not n:
        raise InvalidRegistrationError("registry name must be non-empty after strip()")
    return n.lower()


class Registry(Generic[TBase]):
    """
    /**
     * @brief 轻量注册表：name -> class，不负责对象生命周期 / Lightweight registry: name -> class, not object lifecycle.
     *
     * @note
     * - A2：registry 只做“名字→类”，不做单例、不缓存实例 / A2: store classes only, no singletons, no instances.
     * - 支持可选 base 约束，用于确保注册对象是某接口/抽象基类的实现 / Optional base constraint to ensure classes implement an interface/ABC.
     */
    """

    def __init__(self, namespace: str, base: Optional[Type[TBase]] = None) -> None:
        """
        /**
         * @brief 创建注册表 / Create a registry.
         *
         * @param namespace
         *        命名空间（用于错误信息与调试）/ Namespace (for errors and debugging).
         * @param base
         *        可选基类约束：要求注册的 cls 必须是 base 的子类 / Optional base constraint: cls must be subclass of base.
         */
        """
        if not isinstance(namespace, str) or not namespace.strip():
            raise ValueError("namespace must be a non-empty string")
        self._namespace: str = namespace.strip()
        self._base: Optional[Type[TBase]] = base
        self._items: Dict[str, RegistryItem[TBase]] = {}

    @property
    def namespace(self) -> str:
        """
        /**
         * @brief 获取命名空间 / Get namespace.
         */
        """
        return self._namespace

    @property
    def base(self) -> Optional[Type[TBase]]:
        """
        /**
         * @brief 获取基类约束 / Get base constraint.
         */
        """
        return self._base

    def register(
        self,
        name: str,
        cls: Optional[Type[TBase]] = None,
        *,
        override: bool = False,
    ) -> Any:
        """
        /**
         * @brief 注册一个类到 registry / Register a class into registry.
         *
         * @param name
         *        注册名（建议使用 config 里出现的短名字）/ Registry name (recommended: short name used in configs).
         * @param cls
         *        要注册的类；若为 None，则返回装饰器 / Class to register; if None, returns a decorator.
         * @param override
         *        是否允许覆盖同名注册（慎用，默认 False）/ Allow overriding same name (default False).
         *
         * @return
         *        若直接注册：返回 cls；若装饰器：返回 decorator / If direct: returns cls; if decorator: returns decorator.
         */
        """
        normalized = _normalize_name(name)

        def _do_register(target_cls: Type[TBase]) -> Type[TBase]:
            self._validate_registration(normalized, target_cls)
            item = RegistryItem(
                name=normalized,
                cls=target_cls,
                module=getattr(target_cls, "__module__", "<unknown>"),
                qualname=getattr(
                    target_cls,
                    "__qualname__",
                    getattr(target_cls, "__name__", "<unknown>"),
                ),
            )

            if normalized in self._items and not override:
                old = self._items[normalized]
                if old.cls is target_cls:
                    # 幂等：同一个类重复注册不算错 / Idempotent: re-register same class is ok.
                    return target_cls
                raise DuplicateRegistrationError(
                    f"[{self._namespace}] name '{normalized}' already registered: "
                    f"{old.module}.{old.qualname} -> cannot register {item.module}.{item.qualname}"
                )

            self._items[normalized] = item
            return target_cls

        # decorator form: @registry.register("datamall")
        if cls is None:

            def decorator(target_cls: Type[TBase]) -> Type[TBase]:
                return _do_register(target_cls)

            return decorator

        # direct form: registry.register("datamall", DataMallSource)
        return _do_register(cls)

    def get(self, name: str) -> Optional[Type[TBase]]:
        """
        /**
         * @brief 获取已注册类；不存在则返回 None / Get registered class; return None if not found.
         *
         * @param name
         *        注册名 / Registry name.
         * @return
         *        对应的类或 None / Corresponding class or None.
         */
        """
        normalized = _normalize_name(name)
        item = self._items.get(normalized)
        return None if item is None else item.cls

    def require(self, name: str) -> Type[TBase]:
        """
        /**
         * @brief 获取已注册类；不存在则抛异常 / Get registered class; raise if not found.
         *
         * @param name
         *        注册名 / Registry name.
         * @return
         *        对应的类 / Corresponding class.
         * @throws NotFoundError
         *         当 name 未注册 / When name is not registered.
         */
        """
        cls = self.get(name)
        if cls is None:
            available = ", ".join(self.keys())
            raise NotFoundError(
                f"[{self._namespace}] name '{_normalize_name(name)}' not found. available=[{available}]"
            )
        return cls

    def keys(self) -> Iterable[str]:
        """
        /**
         * @brief 列出所有注册名（排序）/ List all registered names (sorted).
         */
        """
        return tuple(sorted(self._items.keys()))

    def items(self) -> Iterable[RegistryItem[TBase]]:
        """
        /**
         * @brief 列出所有条目（按 name 排序）/ List all items (sorted by name).
         */
        """
        return tuple(self._items[k] for k in sorted(self._items.keys()))

    def __contains__(self, name: object) -> bool:
        """
        /**
         * @brief 判断 name 是否已注册 / Check if name is registered.
         */
        """
        if not isinstance(name, str):
            return False
        return _normalize_name(name) in self._items

    def __len__(self) -> int:
        """
        /**
         * @brief 注册数量 / Number of registered items.
         */
        """
        return len(self._items)

    def __iter__(self) -> Iterator[str]:
        """
        /**
         * @brief 迭代所有 keys（排序）/ Iterate keys (sorted).
         */
        """
        return iter(self.keys())

    def _validate_registration(self, normalized_name: str, target_cls: Any) -> None:
        """
        /**
         * @brief 校验注册输入是否合法 / Validate registration input.
         *
         * @param normalized_name
         *        已规范化的 name / Normalized name.
         * @param target_cls
         *        待注册对象 / Target to register.
         * @return
         *        None
         */
        """
        # 只允许 class，禁止 instance / Only allow classes, forbid instances.
        if not isinstance(target_cls, type):
            raise InvalidRegistrationError(
                f"[{self._namespace}] cannot register non-class for name '{normalized_name}': "
                f"got {type(target_cls).__name__}"
            )

        # 可选 base 约束：必须是 base 的子类 / Optional base constraint: must be subclass of base.
        if self._base is not None:
            try:
                ok = issubclass(target_cls, self._base)  # type: ignore[arg-type]
            except TypeError:
                ok = False
            if not ok:
                raise InvalidRegistrationError(
                    f"[{self._namespace}] class {target_cls.__module__}.{target_cls.__qualname__} "
                    f"must be a subclass of {self._base.__module__}.{self._base.__qualname__}"
                )

