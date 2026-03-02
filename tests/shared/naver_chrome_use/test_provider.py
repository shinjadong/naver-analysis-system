"""
NaverChromeUseProvider 단위 테스트

테스트 항목:
- 브라우저 설정 조회
- ADB Intent 생성
- 브라우저 카드 로드
- URL 빌더
"""

import pytest
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from shared.naver_chrome_use import (
    NaverChromeUseProvider,
    BrowserConfig,
    NaverUrlBuilder,
)
from shared.naver_chrome_use.provider import BrowserType, AdbIntent
from shared.naver_chrome_use.url_builder import NaverSearchCategory


class TestBrowserConfig:
    """브라우저 설정 테스트"""

    def setup_method(self):
        self.provider = NaverChromeUseProvider()

    def test_get_chrome_config(self):
        """Chrome 브라우저 설정 조회"""
        config = self.provider.get_browser_config(BrowserType.CHROME)

        assert config is not None
        assert config.package_name == "com.android.chrome"
        assert config.priority == 1

    def test_get_samsung_config(self):
        """Samsung Internet 설정 조회"""
        config = self.provider.get_browser_config(BrowserType.SAMSUNG_INTERNET)

        assert config is not None
        assert config.package_name == "com.sec.android.app.sbrowser"
        assert config.has_bottom_nav == True

    def test_get_browser_by_package(self):
        """패키지명으로 브라우저 설정 조회"""
        config = self.provider.get_browser_by_package("com.android.chrome")

        assert config is not None
        assert config.name == "Chrome"

    def test_unknown_package_returns_none(self):
        """알 수 없는 패키지는 None 반환"""
        config = self.provider.get_browser_by_package("com.unknown.browser")

        assert config is None

    def test_get_all_browsers(self):
        """모든 브라우저 목록 조회"""
        browsers = self.provider.get_all_browsers()

        assert len(browsers) >= 2
        assert browsers[0].priority <= browsers[1].priority


class TestAdbIntent:
    """ADB Intent 생성 테스트"""

    def setup_method(self):
        self.provider = NaverChromeUseProvider()

    def test_create_open_url_intent(self):
        """URL 열기 Intent 생성"""
        intent = self.provider.create_open_url_intent(
            "https://m.naver.com",
            "com.android.chrome"
        )

        assert intent.action == "android.intent.action.VIEW"
        assert intent.data == "https://m.naver.com"
        assert intent.package == "com.android.chrome"

    def test_intent_to_command(self):
        """Intent를 ADB 명령어로 변환"""
        intent = self.provider.create_open_url_intent(
            "https://m.naver.com",
            "com.android.chrome"
        )

        command = intent.to_command()

        assert "am start" in command
        assert "android.intent.action.VIEW" in command
        assert "https://m.naver.com" in command
        assert "com.android.chrome" in command

    def test_create_incognito_intent(self):
        """시크릿 모드 Intent 생성"""
        intent = self.provider.create_incognito_url_intent(
            "https://m.naver.com",
            "com.android.chrome"
        )

        assert "create_new_tab" in intent.extras
        assert "incognito" in intent.extras

    def test_create_naver_search_intent(self):
        """네이버 검색 Intent 생성"""
        intent = self.provider.create_naver_search_intent(
            "파이썬",
            category="blog"
        )

        assert "where=blog" in intent.data
        assert "%ED%8C%8C%EC%9D%B4%EC%8D%AC" in intent.data  # URL 인코딩된 '파이썬'

    def test_create_naver_shopping_search_intent(self):
        """네이버 쇼핑 검색 Intent 생성"""
        intent = self.provider.create_naver_search_intent(
            "노트북",
            category="shopping"
        )

        assert "msearch.shopping.naver.com" in intent.data


class TestBrowserCard:
    """브라우저 카드 테스트"""

    def setup_method(self):
        self.provider = NaverChromeUseProvider()

    def test_load_chrome_card(self):
        """Chrome 브라우저 카드 로드"""
        card = self.provider.load_browser_card("com.android.chrome")

        assert len(card) > 0
        assert "Chrome" in card
        assert "com.android.chrome" in card

    def test_load_samsung_card(self):
        """Samsung Internet 브라우저 카드 로드"""
        card = self.provider.load_browser_card("com.sec.android.app.sbrowser")

        assert len(card) > 0
        assert "Samsung" in card

    def test_unknown_browser_returns_empty(self):
        """알 수 없는 브라우저는 빈 문자열 반환"""
        card = self.provider.load_browser_card("com.unknown.browser")

        assert card == ""


class TestUICoordinates:
    """UI 좌표 테스트"""

    def setup_method(self):
        self.provider = NaverChromeUseProvider()

    def test_get_chrome_back_button(self):
        """Chrome 뒤로가기 버튼 좌표"""
        x, y = self.provider.get_ui_coordinates(
            "com.android.chrome",
            "back_button"
        )

        assert x == 60
        assert y == 130

    def test_get_samsung_back_button(self):
        """Samsung Internet 뒤로가기 버튼 좌표"""
        x, y = self.provider.get_ui_coordinates(
            "com.sec.android.app.sbrowser",
            "back_button"
        )

        assert x == 120
        assert y == 2300

    def test_coordinate_scaling(self):
        """해상도별 좌표 변환"""
        # 1440x3200 해상도
        x, y = self.provider.get_ui_coordinates(
            "com.android.chrome",
            "back_button",
            screen_width=1440,
            screen_height=3200
        )

        # 기준 (60, 130)에서 1.33배 스케일
        assert x == 80  # 60 * 1.33
        assert y == 173  # 130 * 1.33

    def test_get_naver_search_box(self):
        """네이버 검색창 좌표"""
        x, y = self.provider.get_naver_search_box()

        assert x == 540
        assert y == 180

    def test_get_naver_search_tabs(self):
        """네이버 검색 탭 좌표"""
        tabs = self.provider.get_naver_search_tabs()

        assert "blog" in tabs
        assert "news" in tabs
        assert tabs["blog"][0] == 650


class TestNaverUrlBuilder:
    """NaverUrlBuilder 테스트"""

    def setup_method(self):
        self.builder = NaverUrlBuilder()

    def test_search_all(self):
        """통합 검색 URL 생성"""
        result = self.builder.search("파이썬")

        assert "search.naver.com" in result.url
        assert "query=" in result.url

    def test_search_blog(self):
        """블로그 검색 URL 생성"""
        result = self.builder.search("파이썬", NaverSearchCategory.BLOG)

        assert "where=blog" in result.url
        assert result.category == "blog"

    def test_search_shopping(self):
        """쇼핑 검색 URL 생성"""
        result = self.builder.search("노트북", NaverSearchCategory.SHOPPING)

        assert "msearch.shopping.naver.com" in result.url
        assert result.category == "shopping"

    def test_home_url(self):
        """홈 URL 생성"""
        result = self.builder.home()

        assert result.url == "https://m.naver.com"

    def test_blog_home_url(self):
        """블로그 홈 URL 생성"""
        result = self.builder.blog_home()

        assert result.url == "https://m.blog.naver.com"

    def test_blog_post_url(self):
        """블로그 포스트 URL 생성"""
        result = self.builder.blog_post("myblog", "123456")

        assert "myblog" in result.url
        assert "123456" in result.url

    def test_is_naver_url(self):
        """네이버 URL 판별"""
        assert NaverUrlBuilder.is_naver_url("https://m.naver.com") == True
        assert NaverUrlBuilder.is_naver_url("https://google.com") == False

    def test_extract_domain(self):
        """도메인 추출"""
        domain = NaverUrlBuilder.extract_domain("https://m.blog.naver.com/post/123")

        assert domain == "m.blog.naver.com"

    def test_get_search_category_from_url(self):
        """URL에서 검색 카테고리 추출"""
        category = NaverUrlBuilder.get_search_category_from_url(
            "https://search.naver.com/search.naver?where=blog&query=test"
        )

        assert category == "blog"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
