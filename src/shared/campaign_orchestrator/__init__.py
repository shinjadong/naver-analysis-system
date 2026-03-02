"""
Campaign Orchestrator Module

캠페인 오케스트레이터:
- 모든 모듈 통합 관리
- 캠페인 라이프사이클 관리
- 실행 스케줄링 및 조율

Usage:
    from src.shared.campaign_orchestrator import CampaignOrchestrator

    orchestrator = CampaignOrchestrator()

    # 모듈 등록
    await orchestrator.register_modules(
        persona_generator=persona_generator,
        project_manager=project_manager,
        storyline_generator=storyline_generator,
        ip_manager=ip_manager
    )

    # 캠페인 실행
    await orchestrator.execute_campaign(project_id="seoul_food")
"""

from .orchestrator import CampaignOrchestrator
from .scheduler import CampaignScheduler, ScheduleEntry
from .executor import TaskExecutor, ExecutionContext
from .config import OrchestratorConfig

__all__ = [
    "CampaignOrchestrator",
    "CampaignScheduler",
    "ScheduleEntry",
    "TaskExecutor",
    "ExecutionContext",
    "OrchestratorConfig",
]

__version__ = "0.1.0"
