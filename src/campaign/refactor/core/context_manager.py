"""
캠페인 실행 컨텍스트 관리자
"""

from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict, field


@dataclass
class CampaignContext:
    """캠페인 실행 컨텍스트"""
    # 기본 정보
    campaign_id: str
    device_serial: str
    start_time: datetime = field(default_factory=datetime.now)

    # 페르소나 정보
    persona_id: Optional[str] = None
    persona_name: Optional[str] = None
    android_id: Optional[str] = None
    behavior_profile: Optional[Dict[str, Any]] = None

    # 타겟 정보
    target_url: Optional[str] = None
    keyword: Optional[str] = None
    referrer: Optional[str] = None

    # 실행 상태
    current_action: Optional[str] = None
    visit_num: int = 0
    total_visits: int = 0

    # 결과 데이터
    results: Optional[Dict[str, Any]] = field(default_factory=dict)

    # 컴포넌트
    adb_tools: Optional[Any] = None
    cdp_client: Optional[Any] = None
    identity_manager: Optional[Any] = None
    supabase_client: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (직렬화 가능한 데이터만)"""
        data = {
            "campaign_id": self.campaign_id,
            "device_serial": self.device_serial,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "persona_id": self.persona_id,
            "persona_name": self.persona_name,
            "android_id": self.android_id,
            "behavior_profile": self.behavior_profile,
            "target_url": self.target_url,
            "keyword": self.keyword,
            "referrer": self.referrer,
            "current_action": self.current_action,
            "visit_num": self.visit_num,
            "total_visits": self.total_visits,
            "results": self.results,
        }
        return data


class ContextManager:
    """컨텍스트 관리자"""

    def __init__(self):
        self._contexts: Dict[str, CampaignContext] = {}

    def create_context(
        self,
        campaign_id: str,
        device_serial: str,
        **kwargs
    ) -> CampaignContext:
        """새 컨텍스트 생성"""
        context = CampaignContext(
            campaign_id=campaign_id,
            device_serial=device_serial,
            **kwargs
        )
        self._contexts[campaign_id] = context
        return context

    def get_context(self, campaign_id: str) -> Optional[CampaignContext]:
        """컨텍스트 조회"""
        return self._contexts.get(campaign_id)

    def update_context(self, campaign_id: str, **kwargs):
        """컨텍스트 업데이트"""
        context = self.get_context(campaign_id)
        if context:
            for key, value in kwargs.items():
                if hasattr(context, key):
                    setattr(context, key, value)

    def remove_context(self, campaign_id: str):
        """컨텍스트 삭제"""
        if campaign_id in self._contexts:
            del self._contexts[campaign_id]
