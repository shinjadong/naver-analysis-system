"""
Storyline Generator Module

DeepSeek API를 활용하여 자연스러운 사용자 행동 스토리라인을 생성합니다.

주요 클래스:
- StorylineGenerator: 스토리라인 생성기
- MotionPlanner: 모션 계획기
- DeepSeekClient: DeepSeek API 클라이언트

Usage:
    from src.shared.storyline_generator import (
        StorylineGenerator,
        MotionPlanner,
        Action,
        Storyline
    )

    # 스토리라인 생성
    generator = StorylineGenerator(api_key="your_api_key")

    storyline = await generator.generate_storyline(
        persona_name="Persona_01",
        persona_type="curious_reader",
        interests=["맛집", "여행"],
        keyword="서울 맛집",
        current_page="search_results",
        session_goal="블로그 3개 방문",
        screen_size=(1080, 2400)
    )

    # 모션 계획
    planner = MotionPlanner(screen_size=(1080, 2400))
    tap_plan = planner.plan_tap(540, 1200)
    commands = planner.to_adb_commands(tap_plan)

Author: Naver AI Evolution System
Created: 2025-12-15
"""

from .storyline_generator import (
    StorylineGenerator,
    Action,
    Storyline
)
from .motion_planner import (
    MotionPlanner,
    MotionPlan,
    TouchPoint,
    BezierCurve,
    SwipeGesture
)
from .deepseek_client import DeepSeekClient
from .prompts import (
    SYSTEM_PROMPT,
    STORYLINE_GENERATION_PROMPT,
    MOTION_REFINEMENT_PROMPT,
    ADAPTATION_PROMPT,
    PERSONA_BEHAVIOR_PROMPT,
    NAVER_CONTEXT_PROMPT
)

__all__ = [
    # Generator
    "StorylineGenerator",
    "Action",
    "Storyline",

    # Motion Planner
    "MotionPlanner",
    "MotionPlan",
    "TouchPoint",
    "BezierCurve",
    "SwipeGesture",

    # Client
    "DeepSeekClient",

    # Prompts
    "SYSTEM_PROMPT",
    "STORYLINE_GENERATION_PROMPT",
    "MOTION_REFINEMENT_PROMPT",
    "ADAPTATION_PROMPT",
    "PERSONA_BEHAVIOR_PROMPT",
    "NAVER_CONTEXT_PROMPT",
]

__version__ = "0.1.0"
