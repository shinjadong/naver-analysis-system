"""
Event Bus System

비동기 이벤트 기반 모듈 통신:
- 발행-구독 패턴
- 타입 안전한 이벤트
- 비동기 핸들러 지원
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import (
    Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Generic,
    Awaitable, Union
)
from datetime import datetime
from enum import Enum
import uuid
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='Event')


# ============================================================
# Event Types
# ============================================================

class EventType(Enum):
    """이벤트 타입"""
    # Persona Events
    PERSONA_CREATED = "persona.created"
    PERSONA_UPDATED = "persona.updated"
    PERSONA_ACTIVATED = "persona.activated"
    PERSONA_DEACTIVATED = "persona.deactivated"

    # Project Events
    PROJECT_CREATED = "project.created"
    PROJECT_STARTED = "project.started"
    PROJECT_PAUSED = "project.paused"
    PROJECT_COMPLETED = "project.completed"
    PROJECT_TARGET_ADDED = "project.target_added"

    # Execution Events
    EXECUTION_STARTED = "execution.started"
    EXECUTION_COMPLETED = "execution.completed"
    EXECUTION_FAILED = "execution.failed"
    EXECUTION_PROGRESS = "execution.progress"

    # IP Events
    IP_ASSIGNED = "ip.assigned"
    IP_RELEASED = "ip.released"
    IP_ROTATION = "ip.rotation"
    IP_HEALTH_CHECK = "ip.health_check"

    # Storyline Events
    STORYLINE_GENERATED = "storyline.generated"
    STORYLINE_STEP_COMPLETED = "storyline.step_completed"
    STORYLINE_ADAPTED = "storyline.adapted"

    # System Events
    SYSTEM_READY = "system.ready"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    SYSTEM_HEALTH = "system.health"

    # Device Events
    DEVICE_CONNECTED = "device.connected"
    DEVICE_DISCONNECTED = "device.disconnected"
    DEVICE_ERROR = "device.error"

    # Campaign Events
    CAMPAIGN_CREATED = "campaign.created"
    CAMPAIGN_STARTED = "campaign.started"
    CAMPAIGN_PAUSED = "campaign.paused"
    CAMPAIGN_COMPLETED = "campaign.completed"
    CAMPAIGN_FAILED = "campaign.failed"


@dataclass
class Event:
    """기본 이벤트"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    event_type: EventType = EventType.SYSTEM_READY
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.event_type, str):
            self.event_type = EventType(self.event_type)


@dataclass
class PersonaEvent(Event):
    """페르소나 관련 이벤트"""
    persona_id: str = ""
    persona_name: str = ""


@dataclass
class ProjectEvent(Event):
    """프로젝트 관련 이벤트"""
    project_id: str = ""
    project_name: str = ""
    target_id: Optional[str] = None


@dataclass
class ExecutionEvent(Event):
    """실행 관련 이벤트"""
    project_id: str = ""
    target_id: str = ""
    persona_id: str = ""
    execution_id: str = ""
    success: Optional[bool] = None
    duration_sec: int = 0
    error_message: Optional[str] = None


@dataclass
class IPEvent(Event):
    """IP 관련 이벤트"""
    persona_id: str = ""
    ip_address: Optional[str] = None
    provider: str = ""
    is_korea: bool = False


@dataclass
class StorylineEvent(Event):
    """스토리라인 관련 이벤트"""
    storyline_id: str = ""
    persona_id: str = ""
    step_index: int = 0
    total_steps: int = 0


# ============================================================
# Event Handler
# ============================================================

EventHandler = Callable[[Event], Awaitable[None]]


class EventSubscriber(ABC):
    """이벤트 구독자 인터페이스"""

    @abstractmethod
    def get_subscribed_events(self) -> List[EventType]:
        """구독할 이벤트 타입 목록"""
        pass

    @abstractmethod
    async def handle_event(self, event: Event) -> None:
        """이벤트 처리"""
        pass


# ============================================================
# Event Bus
# ============================================================

class EventBus:
    """
    비동기 이벤트 버스

    Usage:
        bus = EventBus()

        # 핸들러 등록
        async def on_persona_created(event: PersonaEvent):
            print(f"Persona created: {event.persona_id}")

        bus.subscribe(EventType.PERSONA_CREATED, on_persona_created)

        # 이벤트 발행
        await bus.publish(PersonaEvent(
            event_type=EventType.PERSONA_CREATED,
            persona_id="persona_01"
        ))
    """

    _instance: Optional['EventBus'] = None

    def __new__(cls):
        """싱글톤 패턴"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._subscribers: List[EventSubscriber] = []
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._history: List[Event] = []
        self._max_history = 1000
        self._initialized = True

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler
    ) -> None:
        """이벤트 핸들러 등록"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Handler registered for {event_type.value}")

    def unsubscribe(
        self,
        event_type: EventType,
        handler: EventHandler
    ) -> None:
        """이벤트 핸들러 제거"""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)

    def register_subscriber(self, subscriber: EventSubscriber) -> None:
        """구독자 객체 등록"""
        self._subscribers.append(subscriber)
        for event_type in subscriber.get_subscribed_events():
            self.subscribe(event_type, subscriber.handle_event)

    async def publish(self, event: Event) -> None:
        """이벤트 발행 (비동기)"""
        await self._event_queue.put(event)

        # 히스토리 저장
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

    def publish_sync(self, event: Event) -> None:
        """이벤트 발행 (동기 - 큐에 추가만)"""
        try:
            self._event_queue.put_nowait(event)
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history.pop(0)
        except asyncio.QueueFull:
            logger.warning(f"Event queue full, dropping event: {event.event_type}")

    async def _process_event(self, event: Event) -> None:
        """이벤트 처리"""
        handlers = self._handlers.get(event.event_type, [])

        if not handlers:
            logger.debug(f"No handlers for event: {event.event_type.value}")
            return

        # 모든 핸들러 병렬 실행
        tasks = [handler(event) for handler in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 에러 로깅
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Handler error for {event.event_type.value}: {result}"
                )

    async def start(self) -> None:
        """이벤트 처리 루프 시작"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._event_loop())
        logger.info("EventBus started")

    async def stop(self) -> None:
        """이벤트 처리 루프 중지"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("EventBus stopped")

    async def _event_loop(self) -> None:
        """메인 이벤트 루프"""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                await self._process_event(event)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event loop error: {e}")

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100
    ) -> List[Event]:
        """이벤트 히스토리 조회"""
        events = self._history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    @property
    def pending_count(self) -> int:
        """대기 중인 이벤트 수"""
        return self._event_queue.qsize()

    @classmethod
    def get_instance(cls) -> 'EventBus':
        """싱글톤 인스턴스 반환"""
        return cls()


# ============================================================
# Event Decorators
# ============================================================

def event_handler(event_type: EventType):
    """이벤트 핸들러 데코레이터"""
    def decorator(func: EventHandler):
        EventBus.get_instance().subscribe(event_type, func)
        return func
    return decorator


def on_event(*event_types: EventType):
    """다중 이벤트 핸들러 데코레이터"""
    def decorator(func: EventHandler):
        bus = EventBus.get_instance()
        for event_type in event_types:
            bus.subscribe(event_type, func)
        return func
    return decorator


# ============================================================
# Event Emitter Mixin
# ============================================================

class EventEmitter:
    """이벤트 발행 믹스인"""

    def __init__(self):
        self._event_bus = EventBus.get_instance()
        self._source_name = self.__class__.__name__

    async def emit(self, event: Event) -> None:
        """이벤트 발행"""
        event.source = self._source_name
        await self._event_bus.publish(event)

    def emit_sync(self, event: Event) -> None:
        """동기 이벤트 발행"""
        event.source = self._source_name
        self._event_bus.publish_sync(event)
