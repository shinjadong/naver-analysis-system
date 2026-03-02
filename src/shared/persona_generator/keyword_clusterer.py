"""
Keyword Clusterer

키워드 클러스터링:
- 관심사/주제별 그룹화
- 유사도 기반 클러스터링
- 카테고리 자동 분류
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict
from enum import Enum

from .keyword_parser import KeywordEntry, KeywordType

logger = logging.getLogger(__name__)


class ClusterCategory(Enum):
    """클러스터 카테고리"""
    FOOD = "food"                  # 맛집/음식
    TRAVEL = "travel"              # 여행
    BEAUTY = "beauty"              # 뷰티/패션
    TECH = "tech"                  # IT/테크
    FINANCE = "finance"            # 금융/투자
    HEALTH = "health"              # 건강/운동
    EDUCATION = "education"        # 교육
    LIFESTYLE = "lifestyle"        # 라이프스타일
    ENTERTAINMENT = "entertainment"  # 엔터테인먼트
    SHOPPING = "shopping"          # 쇼핑
    LOCAL = "local"                # 지역
    OTHER = "other"                # 기타


@dataclass
class KeywordCluster:
    """키워드 클러스터"""
    cluster_id: str
    name: str
    category: ClusterCategory
    keywords: List[KeywordEntry] = field(default_factory=list)
    center_keyword: Optional[str] = None
    total_volume: int = 0
    avg_difficulty: float = 0.0
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        self._update_stats()

    def add_keyword(self, entry: KeywordEntry) -> None:
        """키워드 추가"""
        self.keywords.append(entry)
        self._update_stats()

    def _update_stats(self) -> None:
        """통계 업데이트"""
        if not self.keywords:
            return

        self.total_volume = sum(k.volume for k in self.keywords)
        difficulties = [k.difficulty for k in self.keywords if k.difficulty > 0]
        self.avg_difficulty = sum(difficulties) / len(difficulties) if difficulties else 0

        # 센터 키워드 (검색량 최고)
        if not self.center_keyword:
            sorted_kw = sorted(self.keywords, key=lambda k: k.volume, reverse=True)
            self.center_keyword = sorted_kw[0].keyword if sorted_kw else None

    @property
    def keyword_list(self) -> List[str]:
        """키워드 문자열 리스트"""
        return [k.keyword for k in self.keywords]

    @property
    def size(self) -> int:
        """클러스터 크기"""
        return len(self.keywords)


class KeywordClusterer:
    """키워드 클러스터러"""

    # 카테고리별 키워드 패턴
    CATEGORY_PATTERNS = {
        ClusterCategory.FOOD: [
            r'맛집|음식|식당|카페|레스토랑|배달|푸드|먹방|요리|레시피',
            r'밥|면|고기|해산물|디저트|커피|빵|술',
        ],
        ClusterCategory.TRAVEL: [
            r'여행|숙소|호텔|펜션|리조트|관광|투어',
            r'비행기|항공|티켓|공항|해외|국내여행',
        ],
        ClusterCategory.BEAUTY: [
            r'화장품|메이크업|스킨케어|뷰티|패션|옷|코디',
            r'헤어|네일|피부|다이어트|성형',
        ],
        ClusterCategory.TECH: [
            r'IT|프로그래밍|개발|코딩|AI|인공지능|앱|소프트웨어',
            r'컴퓨터|노트북|스마트폰|전자기기|테크',
        ],
        ClusterCategory.FINANCE: [
            r'주식|투자|재테크|부동산|금융|은행|보험',
            r'연금|적금|대출|카드|세금',
        ],
        ClusterCategory.HEALTH: [
            r'건강|운동|헬스|요가|필라테스|다이어트',
            r'병원|의료|약|영양제|건강식품',
        ],
        ClusterCategory.EDUCATION: [
            r'교육|학원|과외|인강|자격증|시험|공부',
            r'영어|수학|대학|취업|면접',
        ],
        ClusterCategory.LIFESTYLE: [
            r'인테리어|가구|가전|집|이사|청소',
            r'결혼|육아|반려동물|취미|자동차',
        ],
        ClusterCategory.ENTERTAINMENT: [
            r'영화|드라마|예능|음악|게임|웹툰',
            r'콘서트|공연|축제|연예인',
        ],
        ClusterCategory.SHOPPING: [
            r'쇼핑|할인|세일|쿠폰|구매|가격|비교',
            r'리뷰|후기|추천|베스트|랭킹',
        ],
    }

    # 지역 패턴
    LOCAL_REGIONS = [
        '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
        '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주',
        '강남', '홍대', '이태원', '명동', '잠실', '신촌', '건대', '압구정',
        '해운대', '광안리', '센텀', '동성로', '성심당',
    ]

    def __init__(self):
        self._compiled_patterns = {}
        for cat, patterns in self.CATEGORY_PATTERNS.items():
            self._compiled_patterns[cat] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    async def cluster_keywords(
        self,
        keywords: List[KeywordEntry],
        min_cluster_size: int = 3,
        max_clusters: int = 20
    ) -> List[KeywordCluster]:
        """
        키워드 클러스터링

        Args:
            keywords: 키워드 목록
            min_cluster_size: 최소 클러스터 크기
            max_clusters: 최대 클러스터 수

        Returns:
            List[KeywordCluster]: 클러스터 목록
        """
        # 1단계: 카테고리 분류
        categorized = self._categorize_keywords(keywords)

        # 2단계: 지역별 서브 클러스터
        with_local = self._split_by_region(categorized)

        # 3단계: 유사도 기반 세분화
        refined = self._refine_clusters(with_local)

        # 4단계: 필터링 및 정렬
        filtered = [
            c for c in refined
            if c.size >= min_cluster_size
        ]

        # 검색량 기준 정렬
        sorted_clusters = sorted(
            filtered,
            key=lambda c: c.total_volume,
            reverse=True
        )[:max_clusters]

        logger.info(
            f"Created {len(sorted_clusters)} clusters from {len(keywords)} keywords"
        )

        return sorted_clusters

    def _categorize_keywords(
        self,
        keywords: List[KeywordEntry]
    ) -> Dict[ClusterCategory, List[KeywordEntry]]:
        """카테고리별 분류"""
        categorized = defaultdict(list)

        for kw in keywords:
            category = self._detect_category(kw.keyword)
            if kw.category:
                # 기존 카테고리 사용
                try:
                    category = ClusterCategory(kw.category.lower())
                except ValueError:
                    pass
            categorized[category].append(kw)

        return dict(categorized)

    def _detect_category(self, keyword: str) -> ClusterCategory:
        """키워드 카테고리 감지"""
        for cat, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(keyword):
                    return cat
        return ClusterCategory.OTHER

    def _split_by_region(
        self,
        categorized: Dict[ClusterCategory, List[KeywordEntry]]
    ) -> List[KeywordCluster]:
        """지역별 서브 클러스터 생성"""
        clusters = []
        cluster_id = 0

        for category, keywords in categorized.items():
            # 지역별 그룹화
            regional: Dict[str, List[KeywordEntry]] = defaultdict(list)
            non_regional: List[KeywordEntry] = []

            for kw in keywords:
                region = self._detect_region(kw.keyword)
                if region:
                    regional[region].append(kw)
                else:
                    non_regional.append(kw)

            # 지역별 클러스터
            for region, region_kws in regional.items():
                cluster_id += 1
                clusters.append(KeywordCluster(
                    cluster_id=f"c_{cluster_id:03d}",
                    name=f"{region} {category.value}",
                    category=category,
                    keywords=region_kws,
                    metadata={"region": region}
                ))

            # 비지역 클러스터
            if non_regional:
                cluster_id += 1
                clusters.append(KeywordCluster(
                    cluster_id=f"c_{cluster_id:03d}",
                    name=f"일반 {category.value}",
                    category=category,
                    keywords=non_regional
                ))

        return clusters

    def _detect_region(self, keyword: str) -> Optional[str]:
        """지역 감지"""
        for region in self.LOCAL_REGIONS:
            if region in keyword:
                return region
        return None

    def _refine_clusters(
        self,
        clusters: List[KeywordCluster]
    ) -> List[KeywordCluster]:
        """클러스터 세분화"""
        refined = []

        for cluster in clusters:
            if cluster.size <= 10:
                refined.append(cluster)
                continue

            # 큰 클러스터는 세분화
            sub_clusters = self._split_large_cluster(cluster)
            refined.extend(sub_clusters)

        return refined

    def _split_large_cluster(
        self,
        cluster: KeywordCluster
    ) -> List[KeywordCluster]:
        """큰 클러스터 분할"""
        # 간단한 접두어 기반 분할
        prefix_groups: Dict[str, List[KeywordEntry]] = defaultdict(list)

        for kw in cluster.keywords:
            # 첫 단어를 접두어로 사용
            prefix = kw.keyword.split()[0] if kw.keyword.split() else kw.keyword[:2]
            prefix_groups[prefix].append(kw)

        sub_clusters = []
        idx = 0

        for prefix, kws in prefix_groups.items():
            if len(kws) >= 3:
                idx += 1
                sub_clusters.append(KeywordCluster(
                    cluster_id=f"{cluster.cluster_id}_{idx}",
                    name=f"{cluster.name} - {prefix}",
                    category=cluster.category,
                    keywords=kws,
                    metadata={**cluster.metadata, "sub_prefix": prefix}
                ))

        # 너무 작은 그룹은 원래 클러스터로
        if not sub_clusters:
            return [cluster]

        return sub_clusters

    def merge_small_clusters(
        self,
        clusters: List[KeywordCluster],
        min_size: int = 5
    ) -> List[KeywordCluster]:
        """작은 클러스터 병합"""
        large = [c for c in clusters if c.size >= min_size]
        small = [c for c in clusters if c.size < min_size]

        # 카테고리별로 작은 클러스터 병합
        merged_by_cat: Dict[ClusterCategory, KeywordCluster] = {}

        for c in small:
            if c.category not in merged_by_cat:
                merged_by_cat[c.category] = KeywordCluster(
                    cluster_id=f"merged_{c.category.value}",
                    name=f"기타 {c.category.value}",
                    category=c.category,
                    keywords=[]
                )
            merged_by_cat[c.category].keywords.extend(c.keywords)

        return large + list(merged_by_cat.values())

    def get_cluster_for_persona(
        self,
        clusters: List[KeywordCluster],
        persona_interests: List[str]
    ) -> List[KeywordCluster]:
        """페르소나 관심사에 맞는 클러스터 선택"""
        matching = []

        for cluster in clusters:
            score = 0
            for interest in persona_interests:
                # 클러스터 이름 또는 키워드에 관심사 포함
                if interest.lower() in cluster.name.lower():
                    score += 2
                for kw in cluster.keywords:
                    if interest.lower() in kw.keyword.lower():
                        score += 1

            if score > 0:
                cluster.metadata["match_score"] = score
                matching.append(cluster)

        return sorted(matching, key=lambda c: c.metadata.get("match_score", 0), reverse=True)
