"""
Campaign Orchestrator

캠페인 오케스트레이터:
- 모든 모듈 통합 관리
- 캠페인 라이프사이클 관리
- 실행 조율
"""

import logging
import asyncio
import json
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime
from enum import Enum

from .config import OrchestratorConfig, ExecutionMode
from .scheduler import CampaignScheduler, ScheduleEntry, TaskPriority
from .executor import (
    TaskExecutor,
    ExecutionContext,
    ExecutionResult,
    create_executor_with_defaults
)

# 순환 참조 방지
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..core.events import EventBus
    from ..project_manager import ProjectManager, Project
    from ..persona_generator import PersonaGenerator, GeneratedPersona
    from ..storyline_generator import StorylineGenerator
    from ..ip_manager import IPManager

logger = logging.getLogger(__name__)


class CampaignStatus(Enum):
    """캠페인 상태"""
    CREATED = "created"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CampaignState:
    """캠페인 상태"""
    campaign_id: str
    project_id: str
    status: CampaignStatus = CampaignStatus.CREATED

    # 진행 상황
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    success_rate: float = 0.0

    # 리소스
    assigned_personas: List[str] = field(default_factory=list)
    assigned_devices: List[str] = field(default_factory=list)
    current_ips: Dict[str, str] = field(default_factory=dict)

    # 타임스탬프
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 오류
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "project_id": self.project_id,
            "status": self.status.value,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": self.success_rate,
            "assigned_personas": self.assigned_personas,
            "assigned_devices": self.assigned_devices,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class CampaignOrchestrator:
    """
    캠페인 오케스트레이터

    모든 모듈을 통합하여 캠페인을 실행합니다.

    Usage:
        orchestrator = CampaignOrchestrator()

        # 모듈 등록
        await orchestrator.register_modules(
            project_manager=pm,
            persona_generator=pg,
            storyline_generator=sg,
            ip_manager=im
        )

        # 캠페인 실행
        campaign_id = await orchestrator.execute_campaign("project_001")

        # 상태 확인
        state = orchestrator.get_campaign_state(campaign_id)
    """

    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        event_bus: Optional['EventBus'] = None
    ):
        self.config = config or OrchestratorConfig.default()
        self.event_bus = event_bus

        # 스케줄러 & 실행기
        self.scheduler = CampaignScheduler(
            daily_quota=self.config.schedule.daily_quota,
            hourly_quota=self.config.schedule.max_per_hour,
            active_hours=self.config.schedule.active_hours,
            cooldown_sec=self.config.execution.cooldown_sec
        )
        self.executor = create_executor_with_defaults(
            timeout_sec=self.config.execution.task_timeout_sec,
            max_concurrent=self.config.execution.max_concurrent
        )

        # 모듈 참조
        self._project_manager: Optional['ProjectManager'] = None
        self._persona_generator: Optional['PersonaGenerator'] = None
        self._storyline_generator: Optional['StorylineGenerator'] = None
        self._ip_manager: Optional['IPManager'] = None

        # 캠페인 상태
        self._campaigns: Dict[str, CampaignState] = {}
        self._running_campaign: Optional[str] = None
        self._stop_requested = False

        # 콜백
        self._on_task_complete: List[Callable[[ExecutionResult], Awaitable[None]]] = []
        self._on_campaign_complete: List[Callable[[CampaignState], Awaitable[None]]] = []

        # 상태 파일
        self._state_file = Path(self.config.state_file)
        self._state_file.parent.mkdir(parents=True, exist_ok=True)

    # ==================== 모듈 등록 ====================

    async def register_modules(
        self,
        project_manager: Optional['ProjectManager'] = None,
        persona_generator: Optional['PersonaGenerator'] = None,
        storyline_generator: Optional['StorylineGenerator'] = None,
        ip_manager: Optional['IPManager'] = None
    ) -> None:
        """모듈 등록"""
        if project_manager:
            self._project_manager = project_manager
            logger.info("ProjectManager registered")

        if persona_generator:
            self._persona_generator = persona_generator
            # 연동 설정
            if project_manager:
                persona_generator.set_project_manager(project_manager)
            if storyline_generator:
                persona_generator.set_storyline_generator(storyline_generator)
            if ip_manager:
                persona_generator.set_ip_manager(ip_manager)
            logger.info("PersonaGenerator registered")

        if storyline_generator:
            self._storyline_generator = storyline_generator
            logger.info("StorylineGenerator registered")

        if ip_manager:
            self._ip_manager = ip_manager
            logger.info("IPManager registered")

    def register_task_handler(
        self,
        task_type: str,
        handler: Callable[[ExecutionContext], Awaitable[ExecutionResult]]
    ) -> None:
        """커스텀 작업 핸들러 등록"""
        self.executor.register_handler(task_type, handler)

    def on_task_complete(
        self,
        callback: Callable[[ExecutionResult], Awaitable[None]]
    ) -> None:
        """작업 완료 콜백 등록"""
        self._on_task_complete.append(callback)

    def on_campaign_complete(
        self,
        callback: Callable[[CampaignState], Awaitable[None]]
    ) -> None:
        """캠페인 완료 콜백 등록"""
        self._on_campaign_complete.append(callback)

    # ==================== 캠페인 실행 ====================

    async def execute_campaign(
        self,
        project_id: str,
        personas: Optional[List['GeneratedPersona']] = None,
        device_serials: Optional[List[str]] = None
    ) -> str:
        """
        캠페인 실행

        Args:
            project_id: 프로젝트 ID
            personas: 사용할 페르소나 목록
            device_serials: 사용할 디바이스 시리얼 목록

        Returns:
            str: 캠페인 ID
        """
        if not self._project_manager:
            raise RuntimeError("ProjectManager not registered")

        # 프로젝트 조회
        project = self._project_manager.get_project(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        # 캠페인 상태 생성
        campaign_id = f"camp_{uuid.uuid4().hex[:8]}"
        state = CampaignState(
            campaign_id=campaign_id,
            project_id=project_id,
            status=CampaignStatus.INITIALIZING
        )
        self._campaigns[campaign_id] = state

        try:
            # 1. 리소스 할당
            await self._allocate_resources(state, project, personas, device_serials)

            # 2. 작업 스케줄링
            await self._schedule_tasks(state, project)

            # 3. 캠페인 시작
            state.status = CampaignStatus.RUNNING
            state.started_at = datetime.now()
            self._running_campaign = campaign_id

            # 프로젝트 시작
            self._project_manager.start_project(project_id)

            # 4. 실행 루프
            await self._run_campaign_loop(state, project)

        except Exception as e:
            state.status = CampaignStatus.FAILED
            state.errors.append(str(e))
            logger.error(f"Campaign failed: {e}")

        finally:
            # 상태 저장
            await self._save_state()

            # 콜백 실행
            for callback in self._on_campaign_complete:
                await callback(state)

        return campaign_id

    async def _allocate_resources(
        self,
        state: CampaignState,
        project: 'Project',
        personas: Optional[List['GeneratedPersona']],
        devices: Optional[List[str]]
    ) -> None:
        """리소스 할당"""
        # 페르소나 할당
        if personas:
            state.assigned_personas = [p.persona_id for p in personas]
        elif project.assigned_personas:
            state.assigned_personas = project.assigned_personas[:self.config.resource.max_personas]
        else:
            logger.warning("No personas assigned")

        # 디바이스 할당
        if devices:
            state.assigned_devices = devices
        elif project.assigned_devices:
            state.assigned_devices = project.assigned_devices[:self.config.resource.max_devices]
        else:
            logger.warning("No devices assigned")

        # IP 할당
        if self._ip_manager and self.config.auto_assign_ip:
            for persona_id in state.assigned_personas:
                ip_info = await self._ip_manager.get_next_ip(persona_id)
                if ip_info:
                    state.current_ips[persona_id] = ip_info.get("ip", "unknown")

        logger.info(
            f"Resources allocated: "
            f"{len(state.assigned_personas)} personas, "
            f"{len(state.assigned_devices)} devices"
        )

    async def _schedule_tasks(
        self,
        state: CampaignState,
        project: 'Project'
    ) -> None:
        """작업 스케줄링"""
        task_count = 0
        interval = self.config.execution.cooldown_sec

        for target in project.targets:
            remaining = target.target_clicks - target.total_clicks

            for i in range(remaining):
                # 페르소나 순환 선택
                persona_idx = i % len(state.assigned_personas) if state.assigned_personas else 0
                persona_id = state.assigned_personas[persona_idx] if state.assigned_personas else None

                # 디바이스 순환 선택
                device_idx = i % len(state.assigned_devices) if state.assigned_devices else 0
                device_serial = state.assigned_devices[device_idx] if state.assigned_devices else None

                await self.scheduler.schedule_task(
                    task_type="engagement",
                    payload={
                        "project_id": project.project_id,
                        "target_id": target.target_id,
                        "keyword": target.keyword,
                        "url": target.url,
                        "blog_title": target.blog_title,
                        "persona_id": persona_id,
                        "device_serial": device_serial
                    },
                    priority=TaskPriority.NORMAL,
                    delay_sec=task_count * interval
                )
                task_count += 1

        state.total_tasks = task_count
        logger.info(f"Scheduled {task_count} tasks for campaign {state.campaign_id}")

    async def _run_campaign_loop(
        self,
        state: CampaignState,
        project: 'Project'
    ) -> None:
        """캠페인 실행 루프"""
        while not self._stop_requested:
            # 다음 작업 가져오기
            task = await self.scheduler.get_next_task()
            if not task:
                # 대기 중인 작업이 없으면 종료
                pending = self.scheduler.get_pending_tasks()
                if not pending:
                    break
                await asyncio.sleep(5)
                continue

            # 실행 컨텍스트 생성
            context = await self._create_execution_context(task, state)

            # 작업 실행
            result = await self.executor.execute(context)

            # 결과 처리
            await self._handle_execution_result(state, project, task, result)

            # 완료 체크
            if state.completed_tasks + state.failed_tasks >= state.total_tasks:
                break

        # 캠페인 완료
        state.status = CampaignStatus.COMPLETED
        state.completed_at = datetime.now()

        # 프로젝트 완료 확인
        project = self._project_manager.get_project(project.project_id)
        if project and project.is_completed:
            self._project_manager.complete_project(project.project_id)

        logger.info(f"Campaign completed: {state.campaign_id}")

    async def _create_execution_context(
        self,
        task: ScheduleEntry,
        state: CampaignState
    ) -> ExecutionContext:
        """실행 컨텍스트 생성"""
        payload = task.payload
        persona_id = payload.get("persona_id")

        # IP 확인/갱신
        ip_address = None
        ip_provider = None
        if self._ip_manager and persona_id:
            if self.config.resource.ip_rotation:
                ip_info = await self._ip_manager.get_next_ip(persona_id)
            else:
                ip_info = {"ip": state.current_ips.get(persona_id)}

            if ip_info:
                ip_address = ip_info.get("ip")
                ip_provider = ip_info.get("provider")

        # 스토리라인 생성
        storyline = None
        if self._storyline_generator and self.config.auto_generate_storyline:
            try:
                storyline = await self._storyline_generator.generate(
                    keyword=payload.get("keyword", ""),
                    persona_archetype=payload.get("archetype", "casual")
                )
            except Exception as e:
                logger.warning(f"Storyline generation failed: {e}")

        return ExecutionContext(
            execution_id=f"exec_{uuid.uuid4().hex[:8]}",
            task_id=task.task_id,
            task_type=task.task_type,
            project_id=payload.get("project_id"),
            target_id=payload.get("target_id"),
            keyword=payload.get("keyword"),
            url=payload.get("url"),
            persona_id=persona_id,
            device_serial=payload.get("device_serial"),
            ip_address=ip_address,
            ip_provider=ip_provider,
            storyline=storyline
        )

    async def _handle_execution_result(
        self,
        state: CampaignState,
        project: 'Project',
        task: ScheduleEntry,
        result: ExecutionResult
    ) -> None:
        """실행 결과 처리"""
        # 스케줄러 완료 처리
        await self.scheduler.complete_task(
            task.task_id,
            success=result.success,
            error=result.errors[0] if result.errors else None
        )

        # 상태 업데이트
        if result.success:
            state.completed_tasks += 1
        else:
            state.failed_tasks += 1

            # 재시도
            if task.retry_count < self.config.execution.retry_count:
                await self.scheduler.retry_task(task.task_id)

        # 성공률 계산
        total = state.completed_tasks + state.failed_tasks
        state.success_rate = (state.completed_tasks / total * 100) if total > 0 else 0

        # 프로젝트 매니저에 기록
        if result.success and self._project_manager:
            self._project_manager.record_execution(
                project_id=project.project_id,
                target_id=result.context.target_id or "",
                persona_id=result.context.persona_id or "",
                success=True,
                duration_sec=result.context.duration_sec,
                scroll_depth=result.context.scroll_depth,
                interactions=result.context.interactions,
                device_serial=result.context.device_serial,
                ip_address=result.context.ip_address,
                ip_provider=result.context.ip_provider
            )

        # 콜백 실행
        for callback in self._on_task_complete:
            await callback(result)

        # 이벤트 발행
        if self.event_bus and self.config.publish_events:
            await self._publish_execution_event(result)

    async def _publish_execution_event(self, result: ExecutionResult) -> None:
        """실행 이벤트 발행"""
        if not self.event_bus:
            return

        try:
            from ..core.events import Event, EventType
            event = Event(
                event_type=EventType.EXECUTION_COMPLETED if result.success else EventType.EXECUTION_FAILED,
                source="orchestrator",
                data={
                    "execution_id": result.context.execution_id,
                    "task_type": result.context.task_type,
                    "success": result.success,
                    "duration_ms": result.duration_ms
                }
            )
            await self.event_bus.publish(event)
        except ImportError:
            pass

    # ==================== 캠페인 제어 ====================

    async def pause_campaign(self, campaign_id: str) -> bool:
        """캠페인 일시 정지"""
        if campaign_id not in self._campaigns:
            return False

        state = self._campaigns[campaign_id]
        state.status = CampaignStatus.PAUSED
        self._stop_requested = True
        return True

    async def resume_campaign(self, campaign_id: str) -> bool:
        """캠페인 재개"""
        if campaign_id not in self._campaigns:
            return False

        state = self._campaigns[campaign_id]
        if state.status != CampaignStatus.PAUSED:
            return False

        state.status = CampaignStatus.RUNNING
        self._stop_requested = False

        # 재실행
        project = self._project_manager.get_project(state.project_id)
        if project:
            asyncio.create_task(self._run_campaign_loop(state, project))

        return True

    async def stop_campaign(self, campaign_id: str) -> bool:
        """캠페인 중지"""
        if campaign_id not in self._campaigns:
            return False

        state = self._campaigns[campaign_id]
        state.status = CampaignStatus.COMPLETED
        state.completed_at = datetime.now()
        self._stop_requested = True

        await self.scheduler.cancel_all()
        return True

    # ==================== 상태 조회 ====================

    def get_campaign_state(self, campaign_id: str) -> Optional[CampaignState]:
        """캠페인 상태 조회"""
        return self._campaigns.get(campaign_id)

    def list_campaigns(
        self,
        status: Optional[CampaignStatus] = None
    ) -> List[CampaignState]:
        """캠페인 목록 조회"""
        campaigns = list(self._campaigns.values())
        if status:
            campaigns = [c for c in campaigns if c.status == status]
        return sorted(campaigns, key=lambda c: c.created_at, reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        """전체 통계"""
        return {
            "campaigns": {
                "total": len(self._campaigns),
                "running": len([c for c in self._campaigns.values() if c.status == CampaignStatus.RUNNING]),
                "completed": len([c for c in self._campaigns.values() if c.status == CampaignStatus.COMPLETED]),
            },
            "scheduler": self.scheduler.get_stats(),
            "executor": self.executor.get_stats()
        }

    # ==================== 상태 저장/로드 ====================

    async def _save_state(self) -> None:
        """상태 저장"""
        if not self.config.persist_state:
            return

        data = {
            "saved_at": datetime.now().isoformat(),
            "campaigns": {
                cid: state.to_dict()
                for cid, state in self._campaigns.items()
            }
        }

        with open(self._state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def load_state(self) -> None:
        """상태 로드"""
        if not self._state_file.exists():
            return

        try:
            with open(self._state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for cid, state_data in data.get("campaigns", {}).items():
                state = CampaignState(
                    campaign_id=state_data["campaign_id"],
                    project_id=state_data["project_id"],
                    status=CampaignStatus(state_data["status"]),
                    total_tasks=state_data["total_tasks"],
                    completed_tasks=state_data["completed_tasks"],
                    failed_tasks=state_data["failed_tasks"],
                    success_rate=state_data["success_rate"],
                    assigned_personas=state_data["assigned_personas"],
                    assigned_devices=state_data["assigned_devices"]
                )
                self._campaigns[cid] = state

            logger.info(f"Loaded {len(self._campaigns)} campaigns from state file")

        except Exception as e:
            logger.error(f"Failed to load state: {e}")

    # ==================== 유틸리티 ====================

    async def quick_execute(
        self,
        project_id: str,
        count: int = 5
    ) -> str:
        """빠른 테스트 실행"""
        # 테스트용 설정으로 실행
        original_quota = self.scheduler.quota.daily_limit
        self.scheduler.quota.daily_limit = count

        campaign_id = await self.execute_campaign(project_id)

        self.scheduler.quota.daily_limit = original_quota
        return campaign_id
