"""
Core 모듈 - 파이프라인 엔진, 액션 베이스, 컨텍스트 관리
"""

from .action_base import CampaignAction, ActionResult
from .action_registry import ActionRegistry
from .pipeline_engine import PipelineEngine, PipelineConfig
from .context_manager import ContextManager, CampaignContext

__all__ = [
    "CampaignAction",
    "ActionResult",
    "ActionRegistry",
    "PipelineEngine",
    "PipelineConfig",
    "ContextManager",
    "CampaignContext",
]
