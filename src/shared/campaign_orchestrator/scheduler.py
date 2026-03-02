"""
Campaign Scheduler

캠페인 스케줄러:
- 작업 스케줄링
- 쿨다운 관리
- 할당량 추적
"""

import logging
import asyncio
import heapq
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable, Awaitable
from datetime import datetime, timedelta
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """작업 우선순위"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class TaskStatus(Enum):
    """작업 상태"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(order=True)
class ScheduleEntry:
    """스케줄 항목"""
    scheduled_at: datetime
    priority: int = field(compare=True)
    task_id: str = field(compare=False)
    task_type: str = field(compare=False)
    payload: Dict[str, Any] = field(compare=False, default_factory=dict)
    status: TaskStatus = field(compare=False, default=TaskStatus.PENDING)
    retry_count: int = field(compare=False, default=0)
    created_at: datetime = field(compare=False, default_factory=datetime.now)
    completed_at: Optional[datetime] = field(compare=False, default=None)
    error: Optional[str] = field(compare=False, default=None)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "priority": self.priority,
            "scheduled_at": self.scheduled_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count,
            "error": self.error
        }


@dataclass
class QuotaTracker:
    """할당량 추적기"""
    daily_limit: int = 50
    hourly_limit: int = 10

    _daily_count: int = 0
    _hourly_count: int = 0
    _last_daily_reset: datetime = field(default_factory=datetime.now)
    _last_hourly_reset: datetime = field(default_factory=datetime.now)

    def can_execute(self) -> bool:
        """실행 가능 여부"""
        self._check_reset()
        return (
            self._daily_count < self.daily_limit and
            self._hourly_count < self.hourly_limit
        )

    def increment(self) -> None:
        """실행 카운트 증가"""
        self._check_reset()
        self._daily_count += 1
        self._hourly_count += 1

    def _check_reset(self) -> None:
        """리셋 확인"""
        now = datetime.now()

        # 일간 리셋
        if now.date() > self._last_daily_reset.date():
            self._daily_count = 0
            self._last_daily_reset = now

        # 시간 리셋
        if now.hour != self._last_hourly_reset.hour:
            self._hourly_count = 0
            self._last_hourly_reset = now

    @property
    def remaining_daily(self) -> int:
        self._check_reset()
        return max(0, self.daily_limit - self._daily_count)

    @property
    def remaining_hourly(self) -> int:
        self._check_reset()
        return max(0, self.hourly_limit - self._hourly_count)


class CampaignScheduler:
    """
    캠페인 스케줄러

    Usage:
        scheduler = CampaignScheduler()

        # 작업 추가
        await scheduler.schedule_task(
            task_type="engagement",
            payload={"target_id": "t_001"},
            priority=TaskPriority.NORMAL
        )

        # 다음 작업 가져오기
        task = await scheduler.get_next_task()

        # 작업 완료/실패 처리
        await scheduler.complete_task(task.task_id, success=True)
    """

    def __init__(
        self,
        daily_quota: int = 50,
        hourly_quota: int = 10,
        active_hours: Optional[List[int]] = None,
        cooldown_sec: int = 60
    ):
        self.active_hours = active_hours or list(range(9, 22))
        self.cooldown_sec = cooldown_sec

        # 할당량 추적
        self.quota = QuotaTracker(
            daily_limit=daily_quota,
            hourly_limit=hourly_quota
        )

        # 스케줄 큐 (우선순위 큐)
        self._queue: List[ScheduleEntry] = []
        self._tasks: Dict[str, ScheduleEntry] = {}

        # 쿨다운 추적 (페르소나/디바이스별)
        self._cooldowns: Dict[str, datetime] = {}

        # 실행 중인 작업
        self._running: Dict[str, ScheduleEntry] = {}

        # 락
        self._lock = asyncio.Lock()

        # 통계
        self._stats = {
            "total_scheduled": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_cancelled": 0
        }

    async def schedule_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        scheduled_at: Optional[datetime] = None,
        delay_sec: int = 0
    ) -> ScheduleEntry:
        """
        작업 스케줄링

        Args:
            task_type: 작업 유형
            payload: 작업 데이터
            priority: 우선순위
            scheduled_at: 예약 시간
            delay_sec: 지연 시간 (초)

        Returns:
            ScheduleEntry: 스케줄 항목
        """
        async with self._lock:
            task_id = f"task_{uuid.uuid4().hex[:8]}"

            # 실행 시간 결정
            if scheduled_at is None:
                scheduled_at = datetime.now() + timedelta(seconds=delay_sec)

            entry = ScheduleEntry(
                task_id=task_id,
                task_type=task_type,
                payload=payload,
                priority=priority.value,
                scheduled_at=scheduled_at,
                status=TaskStatus.SCHEDULED
            )

            heapq.heappush(self._queue, entry)
            self._tasks[task_id] = entry
            self._stats["total_scheduled"] += 1

            logger.debug(f"Task scheduled: {task_id} ({task_type})")
            return entry

    async def schedule_batch(
        self,
        tasks: List[Dict[str, Any]],
        interval_sec: int = 60
    ) -> List[ScheduleEntry]:
        """작업 일괄 스케줄링"""
        entries = []
        delay = 0

        for task in tasks:
            entry = await self.schedule_task(
                task_type=task.get("type", "engagement"),
                payload=task.get("payload", {}),
                priority=TaskPriority(task.get("priority", 2)),
                delay_sec=delay
            )
            entries.append(entry)
            delay += interval_sec

        return entries

    async def get_next_task(self) -> Optional[ScheduleEntry]:
        """다음 실행 가능한 작업 가져오기"""
        async with self._lock:
            # 할당량 확인
            if not self.quota.can_execute():
                logger.debug("Quota exhausted")
                return None

            # 활성 시간 확인
            if not self._is_active_hour():
                logger.debug("Outside active hours")
                return None

            # 큐에서 실행 가능한 작업 찾기
            now = datetime.now()
            while self._queue:
                entry = heapq.heappop(self._queue)

                # 취소된 작업 건너뛰기
                if entry.status == TaskStatus.CANCELLED:
                    continue

                # 예약 시간 확인
                if entry.scheduled_at > now:
                    heapq.heappush(self._queue, entry)
                    return None

                # 쿨다운 확인
                persona_id = entry.payload.get("persona_id")
                if persona_id and not self._check_cooldown(persona_id):
                    # 쿨다운 중이면 재스케줄
                    entry.scheduled_at = self._cooldowns[persona_id]
                    heapq.heappush(self._queue, entry)
                    continue

                # 실행 상태로 변경
                entry.status = TaskStatus.RUNNING
                self._running[entry.task_id] = entry
                self.quota.increment()

                # 쿨다운 설정
                if persona_id:
                    self._set_cooldown(persona_id)

                logger.debug(f"Task dispatched: {entry.task_id}")
                return entry

            return None

    async def complete_task(
        self,
        task_id: str,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """작업 완료 처리"""
        async with self._lock:
            if task_id not in self._running:
                logger.warning(f"Task not found in running: {task_id}")
                return

            entry = self._running.pop(task_id)
            entry.completed_at = datetime.now()

            if success:
                entry.status = TaskStatus.COMPLETED
                self._stats["total_completed"] += 1
            else:
                entry.status = TaskStatus.FAILED
                entry.error = error
                self._stats["total_failed"] += 1

            logger.debug(f"Task completed: {task_id} (success={success})")

    async def retry_task(
        self,
        task_id: str,
        max_retries: int = 3
    ) -> bool:
        """작업 재시도"""
        async with self._lock:
            if task_id not in self._tasks:
                return False

            entry = self._tasks[task_id]

            if entry.retry_count >= max_retries:
                logger.warning(f"Max retries exceeded: {task_id}")
                return False

            # 재스케줄
            entry.retry_count += 1
            entry.status = TaskStatus.SCHEDULED
            entry.scheduled_at = datetime.now() + timedelta(
                seconds=30 * entry.retry_count  # 점진적 지연
            )

            if task_id in self._running:
                del self._running[task_id]

            heapq.heappush(self._queue, entry)
            logger.debug(f"Task rescheduled for retry: {task_id}")
            return True

    async def cancel_task(self, task_id: str) -> bool:
        """작업 취소"""
        async with self._lock:
            if task_id not in self._tasks:
                return False

            entry = self._tasks[task_id]
            entry.status = TaskStatus.CANCELLED
            self._stats["total_cancelled"] += 1

            if task_id in self._running:
                del self._running[task_id]

            logger.debug(f"Task cancelled: {task_id}")
            return True

    async def cancel_all(self) -> int:
        """모든 작업 취소"""
        async with self._lock:
            count = 0
            for entry in self._queue:
                if entry.status == TaskStatus.SCHEDULED:
                    entry.status = TaskStatus.CANCELLED
                    count += 1
            self._stats["total_cancelled"] += count
            return count

    def _check_cooldown(self, identifier: str) -> bool:
        """쿨다운 확인"""
        if identifier not in self._cooldowns:
            return True
        return datetime.now() >= self._cooldowns[identifier]

    def _set_cooldown(self, identifier: str) -> None:
        """쿨다운 설정"""
        self._cooldowns[identifier] = datetime.now() + timedelta(
            seconds=self.cooldown_sec
        )

    def _is_active_hour(self) -> bool:
        """활성 시간 확인"""
        return datetime.now().hour in self.active_hours

    def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        return {
            **self._stats,
            "queue_size": len(self._queue),
            "running_count": len(self._running),
            "remaining_daily": self.quota.remaining_daily,
            "remaining_hourly": self.quota.remaining_hourly
        }

    def get_pending_tasks(self, limit: int = 10) -> List[ScheduleEntry]:
        """대기 중인 작업 목록"""
        return sorted(
            [e for e in self._queue if e.status == TaskStatus.SCHEDULED],
            key=lambda e: (e.scheduled_at, e.priority)
        )[:limit]

    async def wait_for_next(self) -> Optional[ScheduleEntry]:
        """다음 작업까지 대기"""
        while True:
            task = await self.get_next_task()
            if task:
                return task

            # 큐가 비어있으면 종료
            if not self._queue:
                return None

            # 다음 작업까지 대기
            next_entry = min(self._queue, key=lambda e: e.scheduled_at)
            wait_time = (next_entry.scheduled_at - datetime.now()).total_seconds()

            if wait_time > 0:
                await asyncio.sleep(min(wait_time, 10))  # 최대 10초
            else:
                await asyncio.sleep(1)
