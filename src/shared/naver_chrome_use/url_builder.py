"""
NaverUrlBuilder - 네이버 URL 생성 헬퍼

네이버 서비스별 URL을 생성하는 유틸리티 클래스
"""

from urllib.parse import quote, urlencode
from typing import Optional, Dict
from dataclasses import dataclass
from enum import Enum


class NaverSearchCategory(Enum):
    """네이버 검색 카테고리"""
    ALL = "all"           # 통합검색
    BLOG = "blog"         # 블로그
    NEWS = "news"         # 뉴스
    IMAGE = "image"       # 이미지
    VIDEO = "video"       # 동영상
    SHOPPING = "shopping" # 쇼핑
    CAFE = "cafe"         # 카페
    KIN = "kin"           # 지식iN
    LOCAL = "local"       # 지역


@dataclass
class NaverUrl:
    """네이버 URL 정보"""
    url: str
    domain: str
    category: str
    params: Dict[str, str]


class NaverUrlBuilder:
    """
    네이버 URL 생성 헬퍼

    Usage:
        builder = NaverUrlBuilder()

        # 검색 URL
        url = builder.search("파이썬", category=NaverSearchCategory.BLOG)

        # 서비스 URL
        url = builder.blog_home()
        url = builder.shopping_home()
    """

    # 기본 도메인
    BASE_HOME = "https://m.naver.com"
    BASE_SEARCH = "https://search.naver.com/search.naver"
    BASE_BLOG = "https://m.blog.naver.com"
    BASE_CAFE = "https://m.cafe.naver.com"
    BASE_SHOPPING = "https://msearch.shopping.naver.com"
    BASE_NEWS = "https://m.news.naver.com"
    BASE_MAP = "https://m.map.naver.com"

    # 검색 카테고리별 where 파라미터
    SEARCH_WHERE_MAP = {
        NaverSearchCategory.ALL: None,
        NaverSearchCategory.BLOG: "blog",
        NaverSearchCategory.NEWS: "news",
        NaverSearchCategory.IMAGE: "image",
        NaverSearchCategory.VIDEO: "video",
        NaverSearchCategory.CAFE: "cafe",
        NaverSearchCategory.KIN: "kin",
        NaverSearchCategory.LOCAL: "local",
    }

    def __init__(self):
        pass

    # ========================================
    # 검색 URL 생성
    # ========================================

    def search(
        self,
        query: str,
        category: NaverSearchCategory = NaverSearchCategory.ALL,
        extra_params: Optional[Dict[str, str]] = None
    ) -> NaverUrl:
        """
        네이버 검색 URL 생성

        Args:
            query: 검색어
            category: 검색 카테고리 (blog, news, image 등)
            extra_params: 추가 파라미터

        Returns:
            NaverUrl 객체
        """
        # 쇼핑은 별도 도메인
        if category == NaverSearchCategory.SHOPPING:
            return self.shopping_search(query, extra_params)

        encoded_query = quote(query)
        params = {"query": encoded_query}

        # where 파라미터 추가
        where_value = self.SEARCH_WHERE_MAP.get(category)
        if where_value:
            params["where"] = where_value

        # 추가 파라미터 병합
        if extra_params:
            params.update(extra_params)

        query_string = urlencode(params)
        url = f"{self.BASE_SEARCH}?{query_string}"

        return NaverUrl(
            url=url,
            domain="search.naver.com",
            category=category.value,
            params=params
        )

    def shopping_search(
        self,
        query: str,
        extra_params: Optional[Dict[str, str]] = None
    ) -> NaverUrl:
        """네이버 쇼핑 검색 URL"""
        encoded_query = quote(query)
        params = {"query": encoded_query}

        if extra_params:
            params.update(extra_params)

        query_string = urlencode(params)
        url = f"{self.BASE_SHOPPING}/search/all?{query_string}"

        return NaverUrl(
            url=url,
            domain="msearch.shopping.naver.com",
            category="shopping",
            params=params
        )

    # ========================================
    # 서비스 홈 URL
    # ========================================

    def home(self) -> NaverUrl:
        """네이버 모바일 홈"""
        return NaverUrl(
            url=self.BASE_HOME,
            domain="m.naver.com",
            category="home",
            params={}
        )

    def blog_home(self) -> NaverUrl:
        """네이버 블로그 홈"""
        return NaverUrl(
            url=self.BASE_BLOG,
            domain="m.blog.naver.com",
            category="blog",
            params={}
        )

    def cafe_home(self) -> NaverUrl:
        """네이버 카페 홈"""
        return NaverUrl(
            url=self.BASE_CAFE,
            domain="m.cafe.naver.com",
            category="cafe",
            params={}
        )

    def shopping_home(self) -> NaverUrl:
        """네이버 쇼핑 홈"""
        return NaverUrl(
            url=self.BASE_SHOPPING,
            domain="msearch.shopping.naver.com",
            category="shopping",
            params={}
        )

    def news_home(self) -> NaverUrl:
        """네이버 뉴스 홈"""
        return NaverUrl(
            url=self.BASE_NEWS,
            domain="m.news.naver.com",
            category="news",
            params={}
        )

    def map_home(self) -> NaverUrl:
        """네이버 지도 홈"""
        return NaverUrl(
            url=self.BASE_MAP,
            domain="m.map.naver.com",
            category="map",
            params={}
        )

    # ========================================
    # 특수 URL
    # ========================================

    def blog_post(self, blog_id: str, log_no: str) -> NaverUrl:
        """블로그 포스트 URL"""
        url = f"{self.BASE_BLOG}/{blog_id}/{log_no}"
        return NaverUrl(
            url=url,
            domain="m.blog.naver.com",
            category="blog_post",
            params={"blog_id": blog_id, "log_no": log_no}
        )

    def cafe_article(self, cafe_id: str, article_id: str) -> NaverUrl:
        """카페 게시글 URL"""
        url = f"{self.BASE_CAFE}/{cafe_id}/{article_id}"
        return NaverUrl(
            url=url,
            domain="m.cafe.naver.com",
            category="cafe_article",
            params={"cafe_id": cafe_id, "article_id": article_id}
        )

    def shopping_product(self, product_id: str) -> NaverUrl:
        """쇼핑 상품 URL"""
        url = f"{self.BASE_SHOPPING}/product/{product_id}"
        return NaverUrl(
            url=url,
            domain="msearch.shopping.naver.com",
            category="shopping_product",
            params={"product_id": product_id}
        )

    def map_search(self, query: str) -> NaverUrl:
        """지도 검색 URL"""
        encoded_query = quote(query)
        url = f"{self.BASE_MAP}/search/{encoded_query}"
        return NaverUrl(
            url=url,
            domain="m.map.naver.com",
            category="map_search",
            params={"query": encoded_query}
        )

    # ========================================
    # 유틸리티 메서드
    # ========================================

    @staticmethod
    def is_naver_url(url: str) -> bool:
        """네이버 URL인지 확인"""
        naver_domains = [
            "naver.com",
            "naver.net",
            "pstatic.net",
        ]
        return any(domain in url for domain in naver_domains)

    @staticmethod
    def extract_domain(url: str) -> str:
        """URL에서 도메인 추출"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc

    @staticmethod
    def get_search_category_from_url(url: str) -> Optional[str]:
        """URL에서 검색 카테고리 추출"""
        from urllib.parse import urlparse, parse_qs

        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        if "where" in query_params:
            return query_params["where"][0]

        # 쇼핑 도메인 체크
        if "shopping.naver.com" in url:
            return "shopping"

        return None
