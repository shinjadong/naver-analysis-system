"""
Module Registry

모듈 등록 및 의존성 주입:
- 싱글톤 모듈 관리
- 지연 초기화
- 의존성 해결
"""

import logging
from typing import (
    Dict, Type, TypeVar, Optional, Any, Callable, List,
    get_type_hints
)
from dataclasses import dataclass, field
import inspect
import asyncio

from .protocols import (
    PersonaProvider,
    IPProvider,
    StorylineProvider,
    ProjectProvider,
    ExecutionProvider,
    OrchestratorProtocol,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class ModuleInfo:
    """모듈 정보"""
    name: str
    module_type: Type
    instance: Optional[Any] = None
    factory: Optional[Callable] = None
    singleton: bool = True
    dependencies: List[str] = field(default_factory=list)
    initialized: bool = False


class ModuleRegistry:
    """
    모듈 레지스트리

    Usage:
        registry = ModuleRegistry()

        # 모듈 등록
        registry.register("persona_provider", PersonaManagerAdapter)
        registry.register("ip_provider", IPManagerAdapter, singleton=True)

        # 팩토리 함수로 등록
        registry.register_factory("storyline_provider", create_storyline_provider)

        # 모듈 조회
        persona_provider = await registry.get(PersonaProvider)
    """

    _instance: Optional['ModuleRegistry'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._modules: Dict[str, ModuleInfo] = {}
        self._type_mapping: Dict[Type, str] = {}
        self._lock = asyncio.Lock()
        self._initialized = True

    def register(
        self,
        name: str,
        module_type: Type[T],
        singleton: bool = True,
        dependencies: List[str] = None
    ) -> None:
        """
        모듈 등록

        Args:
            name: 모듈 이름
            module_type: 모듈 클래스
            singleton: 싱글톤 여부
            dependencies: 의존성 모듈 이름 목록
        """
        self._modules[name] = ModuleInfo(
            name=name,
            module_type=module_type,
            singleton=singleton,
            dependencies=dependencies or []
        )

        # 프로토콜 타입 매핑 (상속 관계 확인)
        for protocol in [
            PersonaProvider, IPProvider, StorylineProvider,
            ProjectProvider, ExecutionProvider, OrchestratorProtocol
        ]:
            if self._implements_protocol(module_type, protocol):
                self._type_mapping[protocol] = name

        logger.debug(f"Module registered: {name} ({module_type.__name__})")

    def register_factory(
        self,
        name: str,
        factory: Callable,
        singleton: bool = True,
        dependencies: List[str] = None
    ) -> None:
        """팩토리 함수로 모듈 등록"""
        # 반환 타입 추론
        hints = get_type_hints(factory)
        return_type = hints.get('return', object)

        self._modules[name] = ModuleInfo(
            name=name,
            module_type=return_type,
            factory=factory,
            singleton=singleton,
            dependencies=dependencies or []
        )

        logger.debug(f"Factory registered: {name}")

    def register_instance(
        self,
        name: str,
        instance: Any,
        protocol_type: Type = None
    ) -> None:
        """인스턴스 직접 등록"""
        self._modules[name] = ModuleInfo(
            name=name,
            module_type=type(instance),
            instance=instance,
            singleton=True,
            initialized=True
        )

        if protocol_type:
            self._type_mapping[protocol_type] = name

        logger.debug(f"Instance registered: {name}")

    async def get(self, type_or_name) -> Optional[Any]:
        """
        모듈 조회

        Args:
            type_or_name: 프로토콜 타입 또는 모듈 이름

        Returns:
            모듈 인스턴스
        """
        # 타입으로 조회
        if isinstance(type_or_name, type):
            name = self._type_mapping.get(type_or_name)
            if not name:
                logger.warning(f"No module found for type: {type_or_name}")
                return None
        else:
            name = type_or_name

        if name not in self._modules:
            logger.warning(f"Module not found: {name}")
            return None

        module_info = self._modules[name]

        # 이미 초기화된 싱글톤
        if module_info.singleton and module_info.instance:
            return module_info.instance

        # 초기화
        async with self._lock:
            return await self._initialize_module(module_info)

    async def _initialize_module(self, module_info: ModuleInfo) -> Any:
        """모듈 초기화"""
        # 이미 초기화됨 (더블체크)
        if module_info.initialized and module_info.instance:
            return module_info.instance

        # 의존성 해결
        deps = {}
        for dep_name in module_info.dependencies:
            dep = await self.get(dep_name)
            if dep is None:
                raise RuntimeError(f"Dependency not found: {dep_name}")
            deps[dep_name] = dep

        # 인스턴스 생성
        if module_info.factory:
            # 팩토리 함수 사용
            if asyncio.iscoroutinefunction(module_info.factory):
                instance = await module_info.factory(**deps)
            else:
                instance = module_info.factory(**deps)
        else:
            # 클래스 직접 생성
            instance = module_info.module_type(**deps)

        # async 초기화 메서드 호출
        if hasattr(instance, 'initialize'):
            if asyncio.iscoroutinefunction(instance.initialize):
                await instance.initialize()
            else:
                instance.initialize()

        if module_info.singleton:
            module_info.instance = instance
            module_info.initialized = True

        logger.info(f"Module initialized: {module_info.name}")
        return instance

    async def initialize_all(self) -> None:
        """모든 모듈 초기화"""
        # 의존성 순서대로 초기화
        initialized = set()
        pending = list(self._modules.keys())

        while pending:
            progress = False
            for name in list(pending):
                module_info = self._modules[name]

                # 의존성 확인
                deps_ready = all(
                    dep in initialized
                    for dep in module_info.dependencies
                )

                if deps_ready:
                    await self.get(name)
                    initialized.add(name)
                    pending.remove(name)
                    progress = True

            if not progress and pending:
                raise RuntimeError(
                    f"Circular dependency detected: {pending}"
                )

        logger.info("All modules initialized")

    async def shutdown_all(self) -> None:
        """모든 모듈 종료"""
        for name, module_info in self._modules.items():
            if module_info.instance and hasattr(module_info.instance, 'shutdown'):
                try:
                    if asyncio.iscoroutinefunction(module_info.instance.shutdown):
                        await module_info.instance.shutdown()
                    else:
                        module_info.instance.shutdown()
                    logger.debug(f"Module shutdown: {name}")
                except Exception as e:
                    logger.error(f"Error shutting down {name}: {e}")

        logger.info("All modules shutdown")

    def list_modules(self) -> Dict[str, dict]:
        """등록된 모듈 목록"""
        return {
            name: {
                "type": info.module_type.__name__,
                "singleton": info.singleton,
                "initialized": info.initialized,
                "dependencies": info.dependencies
            }
            for name, info in self._modules.items()
        }

    def _implements_protocol(self, cls: Type, protocol: Type) -> bool:
        """프로토콜 구현 여부 확인"""
        try:
            # 런타임 프로토콜 체크
            return isinstance(cls, type) and issubclass(cls, protocol)
        except TypeError:
            # Protocol 상속이 아닌 경우 메서드 시그니처로 확인
            protocol_methods = set(
                name for name in dir(protocol)
                if not name.startswith('_') and callable(getattr(protocol, name, None))
            )
            cls_methods = set(
                name for name in dir(cls)
                if not name.startswith('_') and callable(getattr(cls, name, None))
            )
            return protocol_methods.issubset(cls_methods)

    @classmethod
    def get_instance(cls) -> 'ModuleRegistry':
        """싱글톤 인스턴스"""
        return cls()
