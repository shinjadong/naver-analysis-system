"""
Project Schema

프로젝트 관리를 위한 데이터 구조
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime, date, timedelta
import uuid
import json


class ProjectStatus(Enum):
    """프로젝트 상태"""
    DRAFT = "draft"              # 초안 (설정 중)
    ACTIVE = "active"            # 활성 (실행 중)
    PAUSED = "paused"            # 일시 정지
    COMPLETED = "completed"      # 완료
    ARCHIVED = "archived"        # 보관


@dataclass
class ProjectTarget:
    """프로젝트 타겟 (키워드-제목-URL)"""
    target_id: str
    keyword: str
    blog_title: str
    url: Optional[str] = None

    # 목표
    target_clicks: int = 10          # 목표 클릭 수
    target_dwell_time: int = 120     # 목표 체류 시간 (초)
    target_scroll_depth: float = 0.8 # 목표 스크롤 깊이

    # 실적
    total_clicks: int = 0
    total_dwell_time: int = 0        # 누적 체류 시간
    avg_scroll_depth: float = 0.0
    success_count: int = 0
    fail_count: int = 0

    # 메타
    created_at: datetime = field(default_factory=datetime.now)
    last_executed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "target_id": self.target_id,
            "keyword": self.keyword,
            "blog_title": self.blog_title,
            "url": self.url,
            "target_clicks": self.target_clicks,
            "total_clicks": self.total_clicks,
            "total_dwell_time": self.total_dwell_time,
            "avg_scroll_depth": self.avg_scroll_depth,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "progress": self.progress,
        }

    @property
    def progress(self) -> float:
        """진행률 (0-100)"""
        if self.target_clicks == 0:
            return 100.0
        return min(100.0, (self.total_clicks / self.target_clicks) * 100)

    @property
    def is_completed(self) -> bool:
        """목표 달성 여부"""
        return self.total_clicks >= self.target_clicks


@dataclass
class ExecutionRecord:
    """실행 기록"""
    record_id: str
    project_id: str
    target_id: str
    persona_id: str
    device_serial: Optional[str] = None

    # 실행 정보
    executed_at: datetime = field(default_factory=datetime.now)
    duration_sec: int = 0
    scroll_depth: float = 0.0
    interactions: int = 0

    # 결과
    success: bool = False
    error_message: Optional[str] = None

    # IP 정보
    ip_address: Optional[str] = None
    ip_provider: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "project_id": self.project_id,
            "target_id": self.target_id,
            "persona_id": self.persona_id,
            "device_serial": self.device_serial,
            "executed_at": self.executed_at.isoformat(),
            "duration_sec": self.duration_sec,
            "scroll_depth": self.scroll_depth,
            "interactions": self.interactions,
            "success": self.success,
            "ip_address": self.ip_address,
        }


@dataclass
class DailyStats:
    """일별 통계"""
    date: date
    project_id: str

    # 실행 통계
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0

    # 시간 통계
    total_dwell_time: int = 0        # 초
    avg_dwell_time: float = 0.0

    # 페르소나/디바이스 통계
    unique_personas: int = 0
    unique_devices: int = 0
    unique_ips: int = 0

    # 타겟 통계
    targets_executed: int = 0
    targets_completed: int = 0

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "success_rate": self.success_rate,
            "total_dwell_time": self.total_dwell_time,
            "avg_dwell_time": self.avg_dwell_time,
            "unique_personas": self.unique_personas,
            "unique_devices": self.unique_devices,
            "unique_ips": self.unique_ips,
        }

    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return (self.successful_executions / self.total_executions) * 100


@dataclass
class ProjectStats:
    """프로젝트 전체 통계"""
    project_id: str

    # 전체 실행 통계
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0

    # 시간 통계
    total_dwell_time: int = 0
    avg_dwell_time: float = 0.0
    avg_scroll_depth: float = 0.0

    # 리소스 통계
    total_personas_used: int = 0
    total_devices_used: int = 0
    total_ips_used: int = 0

    # 타겟 통계
    total_targets: int = 0
    completed_targets: int = 0

    # 일별 통계
    daily_stats: List[DailyStats] = field(default_factory=list)

    # 기간
    first_execution: Optional[datetime] = None
    last_execution: Optional[datetime] = None
    active_days: int = 0

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "success_rate": self.success_rate,
            "total_dwell_time": self.total_dwell_time,
            "avg_dwell_time": self.avg_dwell_time,
            "avg_scroll_depth": self.avg_scroll_depth,
            "total_personas_used": self.total_personas_used,
            "total_devices_used": self.total_devices_used,
            "total_ips_used": self.total_ips_used,
            "total_targets": self.total_targets,
            "completed_targets": self.completed_targets,
            "target_completion_rate": self.target_completion_rate,
            "active_days": self.active_days,
        }

    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return (self.successful_executions / self.total_executions) * 100

    @property
    def target_completion_rate(self) -> float:
        if self.total_targets == 0:
            return 0.0
        return (self.completed_targets / self.total_targets) * 100


@dataclass
class Project:
    """프로젝트 정의"""
    project_id: str
    name: str
    description: str = ""

    # 타겟 목록
    targets: List[ProjectTarget] = field(default_factory=list)

    # 할당된 리소스
    assigned_personas: List[str] = field(default_factory=list)
    assigned_devices: List[str] = field(default_factory=list)

    # 설정
    daily_quota: int = 10            # 일일 실행 목표
    duration_days: int = 7           # 캠페인 기간
    cooldown_minutes: int = 30       # 동일 타겟 재실행 쿨다운

    # IP 설정
    ip_rotation: bool = True         # IP 로테이션 사용
    require_korea_ip: bool = True    # 한국 IP 필수

    # 상태
    status: ProjectStatus = ProjectStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 실행 기록
    execution_records: List[ExecutionRecord] = field(default_factory=list)

    # 통계 (캐시)
    _stats: Optional[ProjectStats] = field(default=None, repr=False)

    def __post_init__(self):
        if not self.project_id:
            self.project_id = str(uuid.uuid4())[:8]

    def add_target(
        self,
        keyword: str,
        blog_title: str,
        url: Optional[str] = None,
        target_clicks: int = 10
    ) -> ProjectTarget:
        """타겟 추가"""
        target = ProjectTarget(
            target_id=str(uuid.uuid4())[:8],
            keyword=keyword,
            blog_title=blog_title,
            url=url,
            target_clicks=target_clicks
        )
        self.targets.append(target)
        return target

    def add_targets_from_list(self, items: List[Dict[str, Any]]) -> List[ProjectTarget]:
        """리스트에서 타겟 일괄 추가"""
        added = []
        for item in items:
            target = self.add_target(
                keyword=item.get("keyword", ""),
                blog_title=item.get("title", item.get("blog_title", "")),
                url=item.get("url"),
                target_clicks=item.get("target_clicks", 10)
            )
            added.append(target)
        return added

    def assign_persona(self, persona_id: str) -> None:
        """페르소나 할당"""
        if persona_id not in self.assigned_personas:
            self.assigned_personas.append(persona_id)

    def assign_device(self, device_serial: str) -> None:
        """디바이스 할당"""
        if device_serial not in self.assigned_devices:
            self.assigned_devices.append(device_serial)

    def start(self) -> None:
        """프로젝트 시작"""
        self.status = ProjectStatus.ACTIVE
        self.started_at = datetime.now()

    def pause(self) -> None:
        """프로젝트 일시 정지"""
        self.status = ProjectStatus.PAUSED

    def resume(self) -> None:
        """프로젝트 재개"""
        self.status = ProjectStatus.ACTIVE

    def complete(self) -> None:
        """프로젝트 완료"""
        self.status = ProjectStatus.COMPLETED
        self.completed_at = datetime.now()

    def get_next_target(self) -> Optional[ProjectTarget]:
        """다음 실행할 타겟 선택"""
        now = datetime.now()
        cooldown = timedelta(minutes=self.cooldown_minutes)

        # 미완료 타겟 중 쿨다운 지난 것 선택
        candidates = []
        for target in self.targets:
            if target.is_completed:
                continue
            if target.last_executed_at:
                if now - target.last_executed_at < cooldown:
                    continue
            candidates.append(target)

        if not candidates:
            return None

        # 진행률이 낮은 것 우선
        candidates.sort(key=lambda t: t.progress)
        return candidates[0]

    def record_execution(
        self,
        target_id: str,
        persona_id: str,
        success: bool,
        duration_sec: int = 0,
        scroll_depth: float = 0.0,
        interactions: int = 0,
        device_serial: Optional[str] = None,
        ip_address: Optional[str] = None,
        ip_provider: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> ExecutionRecord:
        """실행 기록"""
        record = ExecutionRecord(
            record_id=str(uuid.uuid4())[:8],
            project_id=self.project_id,
            target_id=target_id,
            persona_id=persona_id,
            device_serial=device_serial,
            duration_sec=duration_sec,
            scroll_depth=scroll_depth,
            interactions=interactions,
            success=success,
            error_message=error_message,
            ip_address=ip_address,
            ip_provider=ip_provider
        )
        self.execution_records.append(record)

        # 타겟 통계 업데이트
        for target in self.targets:
            if target.target_id == target_id:
                if success:
                    target.total_clicks += 1
                    target.success_count += 1
                    target.total_dwell_time += duration_sec
                    # 평균 스크롤 깊이 업데이트
                    n = target.success_count
                    target.avg_scroll_depth = (
                        (target.avg_scroll_depth * (n-1) + scroll_depth) / n
                    )
                else:
                    target.fail_count += 1
                target.last_executed_at = datetime.now()
                break

        # 캐시 무효화
        self._stats = None

        return record

    def get_stats(self) -> ProjectStats:
        """프로젝트 통계 계산"""
        if self._stats:
            return self._stats

        stats = ProjectStats(project_id=self.project_id)
        stats.total_targets = len(self.targets)
        stats.completed_targets = sum(1 for t in self.targets if t.is_completed)

        if not self.execution_records:
            self._stats = stats
            return stats

        # 실행 통계
        personas = set()
        devices = set()
        ips = set()
        daily_records: Dict[date, List[ExecutionRecord]] = {}

        for record in self.execution_records:
            stats.total_executions += 1
            if record.success:
                stats.successful_executions += 1
                stats.total_dwell_time += record.duration_sec
            else:
                stats.failed_executions += 1

            personas.add(record.persona_id)
            if record.device_serial:
                devices.add(record.device_serial)
            if record.ip_address:
                ips.add(record.ip_address)

            # 일별 그룹화
            d = record.executed_at.date()
            if d not in daily_records:
                daily_records[d] = []
            daily_records[d].append(record)

        stats.total_personas_used = len(personas)
        stats.total_devices_used = len(devices)
        stats.total_ips_used = len(ips)

        if stats.successful_executions > 0:
            stats.avg_dwell_time = stats.total_dwell_time / stats.successful_executions
            stats.avg_scroll_depth = sum(
                t.avg_scroll_depth for t in self.targets if t.success_count > 0
            ) / max(1, sum(1 for t in self.targets if t.success_count > 0))

        # 일별 통계
        for d, records in sorted(daily_records.items()):
            daily = DailyStats(date=d, project_id=self.project_id)
            daily_personas = set()
            daily_devices = set()
            daily_ips = set()

            for r in records:
                daily.total_executions += 1
                if r.success:
                    daily.successful_executions += 1
                    daily.total_dwell_time += r.duration_sec
                else:
                    daily.failed_executions += 1

                daily_personas.add(r.persona_id)
                if r.device_serial:
                    daily_devices.add(r.device_serial)
                if r.ip_address:
                    daily_ips.add(r.ip_address)

            daily.unique_personas = len(daily_personas)
            daily.unique_devices = len(daily_devices)
            daily.unique_ips = len(daily_ips)

            if daily.successful_executions > 0:
                daily.avg_dwell_time = daily.total_dwell_time / daily.successful_executions

            stats.daily_stats.append(daily)

        stats.active_days = len(daily_records)

        if self.execution_records:
            stats.first_execution = min(r.executed_at for r in self.execution_records)
            stats.last_execution = max(r.executed_at for r in self.execution_records)

        self._stats = stats
        return stats

    @property
    def progress(self) -> float:
        """전체 진행률"""
        if not self.targets:
            return 0.0
        return sum(t.progress for t in self.targets) / len(self.targets)

    @property
    def is_completed(self) -> bool:
        """모든 타겟 완료 여부"""
        return all(t.is_completed for t in self.targets)

    @property
    def today_executions(self) -> int:
        """오늘 실행 횟수"""
        today = date.today()
        return sum(
            1 for r in self.execution_records
            if r.executed_at.date() == today
        )

    @property
    def remaining_today(self) -> int:
        """오늘 남은 실행 횟수"""
        return max(0, self.daily_quota - self.today_executions)

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "targets": [t.to_dict() for t in self.targets],
            "assigned_personas": self.assigned_personas,
            "assigned_devices": self.assigned_devices,
            "daily_quota": self.daily_quota,
            "duration_days": self.duration_days,
            "progress": self.progress,
            "today_executions": self.today_executions,
            "remaining_today": self.remaining_today,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
        }

    def to_json(self) -> str:
        """JSON으로 변환"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
