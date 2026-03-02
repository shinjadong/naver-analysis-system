"""
AI Session Controller - AI-driven session management for dynamic UI

droidrun의 Portal과 StealthAdbTools를 통합하여 AI가 각 스텝마다
동적 UI를 탐지하고 휴먼라이크 액션을 수행합니다.

핵심 개념:
- 네이버 UI는 동적이므로 고정 좌표로는 불가능
- AI가 매 스텝마다 UI 상태를 확인하고 적절한 요소를 찾아야 함
- droidrun StealthAdbTools로 휴먼라이크 액션 수행

사용법:
    controller = AISessionController(device_serial="R3CW60BHSAT")
    await controller.connect()

    # AI가 UI를 분석하고 '블로그' 탭을 찾아 클릭
    result = await controller.find_and_tap("블로그")

    # 특정 텍스트를 포함한 요소 찾기
    element = await controller.find_element_by_text("CCTV가격")
"""

import asyncio
import logging
import random
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger("ai_session")


@dataclass
class UIElement:
    """UI 요소 정보"""
    index: int
    text: str
    class_name: str
    bounds: Tuple[int, int, int, int]  # left, top, right, bottom
    center: Tuple[int, int]
    clickable: bool = True
    children: List['UIElement'] = field(default_factory=list)

    @property
    def width(self) -> int:
        return self.bounds[2] - self.bounds[0]

    @property
    def height(self) -> int:
        return self.bounds[3] - self.bounds[1]


@dataclass
class StepResult:
    """스텝 실행 결과"""
    success: bool
    step_name: str
    element_found: Optional[UIElement] = None
    action_taken: str = ""
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    ui_state_summary: str = ""


class AISessionController:
    """
    AI-driven 세션 컨트롤러

    각 스텝마다:
    1. Portal로 현재 UI 상태 획득
    2. AI가 타겟 요소를 분석/탐지
    3. StealthAdbTools로 휴먼라이크 액션 수행

    Features:
    - 동적 UI 요소 탐지 (텍스트, 클래스, 위치 기반)
    - 휴먼라이크 탭/스크롤/입력 (베지어 커브, Perlin 노이즈)
    - 스텝별 결과 로깅
    """

    def __init__(
        self,
        device_serial: str = None,
        use_tcp: bool = True,
        screen_width: int = 1080,
        screen_height: int = 2400
    ):
        self.device_serial = device_serial
        self.use_tcp = use_tcp
        self.screen_width = screen_width
        self.screen_height = screen_height

        self._device = None
        self._portal = None
        self._tools = None
        self._connected = False

        # 캐시
        self._ui_elements_cache: List[UIElement] = []
        self._raw_tree_cache: Dict = {}

    async def connect(self) -> bool:
        """디바이스 및 Portal 연결"""
        if self._connected:
            return True

        try:
            # droidrun 임포트
            import sys
            droidrun_path = "/home/tlswkehd/projects/cctv/droidrun"
            if droidrun_path not in sys.path:
                sys.path.insert(0, droidrun_path)

            from async_adbutils import adb
            from droidrun.tools.portal_client import PortalClient
            from droidrun.tools.stealth_adb import StealthAdbTools

            # 디바이스 연결
            self._device = await adb.device(serial=self.device_serial)
            state = await self._device.get_state()
            if state != "device":
                raise ConnectionError(f"Device not online: {state}")

            logger.info(f"Connected to device: {self.device_serial or 'default'}")

            # Portal 클라이언트 초기화
            self._portal = PortalClient(self._device, prefer_tcp=self.use_tcp)
            await self._portal.connect()
            logger.info(f"Portal connected (TCP: {self._portal.tcp_available})")

            # StealthAdbTools 초기화
            self._tools = StealthAdbTools(
                serial=self.device_serial,
                use_tcp=self.use_tcp
            )
            await self._tools.connect()
            logger.info("StealthAdbTools initialized")

            self._connected = True
            return True

        except ImportError as e:
            logger.error(f"droidrun import failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    async def get_ui_state(self) -> Dict[str, Any]:
        """현재 UI 상태 획득"""
        if not self._connected:
            await self.connect()

        try:
            import json
            state = await self._portal.get_state()

            # 문자열인 경우 JSON 파싱
            if isinstance(state, str):
                try:
                    state = json.loads(state)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse state as JSON: {state[:100]}...")
                    return {}

            # 중첩된 result/data 필드 처리
            if isinstance(state, dict):
                if "result" in state and isinstance(state["result"], str):
                    try:
                        state = json.loads(state["result"])
                    except json.JSONDecodeError:
                        pass
                elif "data" in state and isinstance(state["data"], str):
                    try:
                        state = json.loads(state["data"])
                    except json.JSONDecodeError:
                        pass

            self._raw_tree_cache = state
            return state if isinstance(state, dict) else {}
        except Exception as e:
            logger.error(f"Failed to get UI state: {e}")
            return {}

    def _parse_bounds(self, node: Dict) -> Optional[Tuple[int, int, int, int]]:
        """
        다양한 형식의 bounds 파싱

        지원 형식:
        - boundsInScreen: {"left": 0, "top": 0, "right": 1080, "bottom": 2340}
        - bounds: "left,top,right,bottom" (문자열)
        - bounds: [left, top, right, bottom] (리스트)
        """
        # 1. boundsInScreen (딕셔너리) - Portal 표준 형식
        bounds_dict = node.get("boundsInScreen") or node.get("boundsInParent")
        if isinstance(bounds_dict, dict):
            try:
                left = int(bounds_dict.get("left", 0))
                top = int(bounds_dict.get("top", 0))
                right = int(bounds_dict.get("right", 0))
                bottom = int(bounds_dict.get("bottom", 0))
                if right > left and bottom > top:  # 유효한 bounds
                    return (left, top, right, bottom)
            except (ValueError, TypeError):
                pass

        # 2. bounds 문자열 "left,top,right,bottom"
        bounds_str = node.get("bounds", "")
        if isinstance(bounds_str, str) and bounds_str:
            try:
                parts = bounds_str.split(",")
                if len(parts) == 4:
                    left, top, right, bottom = map(int, parts)
                    if right > left and bottom > top:
                        return (left, top, right, bottom)
            except (ValueError, AttributeError):
                pass

        # 3. bounds 리스트 [left, top, right, bottom]
        if isinstance(bounds_str, (list, tuple)) and len(bounds_str) == 4:
            try:
                left, top, right, bottom = map(int, bounds_str)
                if right > left and bottom > top:
                    return (left, top, right, bottom)
            except (ValueError, TypeError):
                pass

        return None

    async def refresh_ui_elements(self) -> List[UIElement]:
        """UI 요소 목록 새로고침"""
        state = await self.get_ui_state()

        if not isinstance(state, dict):
            logger.warning(f"State is not a dict: {type(state)}")
            return []

        elements = []
        a11y_tree = state.get("a11y_tree", []) or state.get("result", {}).get("a11y_tree", []) or []

        # a11y_tree가 dict(단일 루트 요소)인 경우 리스트로 래핑
        if isinstance(a11y_tree, dict):
            a11y_tree = [a11y_tree]

        def parse_element(node: Dict, depth: int = 0) -> Optional[UIElement]:
            """재귀적으로 요소 파싱"""
            bounds = self._parse_bounds(node)
            if not bounds:
                # bounds 없어도 children은 파싱 시도
                children_elements = []
                for child in node.get("children", []):
                    child_element = parse_element(child, depth + 1)
                    if child_element:
                        children_elements.append(child_element)

                # bounds 없으면 children만 반환용 더미 (실제로는 flatten에서 children만 사용)
                if children_elements:
                    dummy = UIElement(
                        index=-1, text="", class_name="",
                        bounds=(0, 0, 0, 0), center=(0, 0), clickable=False
                    )
                    dummy.children = children_elements
                    return dummy
                return None

            left, top, right, bottom = bounds
            center_x = (left + right) // 2
            center_y = (top + bottom) // 2

            # 텍스트 추출 (여러 필드에서)
            text = (
                node.get("text", "") or
                node.get("contentDescription", "") or
                node.get("hint", "") or
                ""
            )

            element = UIElement(
                index=node.get("index", node.get("drawingOrder", -1)),
                text=text,
                class_name=node.get("className", ""),
                bounds=(left, top, right, bottom),
                center=(center_x, center_y),
                clickable=node.get("isClickable", False) or node.get("isCheckable", False)
            )

            # 자식 요소 파싱
            for child in node.get("children", []):
                child_element = parse_element(child, depth + 1)
                if child_element:
                    element.children.append(child_element)

            return element

        # 모든 루트 요소 파싱
        for node in a11y_tree:
            element = parse_element(node)
            if element:
                elements.append(element)

        self._ui_elements_cache = elements
        logger.debug(f"Parsed {len(self._flatten_elements())} UI elements")
        return elements

    async def wait_for_elements(
        self,
        min_elements: int = 1,
        timeout_sec: float = 10.0,
        poll_interval: float = 0.5
    ) -> List[UIElement]:
        """
        UI 요소가 로드될 때까지 대기

        Args:
            min_elements: 최소 요소 수 (텍스트 있는 요소 기준)
            timeout_sec: 최대 대기 시간 (초)
            poll_interval: 폴링 간격 (초)

        Returns:
            로드된 UI 요소 목록
        """
        import time
        start_time = time.time()

        while time.time() - start_time < timeout_sec:
            elements = await self.refresh_ui_elements()
            all_elements = self._flatten_elements()
            text_elements = [e for e in all_elements if e.text.strip()]

            if len(text_elements) >= min_elements:
                logger.info(f"Found {len(text_elements)} text elements after {time.time() - start_time:.1f}s")
                return elements

            logger.debug(f"Waiting for elements... ({len(text_elements)}/{min_elements})")
            await asyncio.sleep(poll_interval)

        logger.warning(f"Timeout waiting for elements (got {len(text_elements)}, wanted {min_elements})")
        return self._ui_elements_cache

    def _flatten_elements(self, elements: List[UIElement] = None) -> List[UIElement]:
        """요소 트리를 평탄화"""
        if elements is None:
            elements = self._ui_elements_cache

        result = []
        for element in elements:
            result.append(element)
            result.extend(self._flatten_elements(element.children))
        return result

    async def find_element_by_text(
        self,
        text: str,
        partial: bool = True,
        refresh: bool = True
    ) -> Optional[UIElement]:
        """
        텍스트로 요소 찾기

        Args:
            text: 찾을 텍스트
            partial: 부분 매칭 허용
            refresh: UI 상태 새로고침 여부

        Returns:
            찾은 요소 또는 None
        """
        if refresh:
            await self.refresh_ui_elements()

        all_elements = self._flatten_elements()

        for element in all_elements:
            if partial:
                if text.lower() in element.text.lower():
                    return element
            else:
                if text.lower() == element.text.lower():
                    return element

        return None

    async def find_elements_by_text(
        self,
        text: str,
        partial: bool = True,
        refresh: bool = True
    ) -> List[UIElement]:
        """텍스트로 여러 요소 찾기"""
        if refresh:
            await self.refresh_ui_elements()

        all_elements = self._flatten_elements()
        results = []

        for element in all_elements:
            if partial:
                if text.lower() in element.text.lower():
                    results.append(element)
            else:
                if text.lower() == element.text.lower():
                    results.append(element)

        return results

    async def find_element_by_class(
        self,
        class_name: str,
        refresh: bool = True
    ) -> Optional[UIElement]:
        """클래스 이름으로 요소 찾기"""
        if refresh:
            await self.refresh_ui_elements()

        all_elements = self._flatten_elements()

        for element in all_elements:
            if class_name.lower() in element.class_name.lower():
                return element

        return None

    async def find_element_in_region(
        self,
        y_min: int,
        y_max: int,
        text: str = None,
        refresh: bool = True
    ) -> Optional[UIElement]:
        """
        특정 y 영역 내에서 요소 찾기

        Args:
            y_min: 최소 y 좌표
            y_max: 최대 y 좌표
            text: 텍스트 필터 (선택)
            refresh: 새로고침 여부

        Returns:
            찾은 요소
        """
        if refresh:
            await self.refresh_ui_elements()

        all_elements = self._flatten_elements()

        for element in all_elements:
            center_y = element.center[1]
            if y_min <= center_y <= y_max:
                if text is None or text.lower() in element.text.lower():
                    return element

        return None

    # =========================================================================
    # Humanlike Actions (StealthAdbTools 기반)
    # =========================================================================

    async def humanlike_tap(self, x: int, y: int) -> bool:
        """
        휴먼라이크 탭 (무작위 오프셋 적용)

        Args:
            x: x 좌표
            y: y 좌표

        Returns:
            성공 여부
        """
        if not self._connected:
            await self.connect()

        try:
            # 무작위 오프셋 추가 (±10px)
            offset_x = random.randint(-10, 10)
            offset_y = random.randint(-10, 10)

            tap_x = max(0, min(self.screen_width, x + offset_x))
            tap_y = max(0, min(self.screen_height, y + offset_y))

            await self._device.click(tap_x, tap_y)
            await asyncio.sleep(random.uniform(0.1, 0.3))

            logger.debug(f"Tapped at ({tap_x}, {tap_y})")
            return True

        except Exception as e:
            logger.error(f"Tap failed: {e}")
            return False

    async def humanlike_swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int = 800
    ) -> bool:
        """
        휴먼라이크 스와이프 (베지어 커브 + Perlin 노이즈)

        Args:
            start_x, start_y: 시작점
            end_x, end_y: 종료점
            duration_ms: 지속시간 (ms)

        Returns:
            성공 여부
        """
        if not self._connected:
            await self.connect()

        try:
            # StealthAdbTools의 swipe 메서드 사용
            result = await self._tools.swipe(
                start_x, start_y, end_x, end_y, duration_ms
            )
            await asyncio.sleep(random.uniform(0.2, 0.5))
            return result

        except Exception as e:
            logger.error(f"Swipe failed: {e}")
            # 폴백: 일반 스와이프
            try:
                await self._device.swipe(
                    start_x, start_y, end_x, end_y,
                    duration=duration_ms / 1000
                )
                return True
            except Exception as e2:
                logger.error(f"Fallback swipe also failed: {e2}")
                return False

    async def humanlike_scroll_down(self, distance: int = 800) -> bool:
        """아래로 스크롤 (빠른 속도)"""
        center_x = self.screen_width // 2
        start_y = self.screen_height // 2 + distance // 2
        end_y = self.screen_height // 2 - distance // 2

        return await self.humanlike_swipe(
            center_x, start_y, center_x, end_y,
            duration_ms=random.randint(150, 250)  # 빠른 스크롤
        )

    async def humanlike_scroll_up(self, distance: int = 700) -> bool:
        """위로 스크롤 (빠른 속도)"""
        center_x = self.screen_width // 2
        start_y = self.screen_height // 2 - distance // 2
        end_y = self.screen_height // 2 + distance // 2

        return await self.humanlike_swipe(
            center_x, start_y, center_x, end_y,
            duration_ms=random.randint(120, 200)  # 빠른 스크롤
        )

    async def humanlike_input_text(self, text: str, clear: bool = False) -> bool:
        """
        휴먼라이크 텍스트 입력

        droidrun Portal의 키보드를 사용하여 자연스러운 타이핑 구현

        Args:
            text: 입력할 텍스트
            clear: 기존 텍스트 삭제 여부

        Returns:
            성공 여부
        """
        if not self._connected:
            await self.connect()

        try:
            result = await self._portal.input_text(text, clear=clear)
            return result

        except Exception as e:
            logger.error(f"Input text failed: {e}")
            return False

    # =========================================================================
    # High-level Actions
    # =========================================================================

    async def find_and_tap(
        self,
        text: str,
        partial: bool = True,
        y_region: Tuple[int, int] = None
    ) -> StepResult:
        """
        텍스트로 요소를 찾아서 탭

        Args:
            text: 찾을 텍스트
            partial: 부분 매칭 허용
            y_region: y 좌표 범위 제한 (min, max)

        Returns:
            StepResult
        """
        logger.info(f"Finding and tapping: '{text}'")

        # UI 새로고침 및 요소 찾기
        await self.refresh_ui_elements()

        element = None
        if y_region:
            element = await self.find_element_in_region(
                y_region[0], y_region[1], text, refresh=False
            )
        else:
            element = await self.find_element_by_text(text, partial=partial, refresh=False)

        if not element:
            return StepResult(
                success=False,
                step_name=f"find_and_tap({text})",
                error_message=f"Element with text '{text}' not found"
            )

        # 휴먼라이크 탭
        success = await self.humanlike_tap(element.center[0], element.center[1])

        return StepResult(
            success=success,
            step_name=f"find_and_tap({text})",
            element_found=element,
            action_taken=f"Tapped at ({element.center[0]}, {element.center[1]})"
        )

    async def scroll_and_find(
        self,
        text: str,
        max_scrolls: int = 5,
        direction: str = "down"
    ) -> StepResult:
        """
        스크롤하면서 요소 찾기

        Args:
            text: 찾을 텍스트
            max_scrolls: 최대 스크롤 횟수
            direction: 스크롤 방향 ("down" or "up")

        Returns:
            StepResult with found element
        """
        logger.info(f"Scrolling to find: '{text}'")

        for i in range(max_scrolls):
            # 현재 화면에서 찾기
            element = await self.find_element_by_text(text, refresh=True)

            if element:
                return StepResult(
                    success=True,
                    step_name=f"scroll_and_find({text})",
                    element_found=element,
                    action_taken=f"Found after {i} scrolls"
                )

            # 스크롤
            if direction == "down":
                await self.humanlike_scroll_down()
            else:
                await self.humanlike_scroll_up()

            await asyncio.sleep(random.uniform(0.8, 1.5))

        return StepResult(
            success=False,
            step_name=f"scroll_and_find({text})",
            error_message=f"Element '{text}' not found after {max_scrolls} scrolls"
        )

    async def open_url(self, url: str) -> bool:
        """Chrome에서 URL 열기"""
        if not self._connected:
            await self.connect()

        try:
            cmd = f'am start -a android.intent.action.VIEW -d "{url}" com.android.chrome'
            await self._device.shell(cmd)
            await asyncio.sleep(random.uniform(2.5, 4.0))
            return True
        except Exception as e:
            logger.error(f"Failed to open URL: {e}")
            return False

    async def open_url_with_referrer(self, url: str, referrer: str) -> bool:
        """
        CDP를 사용하여 referrer와 함께 URL 열기

        1. Chrome에서 about:blank 열기 (ADB intent)
        2. CDP Page.navigate(url, referrer) 실행

        실패 시 일반 open_url()로 폴백.

        Args:
            url: 열 URL
            referrer: 설정할 referrer URL

        Returns:
            성공 여부
        """
        if not self._connected:
            await self.connect()

        try:
            from .naver_chrome_use.cdp_client import CdpClient

            # about:blank 열기 (CDP 대상 페이지 준비)
            cmd = 'am start -a android.intent.action.VIEW -d "about:blank" com.android.chrome'
            await self._device.shell(cmd)
            await asyncio.sleep(random.uniform(1.5, 2.5))

            # CDP로 referrer 포함 네비게이션
            cdp = CdpClient(device_serial=self.device_serial)
            if not await cdp.connect():
                logger.warning("CDP failed, falling back to direct open")
                await cdp.disconnect()
                return await self.open_url(url)

            success = await cdp.navigate_with_referrer(url, referrer)
            await cdp.disconnect()

            if success:
                logger.info(f"Opened with referrer: {url[:50]}...")
                return True

            # CDP 네비게이션 실패 시 폴백
            logger.warning("CDP navigate failed, falling back to direct open")
            return await self.open_url(url)

        except ImportError:
            logger.warning("CdpClient not available, using direct open")
            return await self.open_url(url)
        except Exception as e:
            logger.error(f"open_url_with_referrer failed: {e}")
            return await self.open_url(url)

    async def get_current_activity(self) -> str:
        """현재 액티비티 반환"""
        if not self._connected:
            await self.connect()

        try:
            result = await self._device.shell(
                "dumpsys window | grep mCurrentFocus"
            )
            return result.strip()
        except Exception:
            return ""

    async def take_screenshot(self, save_path: str = None) -> bytes:
        """스크린샷 촬영"""
        if not self._connected:
            await self.connect()

        try:
            data = await self._portal.take_screenshot()

            if save_path:
                with open(save_path, "wb") as f:
                    f.write(data)

            return data
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return b""

    def get_ui_summary(self) -> str:
        """현재 UI 상태 요약"""
        all_elements = self._flatten_elements()

        summary_lines = [f"Total elements: {len(all_elements)}"]

        # 텍스트가 있는 요소들
        text_elements = [e for e in all_elements if e.text]
        summary_lines.append(f"Elements with text: {len(text_elements)}")

        # 상위 10개 텍스트 요소
        for i, element in enumerate(text_elements[:10]):
            text_preview = element.text[:30] + "..." if len(element.text) > 30 else element.text
            summary_lines.append(
                f"  [{element.index}] {text_preview} @ ({element.center[0]}, {element.center[1]})"
            )

        return "\n".join(summary_lines)


# =========================================================================
# Singleton
# =========================================================================

_controller_instance: Optional[AISessionController] = None


def get_ai_controller(device_serial: str = None) -> AISessionController:
    """AISessionController 싱글톤 반환"""
    global _controller_instance

    if _controller_instance is None:
        _controller_instance = AISessionController(device_serial=device_serial)

    return _controller_instance


async def reset_controller():
    """컨트롤러 리셋"""
    global _controller_instance
    _controller_instance = None
