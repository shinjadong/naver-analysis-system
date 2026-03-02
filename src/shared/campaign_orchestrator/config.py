"""
Orchestrator Configuration

오케스트레이터 설정
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class ExecutionMode(Enum):
    """실행 모드"""
    SEQUENTIAL = "sequential"      # 순차 실행
    PARALLEL = "parallel"          # 병렬 실행
    BATCH = "batch"               # 배치 실행
    CONTINUOUS = "continuous"      # 연속 실행


class ScheduleMode(Enum):
    """스케줄 모드"""
    IMMEDIATE = "immediate"        # 즉시 실행
    SCHEDULED = "scheduled"        # 예약 실행
    INTERVAL = "interval"          # 주기 실행
    CRON = "cron"                  # 크론 스케줄


@dataclass
class ExecutionConfig:
    """실행 설정"""
    mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    max_concurrent: int = 3        # 최대 동시 실행 수
    task_timeout_sec: int = 300    # 작업 타임아웃
    retry_count: int = 3           # 재시도 횟수
    retry_delay_sec: int = 30      # 재시도 대기
    cooldown_sec: int = 60         # 작업 간 쿨다운


@dataclass
class ScheduleConfig:
    """스케줄 설정"""
    mode: ScheduleMode = ScheduleMode.IMMEDIATE
    daily_quota: int = 50          # 일일 할당량
    max_per_hour: int = 10         # 시간당 최대
    active_hours: List[int] = field(default_factory=lambda: list(range(9, 22)))
    blackout_hours: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5])


@dataclass
class ResourceConfig:
    """리소스 설정"""
    max_devices: int = 5           # 최대 디바이스 수
    max_personas: int = 20         # 최대 페르소나 수
    ip_rotation: bool = True       # IP 로테이션
    device_rotation: bool = True   # 디바이스 로테이션


@dataclass
class MonitoringConfig:
    """모니터링 설정"""
    enable_metrics: bool = True
    enable_logging: bool = True
    log_level: str = "INFO"
    metrics_interval_sec: int = 60
    alert_on_failure: bool = True
    failure_threshold: int = 5


@dataclass
class OrchestratorConfig:
    """오케스트레이터 전체 설정"""
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    resource: ResourceConfig = field(default_factory=ResourceConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)

    # 이벤트 설정
    publish_events: bool = True
    event_batch_size: int = 10

    # 연동 설정
    auto_assign_ip: bool = True
    auto_generate_storyline: bool = True
    persist_state: bool = True
    state_file: str = "data/orchestrator_state.json"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution": {
                "mode": self.execution.mode.value,
                "max_concurrent": self.execution.max_concurrent,
                "task_timeout_sec": self.execution.task_timeout_sec
            },
            "schedule": {
                "mode": self.schedule.mode.value,
                "daily_quota": self.schedule.daily_quota,
                "active_hours": self.schedule.active_hours
            },
            "resource": {
                "max_devices": self.resource.max_devices,
                "max_personas": self.resource.max_personas,
                "ip_rotation": self.resource.ip_rotation
            },
            "monitoring": {
                "enable_metrics": self.monitoring.enable_metrics,
                "log_level": self.monitoring.log_level
            }
        }

    @classmethod
    def default(cls) -> 'OrchestratorConfig':
        return cls()

    @classmethod
    def for_testing(cls) -> 'OrchestratorConfig':
        """테스트용 설정"""
        return cls(
            execution=ExecutionConfig(
                mode=ExecutionMode.SEQUENTIAL,
                max_concurrent=1,
                task_timeout_sec=60
            ),
            schedule=ScheduleConfig(
                mode=ScheduleMode.IMMEDIATE,
                daily_quota=10
            ),
            monitoring=MonitoringConfig(
                enable_metrics=False
            )
        )

    @classmethod
    def for_production(cls) -> 'OrchestratorConfig':
        """프로덕션용 설정"""
        return cls(
            execution=ExecutionConfig(
                mode=ExecutionMode.PARALLEL,
                max_concurrent=5,
                task_timeout_sec=600
            ),
            schedule=ScheduleConfig(
                mode=ScheduleMode.INTERVAL,
                daily_quota=100,
                max_per_hour=20
            ),
            resource=ResourceConfig(
                max_devices=10,
                max_personas=50
            ),
            monitoring=MonitoringConfig(
                enable_metrics=True,
                alert_on_failure=True
            )
        )
