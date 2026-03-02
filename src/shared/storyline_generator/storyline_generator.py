"""
DeepSeek 기반 스토리라인 생성기

페르소나의 컨텍스트를 기반으로 자연스러운 행동 스토리라인을 생성합니다.

Author: Naver AI Evolution System
Created: 2025-12-15
"""

import json
import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any

from .deepseek_client import DeepSeekClient
from .prompts import (
    SYSTEM_PROMPT,
    STORYLINE_GENERATION_PROMPT,
    MOTION_REFINEMENT_PROMPT,
    ADAPTATION_PROMPT,
    PERSONA_BEHAVIOR_PROMPT,
    NAVER_CONTEXT_PROMPT
)

logger = logging.getLogger("naver_evolution.storyline_generator")


@dataclass
class Action:
    """단일 행동"""
    type: str  # search, scroll, tap, read, back, wait
    target: str  # 요소 설명 또는 좌표
    duration_ms: int  # 실행 시간
    parameters: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""  # 행동 이유
    adb_commands: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "target": self.target,
            "duration_ms": self.duration_ms,
            "parameters": self.parameters,
            "reasoning": self.reasoning,
            "adb_commands": self.adb_commands
        }


@dataclass
class Storyline:
    """행동 스토리라인"""
    storyline_id: str
    persona_context: Dict[str, Any]
    actions: List[Action]
    expected_signals: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "storyline_id": self.storyline_id,
            "persona_context": self.persona_context,
            "actions": [a.to_dict() for a in self.actions],
            "expected_signals": self.expected_signals,
            "created_at": self.created_at.isoformat()
        }


class StorylineGenerator:
    """
    DeepSeek 기반 스토리라인 생성기

    페르소나의 특성과 현재 컨텍스트를 기반으로
    자연스러운 행동 시퀀스를 생성합니다.

    사용 예시:
        generator = StorylineGenerator(api_key="...")

        storyline = await generator.generate_storyline(
            persona_name="Persona_01",
            persona_type="curious_reader",
            interests=["맛집", "여행"],
            keyword="서울 맛집",
            current_page="search_results",
            session_goal="블로그 3개 방문",
            screen_size=(1080, 2400)
        )

        for action in storyline.actions:
            refined = await generator.refine_to_adb_commands(action)
            # ADB 명령 실행
    """

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        max_history: int = 10
    ):
        """
        Args:
            api_key: DeepSeek API 키
            model: 사용할 모델
            max_history: 유지할 최대 행동 히스토리
        """
        self.client = DeepSeekClient(api_key, model)
        self.action_history: List[Action] = []
        self.max_history = max_history

    async def generate_storyline(
        self,
        persona_name: str,
        persona_type: str,
        interests: List[str],
        keyword: str,
        current_page: str,
        session_goal: str,
        screen_size: tuple,
        current_app: str = "com.android.chrome",
        battery_level: int = 100,
        additional_context: str = ""
    ) -> Storyline:
        """
        스토리라인 생성

        Args:
            persona_name: 페르소나 이름
            persona_type: 페르소나 유형 (curious_reader, speed_scanner, deep_researcher)
            interests: 관심사 목록
            keyword: 검색 키워드
            current_page: 현재 페이지 유형
            session_goal: 세션 목표
            screen_size: 화면 크기 (width, height)
            current_app: 현재 앱 패키지
            battery_level: 배터리 잔량
            additional_context: 추가 컨텍스트

        Returns:
            Storyline 객체
        """
        # 이전 행동 포맷팅
        previous_actions = self._format_history()

        # 프롬프트 구성
        prompt = STORYLINE_GENERATION_PROMPT.format(
            persona_name=persona_name,
            persona_type=persona_type,
            interests=", ".join(interests),
            keyword=keyword,
            current_page=current_page,
            session_goal=session_goal,
            screen_width=screen_size[0],
            screen_height=screen_size[1],
            current_app=current_app,
            battery_level=battery_level,
            previous_actions=previous_actions
        )

        if additional_context:
            prompt += f"\n\n# 추가 컨텍스트\n{additional_context}"

        # 시스템 프롬프트에 네이버 컨텍스트 추가
        system_prompt = SYSTEM_PROMPT + "\n\n" + NAVER_CONTEXT_PROMPT

        try:
            # DeepSeek 호출
            response = await self.client.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7
            )

            # Action 객체로 변환
            actions = []
            for action_data in response.get("actions", []):
                action = Action(
                    type=action_data.get("type", "wait"),
                    target=action_data.get("target", ""),
                    duration_ms=action_data.get("duration_ms", 1000),
                    parameters=action_data.get("parameters", {}),
                    reasoning=action_data.get("reasoning", "")
                )
                actions.append(action)

            storyline = Storyline(
                storyline_id=response.get("storyline_id", str(uuid.uuid4())),
                persona_context=response.get("persona_context", {
                    "type": persona_type,
                    "interests": interests
                }),
                actions=actions,
                expected_signals=response.get("expected_signals", {})
            )

            logger.info(f"Generated storyline: {storyline.storyline_id} with {len(actions)} actions")
            return storyline

        except Exception as e:
            logger.error(f"Failed to generate storyline: {e}")
            # 기본 스토리라인 반환
            return self._create_default_storyline(
                persona_type, interests, current_page
            )

    async def refine_to_adb_commands(
        self,
        action: Action,
        screen_size: tuple = (1080, 2400)
    ) -> Action:
        """
        액션을 ADB 명령으로 변환

        Args:
            action: 변환할 Action
            screen_size: 화면 크기

        Returns:
            ADB 명령이 추가된 Action
        """
        prompt = MOTION_REFINEMENT_PROMPT.format(
            raw_action=json.dumps(action.to_dict(), ensure_ascii=False)
        )

        prompt += f"\n\n# 디바이스 정보\n- 화면 크기: {screen_size[0]}x{screen_size[1]}"

        try:
            response = await self.client.generate_json(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.3  # 더 결정적인 출력
            )

            action.adb_commands = response.get("adb_commands", [])

            logger.debug(f"Refined action: {action.type} -> {len(action.adb_commands)} commands")
            return action

        except Exception as e:
            logger.error(f"Failed to refine action: {e}")
            # 기본 ADB 명령 생성
            action.adb_commands = self._create_default_adb_commands(action, screen_size)
            return action

    async def adapt_from_result(
        self,
        execution_result: Dict[str, Any],
        expected_result: Dict[str, Any],
        errors: List[str] = None
    ) -> List[Action]:
        """
        실행 결과에 따른 적응

        Args:
            execution_result: 실제 실행 결과
            expected_result: 예상했던 결과
            errors: 발생한 오류 목록

        Returns:
            조정된 Action 목록
        """
        prompt = ADAPTATION_PROMPT.format(
            execution_result=json.dumps(execution_result, ensure_ascii=False),
            expected_result=json.dumps(expected_result, ensure_ascii=False),
            actual_result=json.dumps(execution_result, ensure_ascii=False),
            errors="\n".join(errors) if errors else "없음"
        )

        try:
            response = await self.client.generate_json(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.5
            )

            adjusted_actions = []
            for action_data in response.get("adjusted_next_actions", []):
                action = Action(
                    type=action_data.get("type", "wait"),
                    target=action_data.get("target", ""),
                    duration_ms=action_data.get("duration_ms", 1000),
                    parameters=action_data.get("parameters", {}),
                    reasoning=action_data.get("reasoning", "adapted")
                )
                adjusted_actions.append(action)

            logger.info(f"Adapted {len(adjusted_actions)} actions from result")
            return adjusted_actions

        except Exception as e:
            logger.error(f"Failed to adapt from result: {e}")
            return []

    def record_action(self, action: Action) -> None:
        """
        행동 기록

        Args:
            action: 기록할 Action
        """
        self.action_history.append(action)
        if len(self.action_history) > self.max_history:
            self.action_history.pop(0)

    def clear_history(self) -> None:
        """행동 히스토리 초기화"""
        self.action_history.clear()

    def _format_history(self) -> str:
        """이전 행동 포맷팅"""
        if not self.action_history:
            return "없음"

        history = []
        for i, action in enumerate(self.action_history[-5:], 1):
            history.append(
                f"{i}. [{action.type}] {action.target} "
                f"({action.duration_ms}ms) - {action.reasoning}"
            )
        return "\n".join(history)

    def _create_default_storyline(
        self,
        persona_type: str,
        interests: List[str],
        current_page: str
    ) -> Storyline:
        """기본 스토리라인 생성 (API 실패 시)"""
        default_actions = [
            Action(
                type="wait",
                target="page_load",
                duration_ms=1500,
                reasoning="페이지 로딩 대기"
            ),
            Action(
                type="scroll",
                target="content_area",
                duration_ms=2000,
                parameters={"direction": "down", "distance": 500},
                reasoning="콘텐츠 탐색"
            ),
            Action(
                type="read",
                target="main_content",
                duration_ms=5000,
                reasoning="콘텐츠 읽기"
            )
        ]

        return Storyline(
            storyline_id=str(uuid.uuid4()),
            persona_context={
                "type": persona_type,
                "interests": interests
            },
            actions=default_actions,
            expected_signals={
                "dwell_time": "30초",
                "scroll_depth": "50%"
            }
        )

    def _create_default_adb_commands(
        self,
        action: Action,
        screen_size: tuple
    ) -> List[Dict[str, Any]]:
        """기본 ADB 명령 생성"""
        width, height = screen_size
        center_x, center_y = width // 2, height // 2

        commands = []

        if action.type == "tap":
            commands.append({
                "command": f"input tap {center_x} {center_y}",
                "delay_before_ms": 100,
                "delay_after_ms": 300
            })
        elif action.type == "scroll":
            start_y = int(height * 0.7)
            end_y = int(height * 0.3)
            commands.append({
                "command": f"input swipe {center_x} {start_y} {center_x} {end_y} {action.duration_ms}",
                "delay_before_ms": 100,
                "delay_after_ms": 500
            })
        elif action.type == "wait" or action.type == "read":
            commands.append({
                "command": f"sleep {action.duration_ms / 1000}",
                "delay_before_ms": 0,
                "delay_after_ms": 0
            })
        elif action.type == "back":
            commands.append({
                "command": "input keyevent KEYCODE_BACK",
                "delay_before_ms": 100,
                "delay_after_ms": 500
            })

        return commands

    async def health_check(self) -> bool:
        """DeepSeek API 연결 확인"""
        return await self.client.health_check()
