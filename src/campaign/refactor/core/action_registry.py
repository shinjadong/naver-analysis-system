"""
액션 레지스트리
"""

from typing import Dict, Type, Optional
from .action_base import CampaignAction


class ActionRegistry:
    """액션 등록 및 관리"""

    def __init__(self):
        self._actions: Dict[str, Type[CampaignAction]] = {}
        self._instances: Dict[str, CampaignAction] = {}

    def register_action(
        self,
        name: str,
        action_class: Type[CampaignAction],
        config: Optional[Dict] = None
    ):
        """액션 클래스 등록"""
        self._actions[name] = action_class
        if config:
            self._instances[name] = action_class(config)

    def get_action(self, name: str, config: Optional[Dict] = None) -> Optional[CampaignAction]:
        """액션 인스턴스 조회"""
        # 이미 인스턴스가 있으면 반환
        if name in self._instances and config is None:
            return self._instances[name]

        # 새로 생성
        if name in self._actions:
            action_class = self._actions[name]
            instance = action_class(config)
            if config is None:
                self._instances[name] = instance
            return instance

        return None

    def list_actions(self) -> list:
        """등록된 액션 목록"""
        return list(self._actions.keys())
