"""
SmartExecutor - Portal UI + EnhancedAdbTools 통합 실행기

DroidRun Portal에서 UI 트리를 획득하고, 텍스트 매칭으로
정확한 요소를 찾아 EnhancedAdbTools의 휴먼라이크 입력으로 실행합니다.

모든 탭, 스와이프, 키 입력은 EnhancedAdbTools를 통해 휴먼라이크로 수행됩니다.

Author: Naver AI Evolution System
Created: 2025-12-17
"""

import asyncio
import logging
import subprocess
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple

from ..portal_client import PortalClient, PortalConfig
from ..portal_client.element import UIElement, UITree
from ..storyline_generator.motion_planner import MotionPlanner, MotionPlan
from ..device_tools import EnhancedAdbTools, AdbConfig

logger = logging.getLogger("naver_evolution.smart_executor")


@dataclass
class ActionResult:
    """액션 실행 결과"""
    success: bool
    action_type: str
    message: str = ""
    element: Optional[UIElement] = None
    coordinates: Optional[Tuple[int, int]] = None
    duration_ms: int = 0
    raw_output: str = ""


@dataclass
class UISnapshot:
    """UI 상태 스냅샷"""
    timestamp: float = 0.0
    screen_size: Tuple[int, int] = (0, 0)
    total_elements: int = 0
    clickable_count: int = 0
    elements_summary: List[Dict[str, Any]] = field(default_factory=list)
    screenshot_path: Optional[str] = None
    raw_tree: Optional[UITree] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "screen_size": self.screen_size,
            "total_elements": self.total_elements,
            "clickable_count": self.clickable_count,
            "elements": self.elements_summary[:10]
        }


@dataclass
class ExecutionContext:
    """액션 실행 컨텍스트 (Lifecycle)"""
    action_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    snapshot_before: Optional[UISnapshot] = None
    snapshot_after: Optional[UISnapshot] = None
    result: Optional[ActionResult] = None

    @property
    def success(self) -> bool:
        return self.result.success if self.result else False


@dataclass
class ExecutorConfig:
    """실행기 설정"""
    device_serial: Optional[str] = None
    tap_variance: float = 0.02  # 탭 위치 분산 (2%)
    scroll_variance: float = 0.08  # 스크롤 거리 분산 (8%)
    use_bezier: bool = True  # 베지어 곡선 사용
    retry_on_fail: int = 2  # 실패 시 재시도 횟수
    ui_cache_ttl: float = 0.3  # UI 캐시 유효 시간

    # Action Lifecycle 설정
    lifecycle_enabled: bool = True  # 라이프사이클 사용
    capture_before: bool = True  # 액션 전 스냅샷
    capture_after: bool = True  # 액션 후 스냅샷
    capture_screenshot: bool = False  # 스크린샷 캡처 (선택)
    log_actions: bool = True  # 액션 로깅


class SmartExecutor:
    """
    스마트 실행기

    DroidRun Portal의 UI 트리에서 텍스트 매칭으로 요소를 찾고,
    MotionPlanner의 베지어 곡선으로 자연스럽게 실행합니다.

    사용 예시:
        executor = SmartExecutor(device_serial="...")
        await executor.setup()

        # 텍스트로 요소 찾아서 탭
        result = await executor.tap_by_text("서울 맛집 추천")
        if result.success:
            print(f"탭 성공: {result.coordinates}")

        # 키워드 기반 첫 번째 결과 탭
        result = await executor.tap_first_match(["맛집", "추천", "베스트"])

        # UI 컨텍스트 획득 (DeepSeek 프롬프트용)
        context = await executor.get_ui_context()
    """

    def __init__(self, config: ExecutorConfig = None, device_serial: str = None):
        """
        Args:
            config: 실행기 설정
            device_serial: 디바이스 시리얼 (config보다 우선)
        """
        self.config = config or ExecutorConfig()
        if device_serial:
            self.config.device_serial = device_serial

        # Portal 클라이언트
        portal_config = PortalConfig(
            device_serial=self.config.device_serial,
            cache_ttl_sec=self.config.ui_cache_ttl
        )
        self.portal = PortalClient(portal_config)

        # 모션 플래너 (화면 크기는 setup에서 설정)
        self._screen_size: Tuple[int, int] = (1080, 2400)
        self.planner: Optional[MotionPlanner] = None

        # EnhancedAdbTools 초기화 (휴먼라이크 입력)
        adb_config = AdbConfig(
            serial=self.config.device_serial,
            screen_width=self._screen_size[0],
            screen_height=self._screen_size[1],
        )
        self.adb_tools = EnhancedAdbTools(adb_config)

        # 상태
        self._is_setup = False
        self._last_ui: Optional[UITree] = None

    # =========================================================================
    # Setup
    # =========================================================================

    async def setup(self) -> bool:
        """
        실행기 초기화

        1. Portal 설정
        2. 화면 크기 획득
        3. MotionPlanner 초기화
        4. EnhancedAdbTools 화면 크기 업데이트

        Returns:
            설정 성공 여부
        """
        logger.info("Setting up SmartExecutor...")

        # Portal 설정
        portal_ready = await self.portal.setup()
        if not portal_ready:
            logger.warning("Portal setup incomplete, continuing with limited functionality")

        # 화면 크기 획득
        self._screen_size = self._get_screen_size()
        logger.info(f"Screen size: {self._screen_size}")

        # EnhancedAdbTools 화면 크기 업데이트
        self.adb_tools.config.screen_width = self._screen_size[0]
        self.adb_tools.config.screen_height = self._screen_size[1]

        # MotionPlanner 초기화
        self.planner = MotionPlanner(
            screen_size=self._screen_size,
            tap_variance=self.config.tap_variance,
            scroll_variance=self.config.scroll_variance
        )

        self._is_setup = True
        logger.info("SmartExecutor setup complete")
        return True

    def _get_screen_size(self) -> Tuple[int, int]:
        """ADB로 화면 크기 획득 (orientation 고려)"""
        cmd_base = ["adb"]
        if self.config.device_serial:
            cmd_base.extend(["-s", self.config.device_serial])

        # 1. 물리적 크기 확인
        try:
            cmd = cmd_base + ["shell", "wm", "size"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and "Physical size:" in result.stdout:
                size_str = result.stdout.split("Physical size:")[-1].strip()
                w, h = size_str.split("x")
                physical_w, physical_h = int(w), int(h)
            else:
                physical_w, physical_h = 1080, 2400
        except:
            physical_w, physical_h = 1080, 2400

        # 2. 화면 방향 확인
        try:
            cmd = cmd_base + ["shell", "dumpsys", "display", "|", "grep", "mCurrentOrientation"]
            result = subprocess.run(
                cmd_base + ["shell", "dumpsys display | grep mCurrentOrientation"],
                capture_output=True, text=True, timeout=10, shell=False
            )
            output = result.stdout

            # mCurrentOrientation=1 이면 가로모드
            if "mCurrentOrientation=1" in output or "mCurrentOrientation=3" in output:
                # 가로모드: width > height
                self._is_landscape = True
                if physical_w < physical_h:
                    return (physical_h, physical_w)  # swap
                return (physical_w, physical_h)
            else:
                # 세로모드: height > width
                self._is_landscape = False
                if physical_w > physical_h:
                    return (physical_h, physical_w)  # swap
                return (physical_w, physical_h)
        except:
            pass

        self._is_landscape = False
        return (physical_w, physical_h)

    @property
    def screen_size(self) -> Tuple[int, int]:
        """화면 크기"""
        return self._screen_size

    # =========================================================================
    # ADB Commands (EnhancedAdbTools 기반 휴먼라이크)
    # =========================================================================

    async def _execute_tap(self, x: int, y: int) -> bool:
        """탭 실행 (EnhancedAdbTools 휴먼라이크)"""
        result = await self.adb_tools.tap(x, y)
        return result.success

    async def _execute_swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int) -> bool:
        """스와이프 실행 (EnhancedAdbTools 휴먼라이크)"""
        result = await self.adb_tools.swipe(x1, y1, x2, y2, duration_ms)
        return result.success

    async def _execute_keyevent(self, key: str) -> bool:
        """키 이벤트 실행 (EnhancedAdbTools)"""
        result = await self.adb_tools.press_key(key)
        return result.success

    # =========================================================================
    # UI Tree
    # =========================================================================

    async def refresh_ui(self) -> Optional[UITree]:
        """UI 트리 갱신"""
        self.portal.clear_cache()
        self._last_ui = await self.portal.get_ui_tree()
        return self._last_ui

    async def get_ui_tree(self, force_refresh: bool = False) -> Optional[UITree]:
        """
        UI 트리 획득

        Args:
            force_refresh: 강제 갱신 여부

        Returns:
            UITree 또는 None
        """
        if force_refresh or self._last_ui is None:
            return await self.refresh_ui()
        return self._last_ui

    async def find_element(self, **criteria) -> Optional[UIElement]:
        """
        조건에 맞는 요소 검색

        Args:
            **criteria: text, text_contains, resource_id, clickable 등

        Returns:
            첫 번째 매칭 요소 또는 None
        """
        tree = await self.get_ui_tree()
        if tree:
            return tree.find(**criteria)
        return None

    async def find_elements(self, **criteria) -> List[UIElement]:
        """조건에 맞는 모든 요소 검색"""
        tree = await self.get_ui_tree()
        if tree:
            return tree.find_all(**criteria)
        return []

    # =========================================================================
    # Tap Actions
    # =========================================================================

    async def tap_by_text(
        self,
        text: str,
        exact: bool = False,
        clickable_only: bool = True,
        refresh_ui: bool = True
    ) -> ActionResult:
        """
        텍스트로 요소 찾아서 탭

        Args:
            text: 검색할 텍스트
            exact: 정확한 매칭 여부
            clickable_only: 클릭 가능한 요소만
            refresh_ui: UI 갱신 여부

        Returns:
            ActionResult
        """
        if refresh_ui:
            await self.refresh_ui()

        tree = self._last_ui
        if not tree:
            return ActionResult(
                success=False,
                action_type="tap",
                message="UI 트리 획득 실패"
            )

        # 요소 검색
        if exact:
            elements = tree.find_all(text=text)
        else:
            elements = tree.find_all(text_contains=text)

        if clickable_only:
            elements = [e for e in elements if e.clickable]

        if not elements:
            return ActionResult(
                success=False,
                action_type="tap",
                message=f"'{text}' 요소를 찾을 수 없음"
            )

        # 가장 짧은 텍스트 (가장 정확한 매칭)
        element = min(elements, key=lambda e: len(e.text) if e.text else 999)
        return await self._tap_element(element)

    async def tap_first_match(
        self,
        keywords: List[str],
        region: Tuple[float, float, float, float] = (0.2, 0.8, 0.0, 1.0)
    ) -> ActionResult:
        """
        키워드 매칭으로 첫 번째 요소 탭

        Args:
            keywords: 검색 키워드 목록
            region: 검색 영역 (top_ratio, bottom_ratio, left_ratio, right_ratio)

        Returns:
            ActionResult
        """
        await self.refresh_ui()

        tree = self._last_ui
        if not tree:
            return ActionResult(
                success=False,
                action_type="tap",
                message="UI 트리 획득 실패"
            )

        # 영역 내 클릭 가능한 요소들
        top, bottom, left, right = region
        height, width = self._screen_size[1], self._screen_size[0]

        candidates = []
        for elem in tree.clickable_elements:
            cx, cy = elem.center
            if (width * left <= cx <= width * right and
                height * top <= cy <= height * bottom):
                candidates.append(elem)

        # 키워드 매칭
        for kw in keywords:
            for elem in candidates:
                if elem.contains_text(kw):
                    return await self._tap_element(elem)

        # 키워드 매칭 실패 시 첫 번째 클릭 가능 요소
        if candidates:
            return await self._tap_element(candidates[0])

        return ActionResult(
            success=False,
            action_type="tap",
            message="매칭되는 요소 없음"
        )

    async def tap_blog_post(
        self,
        index: int = 0,
        min_text_length: int = 15,
        exclude_patterns: List[str] = None
    ) -> ActionResult:
        """
        블로그 포스트 제목을 찾아서 탭

        네이버 블로그 검색 결과에서 실제 블로그 포스트 제목을 찾습니다.
        - 텍스트 길이 15자 이상
        - y좌표 500 이상 (탭 영역 아래)
        - View, Layout 등 시스템 요소 제외

        Args:
            index: 몇 번째 결과를 클릭할지 (0부터 시작)
            min_text_length: 최소 텍스트 길이
            exclude_patterns: 제외할 패턴 목록

        Returns:
            ActionResult
        """
        await self.refresh_ui()

        tree = self._last_ui
        if not tree:
            return ActionResult(
                success=False,
                action_type="tap",
                message="UI 트리 획득 실패"
            )

        # 기본 제외 패턴
        default_excludes = [
            'view', 'layout', 'container', 'root', 'widget', 'toolbar',
            'webview', 'frame', 'tabwidget', 'fdr-', '7jb8', 'nxsearch',
            '라벨이 지정되지', '이미지 설명을', 'mdep', 'app-root',
            '쿠폰', '광고', '배너', 'ad', 'banner', '정렬', '필터',
            '업체명 검색', '로딩중', '영업 중', '예약', '포장주문'
        ]
        excludes = (exclude_patterns or []) + default_excludes

        def is_valid_blog_title(text: str) -> bool:
            """블로그 제목으로 유효한지 판단"""
            # 한글이 포함되어 있어야 함
            korean_count = sum(1 for c in text if '\uac00' <= c <= '\ud7a3')
            if korean_count < 3:
                return False

            # 랜덤 해시 문자열 제외 (영문자+숫자가 연속 8자 이상)
            import re
            if re.search(r'[a-zA-Z0-9_]{8,}', text):
                # 하지만 한글이 많으면 허용
                if korean_count < len(text) * 0.3:
                    return False

            return True

        # 블로그 포스트 후보 찾기
        candidates = []
        for elem in tree.all_elements:
            text = elem.text.strip() if elem.text else ""

            # 조건 체크
            if len(text) < min_text_length:
                continue
            if elem.bounds.top < 500:  # 탭 영역 위
                continue
            if not elem.clickable:
                continue

            # 제외 패턴 체크
            text_lower = text.lower()
            if any(exc in text_lower for exc in excludes):
                continue

            # 블로그 제목 유효성
            if not is_valid_blog_title(text):
                continue

            # 후보에 추가
            candidates.append((elem, elem.bounds.top))

        # y좌표 기준 정렬 (위에서 아래로)
        candidates.sort(key=lambda x: x[1])

        if index < len(candidates):
            element = candidates[index][0]
            return await self._tap_element(element)

        return ActionResult(
            success=False,
            action_type="tap",
            message=f"블로그 포스트 #{index + 1}을 찾을 수 없음 (후보: {len(candidates)}개)"
        )

    async def tap_at(self, x: int, y: int) -> ActionResult:
        """
        좌표로 직접 탭 (EnhancedAdbTools 휴먼라이크)

        Args:
            x: X 좌표
            y: Y 좌표

        Returns:
            ActionResult
        """
        if not self.planner:
            await self.setup()

        # EnhancedAdbTools가 자동으로 베지어 오프셋 적용
        success = await self._execute_tap(x, y)
        return ActionResult(
            success=success,
            action_type="tap",
            coordinates=(x, y),
            message=f"휴먼라이크 탭: ({x}, {y})"
        )

    async def _tap_element(self, element: UIElement) -> ActionResult:
        """UIElement 탭 (EnhancedAdbTools 휴먼라이크)"""
        x, y = element.center

        # EnhancedAdbTools가 자동으로 베지어 오프셋 적용
        success = await self._execute_tap(x, y)
        return ActionResult(
            success=success,
            action_type="tap",
            element=element,
            coordinates=(x, y),
            message=f"탭: '{element.text[:30]}' at ({x}, {y})"
        )

    # =========================================================================
    # Scroll Actions
    # =========================================================================

    async def scroll(
        self,
        direction: str = "down",
        distance: int = 500,
        speed: str = "medium"
    ) -> ActionResult:
        """
        스크롤 실행 (EnhancedAdbTools 휴먼라이크)

        Args:
            direction: 방향 (up, down, left, right)
            distance: 거리 (pixels)
            speed: 속도 (slow, medium, fast)

        Returns:
            ActionResult
        """
        if not self.planner:
            await self.setup()

        # EnhancedAdbTools의 휴먼라이크 스크롤 사용
        if direction == "down":
            result = await self.adb_tools.scroll_down(distance)
        elif direction == "up":
            result = await self.adb_tools.scroll_up(distance)
        else:
            # left/right는 기본 swipe로 처리
            center_y = self._screen_size[1] // 2
            if direction == "left":
                result = await self.adb_tools.swipe(
                    self._screen_size[0] - 100, center_y,
                    100, center_y
                )
            else:  # right
                result = await self.adb_tools.swipe(
                    100, center_y,
                    self._screen_size[0] - 100, center_y
                )

        return ActionResult(
            success=result.success,
            action_type="scroll",
            message=f"휴먼라이크 스크롤 {direction}: {distance}px",
            duration_ms=result.duration_ms
        )

    # =========================================================================
    # Other Actions (EnhancedAdbTools 기반 휴먼라이크)
    # =========================================================================

    async def back(self) -> ActionResult:
        """뒤로가기 (EnhancedAdbTools)"""
        result = await self.adb_tools.back()
        return ActionResult(
            success=result.success,
            action_type="back",
            message="뒤로가기"
        )

    async def wait(self, duration_ms: int) -> ActionResult:
        """대기"""
        await asyncio.sleep(duration_ms / 1000)
        return ActionResult(
            success=True,
            action_type="wait",
            message=f"대기: {duration_ms}ms",
            duration_ms=duration_ms
        )

    async def start_app(self, package: str, activity: str = None) -> ActionResult:
        """앱 시작 (EnhancedAdbTools)"""
        result = await self.adb_tools.start_app(package, activity)
        return ActionResult(
            success=result.success,
            action_type="start_app",
            message=f"앱 시작: {package}",
            raw_output=result.message
        )

    async def open_url(self, url: str) -> ActionResult:
        """URL 열기 (EnhancedAdbTools - Chrome)"""
        result = await self.adb_tools.open_url(url, package="com.android.chrome")
        return ActionResult(
            success=result.success,
            action_type="open_url",
            message=f"URL: {url[:50]}",
            raw_output=result.message
        )

    # =========================================================================
    # Context for DeepSeek
    # =========================================================================

    async def get_ui_context(self) -> Dict[str, Any]:
        """
        DeepSeek 프롬프트용 UI 컨텍스트

        Returns:
            UI 컨텍스트 딕셔너리
        """
        await self.refresh_ui()

        tree = self._last_ui
        if not tree:
            return {"error": "UI 트리 획득 실패"}

        # 클릭 가능한 요소들
        clickable = tree.clickable_elements[:20]
        elements_info = []
        for elem in clickable:
            elements_info.append({
                "text": elem.text[:50] if elem.text else elem.content_desc[:50],
                "center": elem.center,
                "bounds": elem.bounds.to_dict(),
                "clickable": True,
                "class": elem.class_name.split(".")[-1]
            })

        return {
            "screen_size": self._screen_size,
            "total_elements": len(tree.all_elements),
            "clickable_count": len(tree.clickable_elements),
            "elements": elements_info
        }

    async def get_screen_summary(self) -> str:
        """화면 요약 텍스트 (DeepSeek 프롬프트용)"""
        context = await self.get_ui_context()

        if "error" in context:
            return "화면 정보를 가져올 수 없습니다."

        lines = [
            f"화면 크기: {context['screen_size']}",
            f"클릭 가능 요소: {context['clickable_count']}개",
            "",
            "주요 요소들:"
        ]

        for elem in context.get("elements", [])[:10]:
            text = elem.get("text", "")[:30]
            if text:
                lines.append(f"  - '{text}' at {elem['center']}")

        return "\n".join(lines)

    # =========================================================================
    # Status
    # =========================================================================

    async def get_status(self) -> Dict[str, Any]:
        """실행기 상태"""
        portal_status = await self.portal.get_status()

        return {
            "is_setup": self._is_setup,
            "device_serial": self.config.device_serial,
            "screen_size": self._screen_size,
            "portal": portal_status,
            "use_bezier": self.config.use_bezier
        }

    # =========================================================================
    # Action Lifecycle (OBSERVE → THINK → ACT → VERIFY)
    # =========================================================================

    async def _capture_snapshot(self, include_screenshot: bool = False) -> UISnapshot:
        """
        현재 UI 상태 스냅샷 캡처

        Args:
            include_screenshot: 스크린샷 포함 여부

        Returns:
            UISnapshot
        """
        import time

        await self.refresh_ui()
        tree = self._last_ui

        snapshot = UISnapshot(
            timestamp=time.time(),
            screen_size=self._screen_size,
            raw_tree=tree
        )

        if tree:
            snapshot.total_elements = len(tree.all_elements)
            snapshot.clickable_count = len(tree.clickable_elements)

            # 상위 요소 요약
            for elem in tree.clickable_elements[:15]:
                text = elem.text.strip() if elem.text else ""
                if text and len(text) > 2:
                    snapshot.elements_summary.append({
                        "text": text[:40],
                        "center": elem.center,
                        "class": elem.class_name.split(".")[-1],
                        "bounds": (elem.bounds.left, elem.bounds.top,
                                   elem.bounds.right, elem.bounds.bottom)
                    })

        # 스크린샷 (선택적)
        if include_screenshot:
            screenshot_bytes = await self.portal.get_screenshot()
            if screenshot_bytes:
                import tempfile
                import os
                path = os.path.join(
                    tempfile.gettempdir(),
                    f"snapshot_{int(snapshot.timestamp * 1000)}.png"
                )
                with open(path, 'wb') as f:
                    f.write(screenshot_bytes)
                snapshot.screenshot_path = path

        return snapshot

    async def execute(
        self,
        action_type: str,
        **params
    ) -> ExecutionContext:
        """
        통합 액션 실행 (Lifecycle 적용)

        기본 워크플로우:
        1. OBSERVE: UI 요소 파싱 + 스냅샷
        2. THINK: (외부에서 DeepSeek 분석 가능)
        3. ACT: 베지어 모션으로 액션 실행
        4. VERIFY: 실행 후 상태 확인

        Args:
            action_type: 액션 유형 (tap, tap_text, tap_blog, scroll, back, wait, open_url)
            **params: 액션별 파라미터

        Returns:
            ExecutionContext (스냅샷 + 결과 포함)

        사용 예시:
            ctx = await executor.execute("tap_text", text="블로그", exact=True)
            if ctx.success:
                print(f"성공: {ctx.result.message}")
                print(f"이전 UI: {ctx.snapshot_before.clickable_count}개")
                print(f"이후 UI: {ctx.snapshot_after.clickable_count}개")
        """
        context = ExecutionContext(action_type=action_type, params=params)

        # 1. OBSERVE: 액션 전 스냅샷
        if self.config.lifecycle_enabled and self.config.capture_before:
            context.snapshot_before = await self._capture_snapshot(
                include_screenshot=self.config.capture_screenshot
            )
            if self.config.log_actions:
                logger.info(
                    f"[OBSERVE] {action_type}: "
                    f"{context.snapshot_before.clickable_count} clickable elements"
                )

        # 2. ACT: 액션 실행
        try:
            result = await self._dispatch_action(action_type, params)
            context.result = result

            if self.config.log_actions:
                status = "SUCCESS" if result.success else "FAILED"
                logger.info(f"[ACT] {action_type}: {status} - {result.message}")

        except Exception as e:
            context.result = ActionResult(
                success=False,
                action_type=action_type,
                message=f"Exception: {str(e)}"
            )
            logger.error(f"[ACT] {action_type}: Exception - {e}")

        # 3. VERIFY: 액션 후 스냅샷
        if self.config.lifecycle_enabled and self.config.capture_after:
            await asyncio.sleep(0.3)  # UI 업데이트 대기
            context.snapshot_after = await self._capture_snapshot(
                include_screenshot=self.config.capture_screenshot
            )
            if self.config.log_actions:
                logger.info(
                    f"[VERIFY] {action_type}: "
                    f"{context.snapshot_after.clickable_count} clickable elements"
                )

        return context

    async def _dispatch_action(
        self,
        action_type: str,
        params: Dict[str, Any]
    ) -> ActionResult:
        """액션 디스패치"""

        if action_type == "tap_text":
            return await self.tap_by_text(
                text=params.get("text", ""),
                exact=params.get("exact", False),
                clickable_only=params.get("clickable_only", True),
                refresh_ui=False  # 이미 스냅샷에서 갱신됨
            )

        elif action_type == "tap_blog":
            return await self.tap_blog_post(
                index=params.get("index", 0),
                min_text_length=params.get("min_text_length", 15)
            )

        elif action_type == "tap_first":
            return await self.tap_first_match(
                keywords=params.get("keywords", []),
                region=params.get("region", (0.2, 0.8, 0.0, 1.0))
            )

        elif action_type == "tap":
            return await self.tap_at(
                x=params.get("x", 0),
                y=params.get("y", 0)
            )

        elif action_type == "scroll":
            return await self.scroll(
                direction=params.get("direction", "down"),
                distance=params.get("distance", 500),
                speed=params.get("speed", "medium")
            )

        elif action_type == "back":
            return await self.back()

        elif action_type == "wait":
            return await self.wait(params.get("duration_ms", 1000))

        elif action_type == "open_url":
            return await self.open_url(params.get("url", ""))

        elif action_type == "start_app":
            return await self.start_app(
                package=params.get("package", ""),
                activity=params.get("activity")
            )

        else:
            return ActionResult(
                success=False,
                action_type=action_type,
                message=f"Unknown action type: {action_type}"
            )

    def get_action_log(self, context: ExecutionContext) -> str:
        """액션 로그 문자열 생성"""
        lines = [
            f"=== Action: {context.action_type} ===",
            f"Params: {context.params}",
        ]

        if context.snapshot_before:
            lines.append(f"Before: {context.snapshot_before.clickable_count} elements")
            for elem in context.snapshot_before.elements_summary[:5]:
                lines.append(f"  - '{elem['text']}' at {elem['center']}")

        if context.result:
            lines.append(f"Result: {'SUCCESS' if context.result.success else 'FAILED'}")
            lines.append(f"Message: {context.result.message}")

        if context.snapshot_after:
            lines.append(f"After: {context.snapshot_after.clickable_count} elements")

        return "\n".join(lines)
