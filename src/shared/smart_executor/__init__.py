"""
Smart Executor - Portal UI 파싱 + 베지어 모션 통합 실행기

DroidRun Portal의 정확한 UI 트리와 MotionPlanner의 자연스러운
베지어 곡선 모션을 통합합니다.

사용 예시:
    from src.shared.smart_executor import SmartExecutor

    executor = SmartExecutor(device_serial="...")
    await executor.setup()

    # 텍스트로 요소 찾아서 자연스럽게 탭
    result = await executor.tap_by_text("검색 결과")

    # UI 컨텍스트 (DeepSeek 프롬프트용)
    context = await executor.get_ui_context()

Author: Naver AI Evolution System
Created: 2025-12-17
"""

from .executor import (
    SmartExecutor,
    ActionResult,
    UISnapshot,
    ExecutionContext,
    ExecutorConfig
)
from .context_builder import UIContextBuilder

__all__ = [
    'SmartExecutor',
    'ActionResult',
    'UISnapshot',
    'ExecutionContext',
    'ExecutorConfig',
    'UIContextBuilder'
]
