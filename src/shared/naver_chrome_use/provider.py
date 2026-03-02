"""
NaverChromeUseProvider - 브라우저 기반 네이버 자동화 제공자

Chrome/Samsung Internet 등 브라우저를 통한 네이버 접속 자동화
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from enum import Enum
from urllib.parse import quote

logger = logging.getLogger("naver_chrome_use")


class BrowserType(Enum):
    """지원 브라우저 유형"""
    CHROME = "chrome"
    SAMSUNG_INTERNET = "samsung_internet"
    EDGE = "edge"


@dataclass
class BrowserConfig:
    """브라우저 설정"""
    package_name: str
    main_activity: str
    name: str
    priority: int = 0
    ui_config: Dict = field(default_factory=dict)

    @property
    def has_bottom_nav(self) -> bool:
        """하단 네비게이션 바 유무"""
        return self.ui_config.get("has_bottom_nav", False)

    def get_back_button(self) -> Tuple[int, int]:
        """뒤로가기 버튼 좌표"""
        return tuple(self.ui_config.get("back_button", (60, 130)))

    def get_share_button(self) -> Optional[Tuple[int, int]]:
        """공유 버튼 좌표 (없으면 None)"""
        coords = self.ui_config.get("share_button")
        return tuple(coords) if coords else None


# 브라우저 기본 설정
BROWSER_CONFIGS = {
    BrowserType.CHROME: BrowserConfig(
        package_name="com.android.chrome",
        main_activity="com.google.android.apps.chrome.Main",
        name="Chrome",
        priority=1,
        ui_config={
            "back_button": [60, 130],
            "share_button": [980, 130],
            "address_bar": [540, 80],
            "tab_button": [920, 80],
            "menu_button": [1020, 80],
            "has_bottom_nav": False,
        }
    ),
    BrowserType.SAMSUNG_INTERNET: BrowserConfig(
        package_name="com.sec.android.app.sbrowser",
        main_activity=".SBrowserMainActivity",
        name="Samsung Internet",
        priority=2,
        ui_config={
            "back_button": [120, 2300],
            "share_button": None,  # 메뉴 내부
            "address_bar": [540, 130],
            "home_button": [540, 2300],
            "tab_button": [900, 2300],
            "menu_button": [980, 2300],
            "has_bottom_nav": True,
        }
    ),
    BrowserType.EDGE: BrowserConfig(
        package_name="com.microsoft.emmx",
        main_activity=".MainActivity",
        name="Microsoft Edge",
        priority=3,
        ui_config={
            "back_button": [60, 130],
            "share_button": [980, 130],
            "address_bar": [540, 80],
            "has_bottom_nav": False,
        }
    ),
}


@dataclass
class AdbIntent:
    """ADB Intent 명령"""
    action: str
    package: str
    data: Optional[str] = None
    extras: Dict[str, str] = field(default_factory=dict)

    def to_command(self) -> str:
        """ADB 명령어로 변환"""
        parts = ["am", "start"]

        if self.action:
            parts.extend(["-a", self.action])

        if self.data:
            parts.extend(["-d", f"'{self.data}'"])

        for key, value in self.extras.items():
            if isinstance(value, bool):
                parts.extend(["--ez", key, str(value).lower()])
            else:
                parts.extend(["--es", key, value])

        parts.append(self.package)

        return " ".join(parts)


class NaverChromeUseProvider:
    """
    NaverChromeUse 제공자

    Chrome 브라우저를 통한 네이버 접속 자동화를 위한 설정 및 명령어 제공

    Usage:
        provider = NaverChromeUseProvider()

        # 사용 가능한 브라우저 확인
        browser = await provider.get_available_browser(adb)

        # 브라우저 카드 로드
        card = await provider.load_browser_card(browser.package_name)

        # URL 열기 명령 생성
        intent = provider.create_open_url_intent(
            "https://m.naver.com",
            browser.package_name
        )
    """

    def __init__(self, cards_path: Optional[str] = None):
        """
        Args:
            cards_path: 브라우저 카드 파일 경로 (기본: 모듈 내 cards 디렉토리)
        """
        if cards_path:
            self.cards_path = Path(cards_path)
        else:
            self.cards_path = Path(__file__).parent / "cards"

        self._browser_configs = BROWSER_CONFIGS.copy()
        self._card_cache: Dict[str, str] = {}

    # ========================================
    # 브라우저 선택
    # ========================================

    def get_browser_config(self, browser_type: BrowserType) -> BrowserConfig:
        """브라우저 타입으로 설정 조회"""
        return self._browser_configs.get(browser_type)

    def get_browser_by_package(self, package_name: str) -> Optional[BrowserConfig]:
        """패키지명으로 브라우저 설정 조회"""
        for config in self._browser_configs.values():
            if config.package_name == package_name:
                return config
        return None

    async def get_available_browser(self, adb_tools) -> BrowserConfig:
        """
        설치된 브라우저 중 우선순위가 높은 것 반환

        Args:
            adb_tools: EnhancedAdbTools 인스턴스

        Returns:
            BrowserConfig
        """
        # 우선순위 순으로 정렬
        sorted_browsers = sorted(
            self._browser_configs.values(),
            key=lambda x: x.priority
        )

        for config in sorted_browsers:
            result = await adb_tools.shell(
                f"pm list packages | grep {config.package_name}"
            )
            if config.package_name in result.output:
                return config

        raise RuntimeError("지원되는 브라우저가 설치되어 있지 않습니다")

    def get_all_browsers(self) -> List[BrowserConfig]:
        """모든 지원 브라우저 목록"""
        return sorted(
            self._browser_configs.values(),
            key=lambda x: x.priority
        )

    # ========================================
    # 브라우저 카드
    # ========================================

    def load_browser_card(self, package_name: str) -> str:
        """
        브라우저 카드 로드

        Args:
            package_name: 브라우저 패키지명

        Returns:
            카드 내용 (마크다운)
        """
        # 캐시 확인
        if package_name in self._card_cache:
            return self._card_cache[package_name]

        # 카드 파일 매핑
        card_files = {
            "com.android.chrome": "chrome_naver.md",
            "com.sec.android.app.sbrowser": "samsung_naver.md",
            "com.microsoft.emmx": "edge_naver.md",
        }

        card_file = card_files.get(package_name)
        if not card_file:
            return ""

        card_path = self.cards_path / card_file
        if not card_path.exists():
            return ""

        content = card_path.read_text(encoding="utf-8")
        self._card_cache[package_name] = content

        return content

    # ========================================
    # ADB Intent 생성
    # ========================================

    def create_open_url_intent(
        self,
        url: str,
        package_name: str = "com.android.chrome"
    ) -> AdbIntent:
        """
        URL 열기 Intent 생성

        Args:
            url: 열 URL
            package_name: 브라우저 패키지명

        Returns:
            AdbIntent
        """
        return AdbIntent(
            action="android.intent.action.VIEW",
            package=package_name,
            data=url
        )

    def create_incognito_url_intent(
        self,
        url: str,
        package_name: str = "com.android.chrome"
    ) -> AdbIntent:
        """
        시크릿 모드 URL 열기 Intent (Chrome 전용)

        Args:
            url: 열 URL
            package_name: 브라우저 패키지명

        Returns:
            AdbIntent
        """
        return AdbIntent(
            action="android.intent.action.VIEW",
            package=package_name,
            data=url,
            extras={
                "create_new_tab": True,
                "incognito": True,
            }
        )

    def create_launch_browser_intent(
        self,
        package_name: str = "com.android.chrome"
    ) -> AdbIntent:
        """
        브라우저 실행 Intent

        Args:
            package_name: 브라우저 패키지명

        Returns:
            AdbIntent
        """
        config = self.get_browser_by_package(package_name)
        if not config:
            raise ValueError(f"Unknown browser package: {package_name}")

        return AdbIntent(
            action="android.intent.action.MAIN",
            package=f"{package_name}/{config.main_activity}"
        )

    # ========================================
    # 네이버 특화 Intent
    # ========================================

    def create_naver_search_intent(
        self,
        query: str,
        category: str = "all",
        package_name: str = "com.android.chrome"
    ) -> AdbIntent:
        """
        네이버 검색 Intent

        Args:
            query: 검색어
            category: 검색 카테고리 (all, blog, news, image, shopping)
            package_name: 브라우저 패키지명

        Returns:
            AdbIntent
        """
        from urllib.parse import quote

        encoded_query = quote(query)

        if category == "shopping":
            url = f"https://msearch.shopping.naver.com/search/all?query={encoded_query}"
        elif category == "all":
            url = f"https://search.naver.com/search.naver?query={encoded_query}"
        else:
            url = f"https://search.naver.com/search.naver?where={category}&query={encoded_query}"

        return self.create_open_url_intent(url, package_name)

    def create_naver_home_intent(
        self,
        package_name: str = "com.android.chrome"
    ) -> AdbIntent:
        """네이버 홈 Intent"""
        return self.create_open_url_intent("https://m.naver.com", package_name)

    def create_naver_blog_intent(
        self,
        package_name: str = "com.android.chrome"
    ) -> AdbIntent:
        """네이버 블로그 홈 Intent"""
        return self.create_open_url_intent("https://m.blog.naver.com", package_name)

    # ========================================
    # CDP Referrer 네비게이션
    # ========================================

    async def navigate_blog_with_search_referrer(
        self,
        blog_url: str,
        search_query: str,
        device_serial: str = None,
        cdp_port: int = 9222,
    ) -> bool:
        """
        CDP를 사용하여 검색 referrer와 함께 블로그 방문

        about:blank → Page.navigate(blog_url, referrer=search_url) 방식.
        검색 페이지 실제 로딩 없이 document.referrer를 설정한다.

        Args:
            blog_url: 방문할 블로그 URL
            search_query: 검색 키워드 (referrer URL 생성에 사용)
            device_serial: ADB 디바이스 시리얼
            cdp_port: CDP 포트 (기본 9222)

        Returns:
            성공 여부
        """
        from .cdp_client import CdpClient

        # 모바일 검색 referrer URL 생성
        encoded_query = quote(search_query)
        search_referrer = (
            f"https://m.search.naver.com/search.naver"
            f"?where=m_blog&query={encoded_query}"
        )

        # 블로그 URL을 모바일 형식으로 변환
        mobile_blog_url = blog_url.replace(
            "blog.naver.com", "m.blog.naver.com"
        ) if "m.blog.naver.com" not in blog_url else blog_url

        cdp = CdpClient(device_serial=device_serial, cdp_port=cdp_port)

        try:
            if not await cdp.connect():
                logger.warning("CDP connect failed, falling back to direct navigation")
                return False

            success = await cdp.navigate_with_referrer(
                url=mobile_blog_url,
                referrer=search_referrer,
            )

            if success:
                ref = await cdp.get_document_referrer()
                logger.info(f"Blog opened with referrer: {ref}")

            return success

        except Exception as e:
            logger.error(f"CDP referrer navigation failed: {e}")
            return False

        finally:
            await cdp.disconnect()

    # ========================================
    # UI 좌표 헬퍼
    # ========================================

    def get_ui_coordinates(
        self,
        package_name: str,
        element: str,
        screen_width: int = 1080,
        screen_height: int = 2400
    ) -> Tuple[int, int]:
        """
        UI 요소 좌표 조회 (해상도 변환 적용)

        Args:
            package_name: 브라우저 패키지명
            element: 요소 이름 (back_button, share_button 등)
            screen_width: 현재 화면 너비
            screen_height: 현재 화면 높이

        Returns:
            (x, y) 좌표
        """
        config = self.get_browser_by_package(package_name)
        if not config:
            raise ValueError(f"Unknown browser package: {package_name}")

        base_coords = config.ui_config.get(element)
        if not base_coords:
            raise ValueError(f"Unknown UI element: {element}")

        # 기준 해상도 (1080x2400)에서 변환
        base_width, base_height = 1080, 2400

        x = int(base_coords[0] * (screen_width / base_width))
        y = int(base_coords[1] * (screen_height / base_height))

        return (x, y)

    # ========================================
    # 네이버 공통 UI 좌표
    # ========================================

    def get_naver_search_box(
        self,
        screen_width: int = 1080,
        screen_height: int = 2400
    ) -> Tuple[int, int]:
        """네이버 홈 검색창 좌표"""
        base_x, base_y = 540, 180
        x = int(base_x * (screen_width / 1080))
        y = int(base_y * (screen_height / 2400))
        return (x, y)

    def get_naver_first_result(
        self,
        screen_width: int = 1080,
        screen_height: int = 2400
    ) -> Tuple[int, int]:
        """네이버 검색 결과 첫 번째 항목 좌표"""
        base_x, base_y = 540, 700
        x = int(base_x * (screen_width / 1080))
        y = int(base_y * (screen_height / 2400))
        return (x, y)

    def get_naver_search_tabs(
        self,
        screen_width: int = 1080,
        screen_height: int = 2400
    ) -> Dict[str, Tuple[int, int]]:
        """네이버 검색 결과 탭 좌표"""
        base_y = 350
        y = int(base_y * (screen_height / 2400))

        tabs = {
            "blog": (int(650 * (screen_width / 1080)), y),
            "news": (int(450 * (screen_width / 1080)), y),
            "image": (int(250 * (screen_width / 1080)), y),
        }
        return tabs
