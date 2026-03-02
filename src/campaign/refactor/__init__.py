"""
모듈화된 캠페인 프레임워크

기존 boost_campaign.py를 재사용 가능한 액션 기반 아키텍처로 리팩토링

주요 컴포넌트:
- core: 액션 베이스, 파이프라인 엔진, 컨텍스트 관리
- actions: 재사용 가능한 액션 모듈 (identity, reset, navigation, interaction, logging)
- campaigns: YAML 기반 캠페인 정의 및 실행기

사용법:
    from src.campaign.refactor.campaigns import CampaignRunner

    runner = CampaignRunner("campaigns/blog_boost.yaml")
    await runner.run_campaign(target=10, now_mode=True)
"""

from .core import (
    CampaignAction,
    ActionResult,
    ActionRegistry,
    PipelineEngine,
    PipelineConfig,
    ContextManager,
    CampaignContext,
)

from .campaigns import CampaignRunner

__all__ = [
    # Core
    "CampaignAction",
    "ActionResult",
    "ActionRegistry",
    "PipelineEngine",
    "PipelineConfig",
    "ContextManager",
    "CampaignContext",
    # Campaign
    "CampaignRunner",
]

__version__ = "1.0.0"
