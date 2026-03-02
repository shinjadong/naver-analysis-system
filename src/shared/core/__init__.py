"""
Core Infrastructure

프로덕션 레벨 모듈 통합을 위한 핵심 인프라:
- 이벤트 버스 (모듈 간 비동기 통신)
- 프로토콜 정의 (인터페이스)
- 기본 클래스
"""

from .events import EventBus, Event, EventHandler, EventType
from .protocols import (
    PersonaProvider,
    IPProvider,
    StorylineProvider,
    ProjectProvider,
    ExecutionProvider,
)
from .registry import ModuleRegistry
from .config import CoreConfig

__all__ = [
    # Events
    "EventBus",
    "Event",
    "EventHandler",
    "EventType",

    # Protocols
    "PersonaProvider",
    "IPProvider",
    "StorylineProvider",
    "ProjectProvider",
    "ExecutionProvider",

    # Registry
    "ModuleRegistry",

    # Config
    "CoreConfig",
]

__version__ = "0.1.0"
