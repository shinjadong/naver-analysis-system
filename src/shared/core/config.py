"""
Core Configuration

핵심 인프라 설정
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum


class LogLevel(Enum):
    """로그 레벨"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class EventBusConfig:
    """이벤트 버스 설정"""
    max_queue_size: int = 1000
    batch_size: int = 10
    process_interval_ms: int = 100
    enable_persistence: bool = False
    persistence_path: str = "data/events.db"


@dataclass
class RegistryConfig:
    """레지스트리 설정"""
    lazy_initialization: bool = True
    auto_wire: bool = True


@dataclass
class LoggingConfig:
    """로깅 설정"""
    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_file_logging: bool = False
    log_file: str = "logs/naver_ai.log"


@dataclass
class CoreConfig:
    """핵심 인프라 전체 설정"""
    event_bus: EventBusConfig = field(default_factory=EventBusConfig)
    registry: RegistryConfig = field(default_factory=RegistryConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # 글로벌 설정
    debug_mode: bool = False
    environment: str = "development"  # development, staging, production

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_bus": {
                "max_queue_size": self.event_bus.max_queue_size,
                "batch_size": self.event_bus.batch_size,
            },
            "registry": {
                "lazy_initialization": self.registry.lazy_initialization,
                "auto_wire": self.registry.auto_wire,
            },
            "logging": {
                "level": self.logging.level.value,
            },
            "debug_mode": self.debug_mode,
            "environment": self.environment
        }

    @classmethod
    def default(cls) -> 'CoreConfig':
        return cls()

    @classmethod
    def for_testing(cls) -> 'CoreConfig':
        return cls(
            debug_mode=True,
            logging=LoggingConfig(level=LogLevel.DEBUG)
        )

    @classmethod
    def for_production(cls) -> 'CoreConfig':
        return cls(
            environment="production",
            event_bus=EventBusConfig(
                max_queue_size=5000,
                enable_persistence=True
            ),
            logging=LoggingConfig(
                level=LogLevel.INFO,
                enable_file_logging=True
            )
        )
