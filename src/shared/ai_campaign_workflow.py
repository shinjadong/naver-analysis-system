"""
AI Campaign Workflow - AI가 각 스텝을 제어하는 캠페인 워크플로우

네이버의 동적 UI를 처리하기 위해 AI가 매 스텝마다:
1. 현재 UI 상태를 분석
2. 타겟 요소를 동적으로 탐지
3. 휴먼라이크 액션 수행

워크플로우:
1. 네이버 통합검색 → 키워드 검색
2. 검색 결과 스크롤 (내려갔다 올라오기)
3. '블로그' 탭 동적 탐지 및 클릭
4. 타겟 포스트 동적 탐지 및 클릭
5. 포스트 페이지 휴먼라이크 리딩
6. 공유 버튼 클릭 → URL 복사

사용법:
    workflow = AICampaignWorkflow(device_serial="R3CW60BHSAT")
    result = await workflow.execute(
        keyword="cctv가격",
        target_blog_title="CCTV가격 부담된다면?",
        target_blogger="한화비전 키퍼"
    )
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import quote

from .ai_session_controller import AISessionController, StepResult, UIElement

logger = logging.getLogger("ai_campaign")


@dataclass
class WorkflowResult:
    """워크플로우 실행 결과"""
    success: bool
    keyword: str
    target_found: bool = False
    target_title: str = ""

    # 스텝별 결과
    steps: List[StepResult] = field(default_factory=list)

    # 메트릭스
    scroll_count: int = 0
    scroll_depth: float = 0.0
    dwell_time_sec: int = 0
    duration_sec: float = 0.0

    error_message: Optional[str] = None


class AICampaignWorkflow:
    """
    AI-driven 캠페인 워크플로우

    각 스텝에서 AISessionController를 사용하여:
    - UI 상태를 실시간으로 분석
    - 동적으로 요소 탐지
    - 휴먼라이크 액션 수행
    - 페르소나 행동 프로필 적용 (scroll_speed, avg_dwell_time, reading_style)
    """

    def __init__(
        self,
        device_serial: str = None,
        screen_width: int = 1080,
        screen_height: int = 2400
    ):
        self.controller = AISessionController(
            device_serial=device_serial,
            screen_width=screen_width,
            screen_height=screen_height
        )
        self.screen_width = screen_width
        self.screen_height = screen_height

        # 기본 행동 프로필 (페르소나 없을 때 사용)
        self.scroll_speed = 1.0
        self.avg_dwell_time = 120
        self.reading_style = "normal"  # fast, normal, slow
        self.scroll_pattern = "natural"  # linear, natural, random
        self.click_delay_min = 0.5
        self.click_delay_max = 2.0

    def _apply_persona_profile(self, persona) -> None:
        """페르소나 행동 프로필 적용"""
        if persona and hasattr(persona, 'behavior_profile') and persona.behavior_profile:
            profile = persona.behavior_profile
            self.scroll_speed = getattr(profile, 'scroll_speed', 1.0)
            self.avg_dwell_time = getattr(profile, 'avg_dwell_time', 120)
            self.reading_style = getattr(profile, 'reading_style', 'normal')
            self.scroll_pattern = getattr(profile, 'scroll_pattern', 'natural')
            self.click_delay_min = getattr(profile, 'click_delay_min', 0.5)
            self.click_delay_max = getattr(profile, 'click_delay_max', 2.0)

            logger.info(
                f"Persona profile applied: speed={self.scroll_speed}, "
                f"dwell={self.avg_dwell_time}s, style={self.reading_style}"
            )

    def _get_reading_multiplier(self) -> float:
        """reading_style에 따른 시간 배율 반환 (최적화됨)"""
        multipliers = {
            "fast": 0.5,
            "normal": 0.8,
            "slow": 1.0,
            "deep_reader": 1.0  # 기존 1.5 → 1.0으로 최적화
        }
        return multipliers.get(self.reading_style, 0.8)

    def _get_scroll_delay(self) -> float:
        """스크롤 사이 대기 시간 (scroll_speed 적용, 빠른 속도)"""
        base_delay = random.uniform(0.2, 0.4)  # 더 짧은 대기
        return base_delay / self.scroll_speed

    def _get_read_time(self) -> float:
        """읽기 대기 시간 (reading_style 적용, 빠른 속도)"""
        base_time = random.uniform(0.8, 1.5)  # 더 짧은 읽기
        return base_time * self._get_reading_multiplier()

    async def execute(
        self,
        keyword: str,
        target_blog_title: str,
        target_blogger: str = None,
        target_date: str = None,
        target_url: str = None,
        persona = None,
        use_referrer: bool = True,
    ) -> WorkflowResult:
        """
        캠페인 워크플로우 실행

        Args:
            keyword: 검색 키워드
            target_blog_title: 타겟 블로그 포스트 제목
            target_blogger: 블로거 이름 (선택)
            target_date: 작성 날짜 (선택)
            target_url: 폴백용 URL (선택)
            persona: 페르소나 정보 (행동 프로필 포함)
            use_referrer: CDP referrer 설정 사용 여부 (기본 True)

        Returns:
            WorkflowResult
        """
        start_time = datetime.now()
        steps = []
        scroll_count = 0
        error_message = None

        # 페르소나 행동 프로필 적용
        self._apply_persona_profile(persona)

        try:
            # 연결
            if not await self.controller.connect():
                return WorkflowResult(
                    success=False,
                    keyword=keyword,
                    error_message="Failed to connect to device"
                )

            # ===== STEP 1: 네이버 검색 페이지 열기 =====
            logger.info(f"[STEP 1] Opening Naver search for: {keyword}")

            encoded_keyword = quote(keyword)
            search_url = f"https://m.search.naver.com/search.naver?query={encoded_keyword}"

            if not await self.controller.open_url(search_url):
                return WorkflowResult(
                    success=False,
                    keyword=keyword,
                    steps=steps,
                    error_message="Failed to open search URL"
                )

            steps.append(StepResult(
                success=True,
                step_name="open_search",
                action_taken=f"Opened {search_url}"
            ))

            await asyncio.sleep(random.uniform(1.5, 2.5))  # 기존 2.5-4.0 → 1.5-2.5

            # ===== STEP 2: 검색 결과 스크롤 (최적화: 간단히) =====
            logger.info("[STEP 2] Scrolling search results...")

            # 아래로 스크롤 (1-2회만)
            scroll_down_count = random.randint(1, 2)  # 기존 2-4 → 1-2
            for i in range(scroll_down_count):
                await self.controller.humanlike_scroll_down()
                scroll_count += 1
                await asyncio.sleep(random.uniform(0.4, 0.8))  # 기존 0.8-1.5 → 0.4-0.8

            # 다시 최상단으로 (빠르게)
            logger.info("Scrolling back to top...")
            for i in range(scroll_down_count):
                await self.controller.humanlike_scroll_up(distance=400)
                scroll_count += 1
                await asyncio.sleep(random.uniform(0.3, 0.6))  # 기존 0.6-1.0 → 0.3-0.6

            steps.append(StepResult(
                success=True,
                step_name="scroll_search_results",
                action_taken=f"Scrolled {scroll_down_count} down, {scroll_down_count} up"
            ))

            await asyncio.sleep(random.uniform(0.5, 1.0))  # 기존 1.0-1.5 → 0.5-1.0

            # ===== STEP 3: 블로그 탭 찾아서 클릭 =====
            logger.info("[STEP 3] Finding and clicking 'Blog' tab...")

            blog_tab_result = await self._find_and_click_blog_tab()
            steps.append(blog_tab_result)

            if not blog_tab_result.success:
                # 폴백: 직접 블로그 검색 URL로 이동
                logger.warning("Blog tab not found, using direct URL...")
                blog_search_url = f"https://m.search.naver.com/search.naver?where=m_blog&query={encoded_keyword}"
                await self.controller.open_url(blog_search_url)

            await asyncio.sleep(random.uniform(1.2, 2.0))  # 기존 2.0-3.0 → 1.2-2.0

            # ===== STEP 4: 타겟 포스트 찾기 =====
            logger.info(f"[STEP 4] Finding target post: {target_blog_title[:30]}...")

            post_result = await self._find_and_click_target_post(
                target_title=target_blog_title,
                target_blogger=target_blogger,
                target_url=target_url
            )
            steps.append(post_result)
            scroll_count += 5  # 대략적인 스크롤 횟수

            target_found = post_result.success

            if not post_result.success and target_url:
                # 폴백: 직접 URL로 이동 (CDP referrer 적용)
                logger.warning("Target post not found, using direct URL...")
                if use_referrer:
                    search_referrer = (
                        f"https://m.search.naver.com/search.naver"
                        f"?where=m_blog&query={encoded_keyword}"
                    )
                    opened = await self.controller.open_url_with_referrer(
                        target_url, search_referrer
                    )
                else:
                    opened = await self.controller.open_url(target_url)
                target_found = True

            await asyncio.sleep(random.uniform(1.5, 2.5))  # 기존 2.5-4.0 → 1.5-2.5

            # ===== STEP 5: 포스트 휴먼라이크 리딩 =====
            logger.info("[STEP 5] Reading post with humanlike scrolling...")

            reading_result, reading_scrolls = await self._humanlike_post_reading()
            steps.append(reading_result)
            scroll_count += reading_scrolls

            # ===== STEP 6: 공유 버튼 클릭 =====
            logger.info("[STEP 6] Finding and clicking share button...")

            share_result = await self._find_and_click_share_button()
            steps.append(share_result)

            if share_result.success:
                await asyncio.sleep(random.uniform(0.5, 1.0))  # 기존 1.0-1.5 → 0.5-1.0

                # URL 복사 클릭
                copy_result = await self._click_copy_url()
                steps.append(copy_result)

            # 결과 계산
            duration = (datetime.now() - start_time).total_seconds()
            dwell_time = int(duration)
            max_scroll_depth = min(1.0, reading_scrolls / 15)

            logger.info(f"Workflow complete: {dwell_time}s dwell, {scroll_count} scrolls")

            return WorkflowResult(
                success=True,
                keyword=keyword,
                target_found=target_found,
                target_title=target_blog_title,
                steps=steps,
                scroll_count=scroll_count,
                scroll_depth=max_scroll_depth,
                dwell_time_sec=dwell_time,
                duration_sec=duration
            )

        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            return WorkflowResult(
                success=False,
                keyword=keyword,
                steps=steps,
                scroll_count=scroll_count,
                duration_sec=(datetime.now() - start_time).total_seconds(),
                error_message=str(e)
            )

    async def _find_and_click_blog_tab(self) -> StepResult:
        """블로그 탭 동적 탐지 및 클릭"""

        # 먼저 UI 요소가 로드될 때까지 대기
        await self.controller.wait_for_elements(min_elements=3, timeout_sec=8.0)

        # 방법 1: 텍스트로 찾기
        element = await self.controller.find_element_by_text("블로그", refresh=True)

        if element:
            # 탭 영역 확인 (y < 600 정도가 탭 영역)
            if element.center[1] < 600:
                success = await self.controller.humanlike_tap(
                    element.center[0], element.center[1]
                )
                return StepResult(
                    success=success,
                    step_name="click_blog_tab",
                    element_found=element,
                    action_taken=f"Tapped blog tab at ({element.center[0]}, {element.center[1]})"
                )

        # 방법 2: 영역 기반으로 찾기 (탭은 보통 y 400-550 영역)
        element = await self.controller.find_element_in_region(
            y_min=380, y_max=600, text="블로그", refresh=True
        )

        if element:
            success = await self.controller.humanlike_tap(
                element.center[0], element.center[1]
            )
            return StepResult(
                success=success,
                step_name="click_blog_tab",
                element_found=element,
                action_taken=f"Tapped blog tab at ({element.center[0]}, {element.center[1]})"
            )

        # 방법 3: UI 요약 로깅하고 실패
        logger.warning("Blog tab not found. Current UI state:")
        logger.warning(self.controller.get_ui_summary())

        return StepResult(
            success=False,
            step_name="click_blog_tab",
            error_message="Blog tab not found in current UI"
        )

    async def _find_and_click_target_post(
        self,
        target_title: str,
        target_blogger: str = None,
        target_url: str = None,
        max_scrolls: int = 5
    ) -> StepResult:
        """타겟 포스트 동적 탐지 및 클릭"""

        # 먼저 UI 요소가 로드될 때까지 대기
        await self.controller.wait_for_elements(min_elements=3, timeout_sec=8.0)

        for scroll_attempt in range(max_scrolls):
            # 제목의 앞 15자로 검색 (부분 매칭)
            search_text = target_title[:15] if len(target_title) > 15 else target_title

            # 방법 1: 제목으로 찾기
            elements = await self.controller.find_elements_by_text(
                search_text, partial=True, refresh=True
            )

            if elements:
                # 검색 결과 영역에 있는 요소만 (y > 500)
                for element in elements:
                    if element.center[1] > 500:
                        success = await self.controller.humanlike_tap(
                            element.center[0], element.center[1]
                        )
                        return StepResult(
                            success=success,
                            step_name="click_target_post",
                            element_found=element,
                            action_taken=f"Tapped post at ({element.center[0]}, {element.center[1]})"
                        )

            # 방법 2: 블로거 이름으로 찾기
            if target_blogger:
                blogger_elements = await self.controller.find_elements_by_text(
                    target_blogger, partial=True, refresh=False
                )

                for element in blogger_elements:
                    if element.center[1] > 500:
                        # 블로거 이름 위치에서 약간 위로 (제목 영역)
                        tap_y = max(500, element.center[1] - 50)
                        success = await self.controller.humanlike_tap(
                            element.center[0], tap_y
                        )
                        return StepResult(
                            success=success,
                            step_name="click_target_post",
                            element_found=element,
                            action_taken=f"Tapped near blogger name at ({element.center[0]}, {tap_y})"
                        )

            # 스크롤해서 더 찾기
            if scroll_attempt < max_scrolls - 1:
                logger.info(f"Scrolling to find target ({scroll_attempt + 1}/{max_scrolls})...")
                await self.controller.humanlike_scroll_down()
                await asyncio.sleep(random.uniform(0.5, 0.8))  # 기존 1.0-1.5 → 0.5-0.8

        # 마지막 폴백: 첫 번째 검색 결과 클릭
        logger.warning("Target post not found, clicking first result...")
        await self.controller.humanlike_tap(self.screen_width // 2, 700)

        return StepResult(
            success=False,
            step_name="click_target_post",
            error_message="Target post not found, used fallback"
        )

    async def _humanlike_post_reading(self) -> tuple[StepResult, int]:
        """
        포스트 휴먼라이크 리딩 (최적화됨)

        목표: 30-60초 내에 자연스러운 읽기 패턴 구현
        - Phase 1: 아래로 스크롤하며 읽기 (3-5회)
        - Phase 2: 끝까지 빠르게 스크롤 후 공유 버튼 찾기 (2-3회)
        """
        scroll_count = 0
        reading_multiplier = self._get_reading_multiplier()

        try:
            # Phase 1: 콘텐츠 읽기 (자연스럽게)
            logger.info(f"Phase 1: Reading content (style={self.reading_style})...")
            phase1_scrolls = random.randint(3, 5)  # 기존 6-10 → 3-5

            for i in range(phase1_scrolls):
                # 읽는 시간 (최적화된 짧은 시간)
                read_time = self._get_read_time()
                await asyncio.sleep(read_time)

                # 스크롤
                await self.controller.humanlike_scroll_down()
                scroll_count += 1

                # 스크롤 후 짧은 대기
                await asyncio.sleep(self._get_scroll_delay())

                # 가끔 멈춤 (확률 낮춤: 15%)
                if random.random() < 0.15:
                    pause_time = random.uniform(0.8, 1.5)
                    await asyncio.sleep(pause_time)

            # 잠시 대기 (콘텐츠 확인하는 느낌)
            await asyncio.sleep(random.uniform(0.8, 1.5))

            # Phase 2: 공유 버튼 찾기 위해 끝으로
            logger.info("Phase 2: Scrolling to find share button...")
            phase2_scrolls = random.randint(2, 3)  # 기존 3-5 + 4-6 → 2-3

            for _ in range(phase2_scrolls):
                await self.controller.humanlike_scroll_down()
                scroll_count += 1
                await asyncio.sleep(self._get_scroll_delay())

            return StepResult(
                success=True,
                step_name="humanlike_reading",
                action_taken=f"Read post with {scroll_count} scrolls (style={self.reading_style})"
            ), scroll_count

        except Exception as e:
            return StepResult(
                success=False,
                step_name="humanlike_reading",
                error_message=str(e)
            ), scroll_count

    async def _find_and_click_share_button(self) -> StepResult:
        """공유 버튼 동적 탐지 및 클릭"""

        # 방법 1: 텍스트로 찾기
        for text in ["공유", "share", "보내기"]:
            element = await self.controller.find_element_by_text(text, refresh=True)
            if element:
                success = await self.controller.humanlike_tap(
                    element.center[0], element.center[1]
                )
                return StepResult(
                    success=success,
                    step_name="click_share",
                    element_found=element,
                    action_taken=f"Tapped share at ({element.center[0]}, {element.center[1]})"
                )

        # 방법 2: 좌표 기반 폴백 (우하단)
        share_positions = [
            (self.screen_width - 100, self.screen_height - 100),
            (self.screen_width // 2 + 200, self.screen_height - 80),
        ]

        for x, y in share_positions:
            await self.controller.humanlike_tap(x, y)
            await asyncio.sleep(0.5)  # 기존 0.8 → 0.5

            # 공유 메뉴가 열렸는지 확인
            share_menu = await self.controller.find_element_by_text(
                "복사", refresh=True
            )
            if share_menu:
                return StepResult(
                    success=True,
                    step_name="click_share",
                    action_taken=f"Tapped share area at ({x}, {y})"
                )

        return StepResult(
            success=False,
            step_name="click_share",
            error_message="Share button not found"
        )

    async def _click_copy_url(self) -> StepResult:
        """URL 복사 버튼 클릭"""

        for text in ["URL 복사", "링크 복사", "복사"]:
            element = await self.controller.find_element_by_text(text, refresh=True)
            if element:
                success = await self.controller.humanlike_tap(
                    element.center[0], element.center[1]
                )
                return StepResult(
                    success=success,
                    step_name="click_copy_url",
                    element_found=element,
                    action_taken=f"Tapped copy URL at ({element.center[0]}, {element.center[1]})"
                )

        # 폴백: 화면 중앙 상단 탭
        await self.controller.humanlike_tap(
            self.screen_width // 2,
            self.screen_height // 3
        )

        return StepResult(
            success=True,
            step_name="click_copy_url",
            action_taken="Tapped copy area (fallback)"
        )


    async def execute_direct_visit(
        self,
        blog_url: str,
        keyword: str,
        persona=None,
    ) -> WorkflowResult:
        """
        Phase 1 전용: CDP referrer와 함께 블로그 직접 방문

        인덱싱 전(Day 0~3) 참여도 지표 축적용.
        검색 과정 없이 바로 블로그를 방문하되,
        document.referrer를 검색 유입으로 설정한다.

        워크플로우:
        1. CDP로 블로그 열기 (검색 referrer 포함)
        2. 휴먼라이크 리딩 (스크롤 + 체류)
        3. 공유 버튼 클릭

        Args:
            blog_url: 블로그 URL
            keyword: 검색 키워드 (referrer 생성용)
            persona: 페르소나 정보

        Returns:
            WorkflowResult
        """
        start_time = datetime.now()
        steps = []
        scroll_count = 0

        self._apply_persona_profile(persona)

        try:
            if not await self.controller.connect():
                return WorkflowResult(
                    success=False,
                    keyword=keyword,
                    error_message="Failed to connect to device",
                )

            # ===== STEP 1: CDP referrer로 블로그 열기 =====
            encoded_keyword = quote(keyword)
            search_referrer = (
                f"https://m.search.naver.com/search.naver"
                f"?where=m_blog&query={encoded_keyword}"
            )

            logger.info(f"[Phase1] Opening blog with search referrer: {blog_url[:50]}...")
            opened = await self.controller.open_url_with_referrer(
                blog_url, search_referrer
            )

            steps.append(StepResult(
                success=opened,
                step_name="open_blog_with_referrer",
                action_taken=f"CDP referrer navigation to {blog_url[:50]}...",
            ))

            if not opened:
                return WorkflowResult(
                    success=False,
                    keyword=keyword,
                    steps=steps,
                    error_message="Failed to open blog with referrer",
                )

            await asyncio.sleep(random.uniform(1.5, 2.5))

            # ===== STEP 2: 휴먼라이크 리딩 =====
            logger.info("[Phase1] Reading post...")
            reading_result, reading_scrolls = await self._humanlike_post_reading()
            steps.append(reading_result)
            scroll_count += reading_scrolls

            # ===== STEP 3: 공유 버튼 클릭 (선택적) =====
            if random.random() < 0.3:  # 30% 확률
                logger.info("[Phase1] Clicking share button...")
                share_result = await self._find_and_click_share_button()
                steps.append(share_result)

            duration = (datetime.now() - start_time).total_seconds()

            return WorkflowResult(
                success=True,
                keyword=keyword,
                target_found=True,
                target_title=blog_url,
                steps=steps,
                scroll_count=scroll_count,
                scroll_depth=min(1.0, reading_scrolls / 15),
                dwell_time_sec=int(duration),
                duration_sec=duration,
            )

        except Exception as e:
            logger.error(f"Phase1 direct visit failed: {e}")
            return WorkflowResult(
                success=False,
                keyword=keyword,
                steps=steps,
                scroll_count=scroll_count,
                duration_sec=(datetime.now() - start_time).total_seconds(),
                error_message=str(e),
            )


# =========================================================================
# Factory function
# =========================================================================

def create_ai_workflow(device_serial: str = None) -> AICampaignWorkflow:
    """AICampaignWorkflow 인스턴스 생성"""
    return AICampaignWorkflow(device_serial=device_serial)
