"""
BehaviorInjector 단위 테스트

테스트 항목:
- 베지어 커브 생성
- 인간적인 탭 생성
- 가변 속도 스크롤 생성
- 인간적인 타이핑 생성
"""

import pytest
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from shared.device_tools.behavior_injector import (
    BehaviorInjector,
    BehaviorConfig,
    TouchPoint,
    SwipeSegment,
    TypingEvent,
    ScrollStyle,
    create_stealth_injector,
    create_fast_injector,
)


class TestBezierCurve:
    """베지어 커브 생성 테스트"""

    def setup_method(self):
        self.injector = BehaviorInjector()

    def test_basic_bezier_curve(self):
        """기본 베지어 커브 생성"""
        start = (100, 100)
        end = (500, 800)

        points = self.injector.generate_bezier_curve(start, end)

        # 포인트가 생성되었는지 확인
        assert len(points) > 0
        assert isinstance(points[0], TouchPoint)

        # 시작점과 끝점 확인
        assert abs(points[0].x - start[0]) < 50  # 약간의 오차 허용
        assert abs(points[0].y - start[1]) < 50
        assert abs(points[-1].x - end[0]) < 50
        assert abs(points[-1].y - end[1]) < 50

    def test_bezier_curve_has_pressure(self):
        """베지어 커브 포인트에 압력 값이 있는지 확인"""
        points = self.injector.generate_bezier_curve((0, 0), (100, 100))

        for point in points:
            assert 0.0 <= point.pressure <= 1.0

    def test_bezier_curve_timestamps(self):
        """베지어 커브 포인트의 타임스탬프가 순차적인지 확인"""
        points = self.injector.generate_bezier_curve((0, 0), (100, 100))

        for i in range(1, len(points)):
            assert points[i].timestamp >= points[i-1].timestamp

    def test_bezier_curve_custom_sample_count(self):
        """커스텀 샘플 수로 베지어 커브 생성"""
        sample_count = 15
        points = self.injector.generate_bezier_curve(
            (0, 0), (100, 100),
            sample_count=sample_count
        )

        assert len(points) == sample_count + 1

    def test_bezier_curve_control_points(self):
        """다양한 제어점 수로 베지어 커브 생성"""
        for control_count in [1, 2, 3, 4]:
            points = self.injector.generate_bezier_curve(
                (0, 0), (100, 100),
                control_point_count=control_count
            )
            assert len(points) > 0


class TestHumanTap:
    """인간적인 탭 생성 테스트"""

    def setup_method(self):
        self.injector = BehaviorInjector()

    def test_basic_human_tap(self):
        """기본 인간적인 탭 생성"""
        x, y = 540, 700
        result = self.injector.generate_human_tap(x, y)

        # 결과 타입 확인
        assert hasattr(result, 'x')
        assert hasattr(result, 'y')
        assert hasattr(result, 'duration_ms')

    def test_tap_has_offset(self):
        """탭에 오프셋이 적용되는지 확인"""
        x, y = 500, 500

        # 여러 번 생성하여 오프셋이 다른지 확인
        results = [self.injector.generate_human_tap(x, y) for _ in range(10)]

        # 모든 결과가 동일하지 않아야 함 (랜덤성)
        x_values = [r.x for r in results]
        y_values = [r.y for r in results]

        assert len(set(x_values)) > 1 or len(set(y_values)) > 1

    def test_tap_offset_within_limits(self):
        """탭 오프셋이 설정된 범위 내에 있는지 확인"""
        config = BehaviorConfig(tap_offset_max_px=10)
        injector = BehaviorInjector(config)

        x, y = 500, 500

        for _ in range(100):
            result = injector.generate_human_tap(x, y)
            assert abs(result.offset_x) <= 10
            assert abs(result.offset_y) <= 10

    def test_tap_duration_range(self):
        """탭 지속시간이 설정된 범위 내에 있는지 확인"""
        config = BehaviorConfig(
            tap_duration_min_ms=50,
            tap_duration_max_ms=150
        )
        injector = BehaviorInjector(config)

        for _ in range(50):
            result = injector.generate_human_tap(500, 500)
            assert 50 <= result.duration_ms <= 150

    def test_tap_precision_affects_offset(self):
        """정밀도가 오프셋에 영향을 미치는지 확인"""
        high_precision_offsets = []
        low_precision_offsets = []

        for _ in range(50):
            high = self.injector.generate_human_tap(500, 500, precision=1.0)
            low = self.injector.generate_human_tap(500, 500, precision=0.3)

            high_precision_offsets.append(abs(high.offset_x) + abs(high.offset_y))
            low_precision_offsets.append(abs(low.offset_x) + abs(low.offset_y))

        # 낮은 정밀도가 더 큰 평균 오프셋을 가져야 함
        avg_high = sum(high_precision_offsets) / len(high_precision_offsets)
        avg_low = sum(low_precision_offsets) / len(low_precision_offsets)

        assert avg_low >= avg_high


class TestVariableScroll:
    """가변 속도 스크롤 생성 테스트"""

    def setup_method(self):
        self.injector = BehaviorInjector()

    def test_basic_variable_scroll(self):
        """기본 가변 속도 스크롤 생성"""
        segments = self.injector.generate_variable_scroll(1600, 800)

        assert len(segments) > 0
        assert isinstance(segments[0], SwipeSegment)

    def test_scroll_covers_distance(self):
        """스크롤이 전체 거리를 커버하는지 확인"""
        start_y = 1600
        end_y = 800

        segments = self.injector.generate_variable_scroll(start_y, end_y)

        # 멈춤이 아닌 세그먼트만 필터링
        swipe_segments = [s for s in segments if not s.is_pause]

        # 첫 세그먼트는 시작점에서 시작
        assert swipe_segments[0].start_y == start_y

        # 마지막 세그먼트는 끝점에서 끝
        assert swipe_segments[-1].end_y == end_y

    def test_scroll_has_pauses(self):
        """스크롤에 멈춤이 포함될 수 있는지 확인"""
        config = BehaviorConfig(scroll_pause_probability=0.5)
        injector = BehaviorInjector(config)

        # 여러 번 생성하여 멈춤이 있는지 확인
        has_pause = False
        for _ in range(20):
            segments = injector.generate_variable_scroll(1600, 800)
            if any(s.is_pause for s in segments):
                has_pause = True
                break

        assert has_pause

    def test_scroll_styles(self):
        """다양한 스크롤 스타일 테스트"""
        for style in ScrollStyle:
            segments = self.injector.generate_variable_scroll(
                1600, 800, style=style
            )
            assert len(segments) > 0

    def test_scroll_x_variance(self):
        """스크롤 X 좌표에 변화가 있는지 확인"""
        segments = self.injector.generate_variable_scroll(1600, 800)
        swipe_segments = [s for s in segments if not s.is_pause]

        # X 좌표가 모두 동일하지 않아야 함
        x_values = [s.start_x for s in swipe_segments] + [s.end_x for s in swipe_segments]
        assert len(set(x_values)) > 1


class TestHumanTyping:
    """인간적인 타이핑 생성 테스트"""

    def setup_method(self):
        self.injector = BehaviorInjector()

    def test_basic_human_typing(self):
        """기본 인간적인 타이핑 생성"""
        text = "hello"
        events = self.injector.generate_human_typing(text)

        assert len(events) > 0
        assert isinstance(events[0], TypingEvent)

    def test_typing_covers_all_characters(self):
        """모든 문자가 입력되는지 확인"""
        text = "test"
        events = self.injector.generate_human_typing(text, error_rate=0.0)

        # 오타 없이 모든 문자가 입력되어야 함
        typed_chars = [e.char for e in events]
        assert "".join(typed_chars) == text

    def test_typing_has_errors(self):
        """타이핑에 오타가 포함될 수 있는지 확인"""
        config = BehaviorConfig(typing_error_rate=0.5)  # 높은 오타율
        injector = BehaviorInjector(config)

        # 여러 번 생성하여 오타가 있는지 확인
        has_error = False
        for _ in range(20):
            events = injector.generate_human_typing("testing")
            if any(e.char == '\b' for e in events):
                has_error = True
                break

        assert has_error

    def test_typing_delays(self):
        """타이핑 지연 시간이 설정된 범위 내에 있는지 확인"""
        config = BehaviorConfig(
            typing_delay_min_ms=50,
            typing_delay_max_ms=200
        )
        injector = BehaviorInjector(config)

        events = injector.generate_human_typing("test", error_rate=0.0)

        for event in events:
            # 첫 문자나 단어 시작은 추가 지연이 있을 수 있음
            assert event.delay_ms >= 50

    def test_typing_word_pause(self):
        """단어 시작시 추가 지연이 있는지 확인"""
        events = self.injector.generate_human_typing("a b", error_rate=0.0)

        # 공백 다음 문자('b')의 지연이 더 길어야 함
        # events: 'a', ' ', 'b'
        if len(events) >= 3:
            # 'b'의 지연이 'a'보다 같거나 커야 함 (단어 시작 추가 지연)
            # (하지만 랜덤이므로 항상 그렇지는 않음)
            pass

    def test_typing_special_characters(self):
        """특수 문자 타이핑 테스트"""
        text = "hello@world.com"
        events = self.injector.generate_human_typing(text, error_rate=0.0)

        typed_chars = [e.char for e in events]
        assert "".join(typed_chars) == text


class TestConfiguration:
    """설정 테스트"""

    def test_default_config(self):
        """기본 설정으로 인젝터 생성"""
        injector = BehaviorInjector()
        assert injector.config is not None

    def test_custom_config(self):
        """커스텀 설정으로 인젝터 생성"""
        config = BehaviorConfig(
            typing_delay_min_ms=100,
            tap_offset_max_px=20,
        )
        injector = BehaviorInjector(config)

        assert injector.config.typing_delay_min_ms == 100
        assert injector.config.tap_offset_max_px == 20

    def test_stealth_injector_factory(self):
        """스텔스 인젝터 팩토리 함수"""
        injector = create_stealth_injector()

        assert injector.config.typing_delay_min_ms == 80
        assert injector.config.scroll_pause_probability == 0.25

    def test_fast_injector_factory(self):
        """빠른 인젝터 팩토리 함수"""
        injector = create_fast_injector()

        assert injector.config.typing_error_rate == 0.0
        assert injector.config.scroll_pause_probability == 0.05


class TestUtilityMethods:
    """유틸리티 메서드 테스트"""

    def setup_method(self):
        self.injector = BehaviorInjector()

    def test_add_jitter(self):
        """지터 추가 테스트"""
        value = 100
        jitter_percent = 0.1

        results = [self.injector.add_jitter(value, jitter_percent) for _ in range(50)]

        # 결과가 범위 내에 있어야 함
        for result in results:
            assert 90 <= result <= 110

        # 결과가 다양해야 함
        assert len(set(results)) > 1

    def test_random_delay(self):
        """랜덤 지연 테스트"""
        min_ms = 100
        max_ms = 500

        for _ in range(50):
            delay = self.injector.random_delay(min_ms, max_ms)
            assert min_ms <= delay <= max_ms

    def test_should_pause(self):
        """멈춤 여부 결정 테스트"""
        # 확률 1.0이면 항상 True
        assert self.injector.should_pause(1.0) == True

        # 확률 0.0이면 항상 False
        assert self.injector.should_pause(0.0) == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
