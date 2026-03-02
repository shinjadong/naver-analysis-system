"""
액션 베이스 클래스 및 결과 구조
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import time


@dataclass
class ActionResult:
    """액션 실행 결과"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.metadata is None:
            self.metadata = {}


class CampaignAction(ABC):
    """캠페인 액션 베이스 클래스"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.name = self.__class__.__name__
        self._context: Optional[Dict[str, Any]] = None

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> ActionResult:
        """액션 실행 (추상 메서드)"""
        pass

    def set_context(self, context: Dict[str, Any]):
        """실행 컨텍스트 설정"""
        self._context = context

    def get_context_value(self, key: str, default=None):
        """컨텍스트 값 조회"""
        return self._context.get(key, default) if self._context else default

    async def _execute_with_timing(self, context: Dict[str, Any]) -> ActionResult:
        """실행 시간 측정을 포함한 실행"""
        start_time = time.time()

        try:
            self.set_context(context)
            result = await self.execute(context)
            result.execution_time = time.time() - start_time
            return result
        except Exception as e:
            return ActionResult(
                success=False,
                error_message=f"{self.name} 실행 실패: {str(e)}",
                execution_time=time.time() - start_time
            )
