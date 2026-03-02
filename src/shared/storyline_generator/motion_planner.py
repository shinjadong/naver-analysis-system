"""
모션 계획기

스토리라인의 액션을 실제 디바이스에서 실행 가능한
저수준 모션으로 변환합니다.

Author: Naver AI Evolution System
Created: 2025-12-15
"""

import math
import random
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any

logger = logging.getLogger("naver_evolution.motion_planner")


@dataclass
class TouchPoint:
    """터치 포인트"""
    x: int
    y: int
    pressure: float = 0.5
    duration_ms: int = 50


@dataclass
class BezierCurve:
    """베지어 커브"""
    start: Tuple[int, int]
    control1: Tuple[int, int]
    control2: Tuple[int, int]
    end: Tuple[int, int]
    duration_ms: int = 300

    def get_point(self, t: float) -> Tuple[float, float]:
        """
        t (0-1)에서의 점 계산

        3차 베지어 곡선:
        P(t) = (1-t)^3*P0 + 3*(1-t)^2*t*P1 + 3*(1-t)*t^2*P2 + t^3*P3
        """
        t2 = t * t
        t3 = t2 * t
        mt = 1 - t
        mt2 = mt * mt
        mt3 = mt2 * mt

        x = (mt3 * self.start[0] +
             3 * mt2 * t * self.control1[0] +
             3 * mt * t2 * self.control2[0] +
             t3 * self.end[0])

        y = (mt3 * self.start[1] +
             3 * mt2 * t * self.control1[1] +
             3 * mt * t2 * self.control2[1] +
             t3 * self.end[1])

        return (x, y)

    def get_points(self, segments: int = 10) -> List[Tuple[int, int]]:
        """커브를 따라 여러 점 생성"""
        points = []
        for i in range(segments + 1):
            t = i / segments
            x, y = self.get_point(t)
            points.append((int(x), int(y)))
        return points


@dataclass
class SwipeGesture:
    """스와이프 제스처"""
    points: List[Tuple[int, int]]
    total_duration_ms: int
    velocity_curve: str = "ease_in_out"  # linear, ease_in, ease_out, ease_in_out


@dataclass
class MotionPlan:
    """모션 계획"""
    action_type: str
    touch_points: List[TouchPoint] = field(default_factory=list)
    bezier_curves: List[BezierCurve] = field(default_factory=list)
    swipes: List[SwipeGesture] = field(default_factory=list)
    adb_commands: List[str] = field(default_factory=list)
    total_duration_ms: int = 0


class MotionPlanner:
    """
    모션 계획기

    고수준 액션을 자연스러운 저수준 모션으로 변환합니다.

    사용 예시:
        planner = MotionPlanner(screen_size=(1080, 2400))

        # 탭 모션 계획
        plan = planner.plan_tap(540, 1200)

        # 스크롤 모션 계획
        plan = planner.plan_scroll(direction="down", distance=500)

        # ADB 명령 생성
        commands = planner.to_adb_commands(plan)
    """

    def __init__(
        self,
        screen_size: Tuple[int, int] = (1080, 2400),
        tap_variance: float = 0.05,
        scroll_variance: float = 0.1
    ):
        """
        Args:
            screen_size: 화면 크기 (width, height)
            tap_variance: 탭 위치 분산 비율
            scroll_variance: 스크롤 거리 분산 비율
        """
        self.screen_width, self.screen_height = screen_size
        self.tap_variance = tap_variance
        self.scroll_variance = scroll_variance

    def plan_tap(
        self,
        x: int,
        y: int,
        with_approach: bool = True
    ) -> MotionPlan:
        """
        탭 모션 계획

        Args:
            x: 타겟 X 좌표
            y: 타겟 Y 좌표
            with_approach: 접근 모션 포함 여부

        Returns:
            MotionPlan
        """
        plan = MotionPlan(action_type="tap")

        # 약간의 분산 추가
        variance_x = int(self.screen_width * self.tap_variance)
        variance_y = int(self.screen_height * self.tap_variance)

        final_x = x + random.randint(-variance_x, variance_x)
        final_y = y + random.randint(-variance_y, variance_y)

        # 화면 범위 내로 제한
        final_x = max(10, min(self.screen_width - 10, final_x))
        final_y = max(10, min(self.screen_height - 10, final_y))

        if with_approach:
            # 베지어 곡선으로 접근
            start_x = final_x + random.randint(-100, 100)
            start_y = final_y + random.randint(-50, 50)

            curve = self._create_approach_curve(
                (start_x, start_y),
                (final_x, final_y)
            )
            plan.bezier_curves.append(curve)

        # 터치 포인트
        plan.touch_points.append(TouchPoint(
            x=final_x,
            y=final_y,
            pressure=random.uniform(0.4, 0.7),
            duration_ms=random.randint(40, 80)
        ))

        plan.total_duration_ms = sum(tp.duration_ms for tp in plan.touch_points)
        if plan.bezier_curves:
            plan.total_duration_ms += sum(bc.duration_ms for bc in plan.bezier_curves)

        return plan

    def plan_scroll(
        self,
        direction: str = "down",
        distance: int = 500,
        speed: str = "medium"
    ) -> MotionPlan:
        """
        스크롤 모션 계획

        Args:
            direction: 스크롤 방향 (up, down, left, right)
            distance: 스크롤 거리 (pixels)
            speed: 스크롤 속도 (slow, medium, fast)

        Returns:
            MotionPlan
        """
        plan = MotionPlan(action_type="scroll")

        # 분산 추가
        variance = int(distance * self.scroll_variance)
        actual_distance = distance + random.randint(-variance, variance)

        # 시작점 결정
        center_x = self.screen_width // 2
        center_y = self.screen_height // 2

        if direction == "down":
            start_y = int(self.screen_height * 0.7)
            end_y = start_y - actual_distance
            start = (center_x, start_y)
            end = (center_x + random.randint(-20, 20), end_y)
        elif direction == "up":
            start_y = int(self.screen_height * 0.3)
            end_y = start_y + actual_distance
            start = (center_x, start_y)
            end = (center_x + random.randint(-20, 20), end_y)
        elif direction == "left":
            start_x = int(self.screen_width * 0.8)
            end_x = start_x - actual_distance
            start = (start_x, center_y)
            end = (end_x, center_y + random.randint(-20, 20))
        else:  # right
            start_x = int(self.screen_width * 0.2)
            end_x = start_x + actual_distance
            start = (start_x, center_y)
            end = (end_x, center_y + random.randint(-20, 20))

        # 속도에 따른 지속 시간
        speed_map = {
            "slow": (800, 1200),
            "medium": (400, 600),
            "fast": (200, 350)
        }
        duration_range = speed_map.get(speed, speed_map["medium"])
        duration = random.randint(*duration_range)

        # 베지어 커브로 자연스러운 스와이프
        curve = self._create_scroll_curve(start, end, duration)
        plan.bezier_curves.append(curve)

        # 스와이프 제스처 생성
        swipe = SwipeGesture(
            points=curve.get_points(segments=8),
            total_duration_ms=duration,
            velocity_curve="ease_in_out"
        )
        plan.swipes.append(swipe)

        plan.total_duration_ms = duration

        return plan

    def plan_typing(
        self,
        text: str,
        typing_speed: str = "medium"
    ) -> MotionPlan:
        """
        타이핑 모션 계획

        Args:
            text: 입력할 텍스트
            typing_speed: 타이핑 속도 (slow, medium, fast)

        Returns:
            MotionPlan
        """
        plan = MotionPlan(action_type="typing")

        # 속도별 글자당 지연 시간 (ms)
        speed_map = {
            "slow": (100, 200),
            "medium": (50, 120),
            "fast": (30, 70)
        }
        delay_range = speed_map.get(typing_speed, speed_map["medium"])

        total_time = 0
        for char in text:
            delay = random.randint(*delay_range)
            total_time += delay

            # 가끔 타이핑 실수 시뮬레이션 (더 긴 지연)
            if random.random() < 0.05:
                total_time += random.randint(100, 300)

        plan.total_duration_ms = total_time
        plan.adb_commands.append(f'input text "{text}"')

        return plan

    def plan_wait(self, duration_ms: int) -> MotionPlan:
        """대기 모션 계획"""
        plan = MotionPlan(action_type="wait")
        plan.total_duration_ms = duration_ms
        return plan

    def plan_back(self) -> MotionPlan:
        """뒤로가기 모션 계획"""
        plan = MotionPlan(action_type="back")
        plan.adb_commands.append("input keyevent KEYCODE_BACK")
        plan.total_duration_ms = random.randint(100, 300)
        return plan

    def to_adb_commands(
        self,
        plan: MotionPlan,
        include_delays: bool = True
    ) -> List[Dict[str, Any]]:
        """
        MotionPlan을 ADB 명령으로 변환

        Args:
            plan: 모션 계획
            include_delays: 지연 포함 여부

        Returns:
            ADB 명령 목록
        """
        commands = []

        if plan.action_type == "tap" and plan.touch_points:
            tp = plan.touch_points[0]
            commands.append({
                "command": f"input tap {tp.x} {tp.y}",
                "delay_before_ms": random.randint(50, 150) if include_delays else 0,
                "delay_after_ms": random.randint(100, 300) if include_delays else 0
            })

        elif plan.action_type == "scroll" and plan.bezier_curves:
            curve = plan.bezier_curves[0]
            commands.append({
                "command": f"input swipe {curve.start[0]} {curve.start[1]} {curve.end[0]} {curve.end[1]} {curve.duration_ms}",
                "delay_before_ms": random.randint(50, 100) if include_delays else 0,
                "delay_after_ms": random.randint(200, 500) if include_delays else 0
            })

        elif plan.action_type == "wait":
            commands.append({
                "command": f"sleep {plan.total_duration_ms / 1000:.2f}",
                "delay_before_ms": 0,
                "delay_after_ms": 0
            })

        elif plan.action_type == "back":
            commands.append({
                "command": "input keyevent KEYCODE_BACK",
                "delay_before_ms": random.randint(50, 100) if include_delays else 0,
                "delay_after_ms": random.randint(300, 600) if include_delays else 0
            })

        elif plan.action_type == "typing" and plan.adb_commands:
            for cmd in plan.adb_commands:
                commands.append({
                    "command": cmd,
                    "delay_before_ms": random.randint(100, 200) if include_delays else 0,
                    "delay_after_ms": random.randint(200, 400) if include_delays else 0
                })

        return commands

    def _create_approach_curve(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int]
    ) -> BezierCurve:
        """접근 베지어 커브 생성"""
        # 자연스러운 접근을 위한 제어점
        mid_x = (start[0] + end[0]) // 2
        mid_y = (start[1] + end[1]) // 2

        control1 = (
            start[0] + random.randint(-30, 30),
            mid_y + random.randint(-20, 20)
        )
        control2 = (
            end[0] + random.randint(-20, 20),
            end[1] + random.randint(-30, 30)
        )

        return BezierCurve(
            start=start,
            control1=control1,
            control2=control2,
            end=end,
            duration_ms=random.randint(150, 250)
        )

    def _create_scroll_curve(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        duration_ms: int
    ) -> BezierCurve:
        """스크롤 베지어 커브 생성"""
        # 자연스러운 스크롤을 위한 곡선
        dx = end[0] - start[0]
        dy = end[1] - start[1]

        # 중간점에서 약간 벗어나는 제어점
        control1 = (
            start[0] + dx * 0.3 + random.randint(-15, 15),
            start[1] + dy * 0.3 + random.randint(-15, 15)
        )
        control2 = (
            start[0] + dx * 0.7 + random.randint(-15, 15),
            start[1] + dy * 0.7 + random.randint(-15, 15)
        )

        return BezierCurve(
            start=start,
            control1=control1,
            control2=control2,
            end=end,
            duration_ms=duration_ms
        )

    def generate_natural_reading_pattern(
        self,
        content_height: int,
        reading_time_sec: int
    ) -> List[MotionPlan]:
        """
        자연스러운 읽기 패턴 생성

        Args:
            content_height: 콘텐츠 높이
            reading_time_sec: 읽기 시간 (초)

        Returns:
            모션 계획 목록
        """
        plans = []

        # 스크롤 횟수 계산
        scroll_count = max(1, content_height // 500)
        time_per_scroll = reading_time_sec * 1000 // scroll_count

        for i in range(scroll_count):
            # 읽기 대기
            read_time = int(time_per_scroll * random.uniform(0.6, 0.9))
            plans.append(self.plan_wait(read_time))

            # 스크롤
            scroll_distance = random.randint(300, 600)
            plans.append(self.plan_scroll(
                direction="down",
                distance=scroll_distance,
                speed=random.choice(["slow", "medium"])
            ))

            # 가끔 멈춤 (관심 있는 부분)
            if random.random() < 0.3:
                plans.append(self.plan_wait(random.randint(1000, 3000)))

        return plans
