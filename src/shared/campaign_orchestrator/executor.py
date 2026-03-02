"""
Task Executor

작업 실행기:
- 개별 작업 실행
- 실행 컨텍스트 관리
- 결과 수집
"""

import logging
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, Awaitable, List
from datetime import datetime
from enum import Enum
import traceback

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """실행 상태"""
    PENDING = "pending"
    PREPARING = "preparing"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ExecutionContext:
    """실행 컨텍스트"""
    execution_id: str
    task_id: str
    task_type: str

    # 리소스
    persona_id: Optional[str] = None
    device_serial: Optional[str] = None
    ip_address: Optional[str] = None
    ip_provider: Optional[str] = None

    # 타겟
    project_id: Optional[str] = None
    target_id: Optional[str] = None
    keyword: Optional[str] = None
    url: Optional[str] = None

    # 실행 파라미터
    storyline: Optional[Dict] = None
    behavior_profile: Optional[Dict] = None

    # 상태
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 결과
    success: bool = False
    duration_sec: int = 0
    scroll_depth: float = 0.0
    interactions: int = 0
    error: Optional[str] = None

    # 메타데이터
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "persona_id": self.persona_id,
            "device_serial": self.device_serial,
            "ip_address": self.ip_address,
            "project_id": self.project_id,
            "target_id": self.target_id,
            "keyword": self.keyword,
            "status": self.status.value,
            "success": self.success,
            "duration_sec": self.duration_sec,
            "scroll_depth": self.scroll_depth,
            "interactions": self.interactions,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class ExecutionResult:
    """실행 결과"""
    success: bool
    context: ExecutionContext
    duration_ms: int = 0
    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "duration_ms": self.duration_ms,
            "context": self.context.to_dict(),
            "data": self.data,
            "errors": self.errors
        }


# 작업 핸들러 타입
TaskHandler = Callable[[ExecutionContext], Awaitable[ExecutionResult]]


class TaskExecutor:
    """
    작업 실행기

    Usage:
        executor = TaskExecutor()

        # 핸들러 등록
        executor.register_handler("engagement", engagement_handler)
        executor.register_handler("search", search_handler)

        # 실행
        result = await executor.execute(context)
    """

    def __init__(
        self,
        timeout_sec: int = 300,
        max_concurrent: int = 3
    ):
        self.timeout_sec = timeout_sec
        self.max_concurrent = max_concurrent

        # 핸들러 레지스트리
        self._handlers: Dict[str, TaskHandler] = {}

        # 실행 중인 작업
        self._running: Dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # 훅
        self._pre_hooks: List[Callable[[ExecutionContext], Awaitable[None]]] = []
        self._post_hooks: List[Callable[[ExecutionResult], Awaitable[None]]] = []

        # 통계
        self._stats = {
            "total_executions": 0,
            "successful": 0,
            "failed": 0,
            "timeouts": 0,
            "avg_duration_ms": 0
        }
        self._duration_sum = 0

    def register_handler(
        self,
        task_type: str,
        handler: TaskHandler
    ) -> None:
        """작업 핸들러 등록"""
        self._handlers[task_type] = handler
        logger.debug(f"Handler registered: {task_type}")

    def add_pre_hook(
        self,
        hook: Callable[[ExecutionContext], Awaitable[None]]
    ) -> None:
        """사전 훅 추가"""
        self._pre_hooks.append(hook)

    def add_post_hook(
        self,
        hook: Callable[[ExecutionResult], Awaitable[None]]
    ) -> None:
        """사후 훅 추가"""
        self._post_hooks.append(hook)

    async def execute(
        self,
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        작업 실행

        Args:
            context: 실행 컨텍스트

        Returns:
            ExecutionResult: 실행 결과
        """
        start_time = datetime.now()
        result = ExecutionResult(
            success=False,
            context=context
        )

        async with self._semaphore:
            try:
                # 핸들러 확인
                handler = self._handlers.get(context.task_type)
                if not handler:
                    result.errors.append(f"No handler for task type: {context.task_type}")
                    return result

                # 사전 훅 실행
                context.status = ExecutionStatus.PREPARING
                context.started_at = datetime.now()

                for hook in self._pre_hooks:
                    await hook(context)

                # 작업 실행
                context.status = ExecutionStatus.EXECUTING

                try:
                    result = await asyncio.wait_for(
                        handler(context),
                        timeout=self.timeout_sec
                    )
                except asyncio.TimeoutError:
                    context.status = ExecutionStatus.TIMEOUT
                    result.errors.append("Execution timeout")
                    self._stats["timeouts"] += 1
                    return result

                # 상태 업데이트
                if result.success:
                    context.status = ExecutionStatus.COMPLETED
                    context.success = True
                    self._stats["successful"] += 1
                else:
                    context.status = ExecutionStatus.FAILED
                    self._stats["failed"] += 1

            except Exception as e:
                context.status = ExecutionStatus.FAILED
                context.error = str(e)
                result.errors.append(str(e))
                result.errors.append(traceback.format_exc())
                self._stats["failed"] += 1
                logger.error(f"Execution failed: {e}")

            finally:
                context.completed_at = datetime.now()
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                result.duration_ms = duration_ms
                context.duration_sec = duration_ms // 1000

                # 사후 훅 실행
                for hook in self._post_hooks:
                    try:
                        await hook(result)
                    except Exception as e:
                        logger.error(f"Post hook error: {e}")

                # 통계 업데이트
                self._stats["total_executions"] += 1
                self._duration_sum += duration_ms
                self._stats["avg_duration_ms"] = self._duration_sum // self._stats["total_executions"]

        return result

    async def execute_batch(
        self,
        contexts: List[ExecutionContext],
        sequential: bool = False
    ) -> List[ExecutionResult]:
        """작업 일괄 실행"""
        if sequential:
            results = []
            for ctx in contexts:
                result = await self.execute(ctx)
                results.append(result)
            return results

        # 병렬 실행
        tasks = [self.execute(ctx) for ctx in contexts]
        return await asyncio.gather(*tasks)

    def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        return {
            **self._stats,
            "running_count": len(self._running),
            "available_slots": self._semaphore._value
        }


# ==================== 기본 핸들러 ====================

async def engagement_handler(context: ExecutionContext) -> ExecutionResult:
    """
    인게이지먼트 핸들러 (기본 구현)

    실제 구현에서는 이 핸들러를 오버라이드하여 사용
    """
    result = ExecutionResult(success=False, context=context)

    # 필수 필드 확인
    if not context.keyword:
        result.errors.append("Missing keyword")
        return result

    if not context.persona_id:
        result.errors.append("Missing persona_id")
        return result

    # 시뮬레이션 (실제 구현에서 대체)
    logger.info(f"[SIM] Engagement: {context.keyword} by {context.persona_id}")
    await asyncio.sleep(0.1)

    # 결과 설정
    context.scroll_depth = 0.85
    context.interactions = 3
    result.success = True
    result.data = {
        "keyword": context.keyword,
        "simulated": True
    }

    return result


async def search_handler(context: ExecutionContext) -> ExecutionResult:
    """검색 핸들러 (기본 구현)"""
    result = ExecutionResult(success=False, context=context)

    if not context.keyword:
        result.errors.append("Missing keyword")
        return result

    # 시뮬레이션
    logger.info(f"[SIM] Search: {context.keyword}")
    await asyncio.sleep(0.05)

    result.success = True
    result.data = {
        "keyword": context.keyword,
        "results_count": 10
    }

    return result


async def click_handler(context: ExecutionContext) -> ExecutionResult:
    """클릭 핸들러 (기본 구현)"""
    result = ExecutionResult(success=False, context=context)

    if not context.url:
        result.errors.append("Missing URL")
        return result

    # 시뮬레이션
    logger.info(f"[SIM] Click: {context.url}")
    await asyncio.sleep(0.1)

    result.success = True
    result.data = {
        "url": context.url,
        "loaded": True
    }

    return result


async def dwell_handler(context: ExecutionContext) -> ExecutionResult:
    """체류 핸들러 (기본 구현)"""
    result = ExecutionResult(success=False, context=context)

    duration = context.metadata.get("dwell_duration", 30)

    # 시뮬레이션
    logger.info(f"[SIM] Dwell: {duration}s")
    await asyncio.sleep(0.1)

    context.duration_sec = duration
    context.scroll_depth = 0.75
    result.success = True
    result.data = {
        "duration": duration,
        "scroll_depth": 0.75
    }

    return result


# 기본 핸들러 맵
DEFAULT_HANDLERS = {
    "engagement": engagement_handler,
    "search": search_handler,
    "click": click_handler,
    "dwell": dwell_handler
}


def create_executor_with_defaults(
    timeout_sec: int = 300,
    max_concurrent: int = 3
) -> TaskExecutor:
    """기본 핸들러가 등록된 실행기 생성"""
    executor = TaskExecutor(
        timeout_sec=timeout_sec,
        max_concurrent=max_concurrent
    )

    for task_type, handler in DEFAULT_HANDLERS.items():
        executor.register_handler(task_type, handler)

    return executor
