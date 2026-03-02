"""
Interest Profiler

관심사 프로필 생성:
- 키워드 기반 관심사 추출
- 관심사 가중치 계산
- 검색 행동 패턴 생성
"""

import logging
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, time
from enum import Enum

logger = logging.getLogger(__name__)


class InterestIntensity(Enum):
    """관심사 강도"""
    HIGH = "high"          # 핵심 관심사
    MEDIUM = "medium"      # 일반 관심사
    LOW = "low"           # 부수적 관심사


class SearchIntention(Enum):
    """검색 의도"""
    INFORMATIONAL = "informational"   # 정보 탐색
    NAVIGATIONAL = "navigational"     # 특정 사이트 접근
    TRANSACTIONAL = "transactional"   # 구매/거래 목적
    COMMERCIAL = "commercial"          # 상업적 조사


@dataclass
class InterestItem:
    """개별 관심사"""
    topic: str
    intensity: InterestIntensity = InterestIntensity.MEDIUM
    keywords: List[str] = field(default_factory=list)
    weight: float = 1.0
    search_frequency: int = 5  # 주간 검색 횟수
    preferred_time: Optional[List[int]] = None  # 선호 검색 시간대

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "intensity": self.intensity.value,
            "keywords": self.keywords,
            "weight": self.weight,
            "search_frequency": self.search_frequency,
            "preferred_time": self.preferred_time
        }


@dataclass
class SearchBehavior:
    """검색 행동 패턴"""
    # 검색 스타일
    avg_keywords_per_query: float = 2.5   # 평균 검색어 길이
    refinement_rate: float = 0.3           # 검색어 수정 비율
    uses_autocomplete: float = 0.6         # 자동완성 사용률

    # 결과 상호작용
    avg_results_viewed: int = 5            # 평균 결과 확인 수
    click_through_rate: float = 0.4        # 클릭률
    bounce_rate: float = 0.3               # 이탈률

    # 시간 패턴
    session_duration_min: int = 5          # 세션 시간 (분)
    searches_per_session: int = 3          # 세션당 검색 수

    def to_dict(self) -> dict:
        return {
            "avg_keywords_per_query": self.avg_keywords_per_query,
            "refinement_rate": self.refinement_rate,
            "uses_autocomplete": self.uses_autocomplete,
            "avg_results_viewed": self.avg_results_viewed,
            "click_through_rate": self.click_through_rate,
            "bounce_rate": self.bounce_rate,
            "session_duration_min": self.session_duration_min,
            "searches_per_session": self.searches_per_session
        }


@dataclass
class InterestProfile:
    """관심사 프로필"""
    profile_id: str
    archetype: str

    # 관심사 목록
    interests: List[InterestItem] = field(default_factory=list)

    # 검색 행동
    search_behavior: SearchBehavior = field(default_factory=SearchBehavior)

    # 검색 의도 분포
    intention_distribution: Dict[SearchIntention, float] = field(
        default_factory=lambda: {
            SearchIntention.INFORMATIONAL: 0.5,
            SearchIntention.NAVIGATIONAL: 0.2,
            SearchIntention.TRANSACTIONAL: 0.2,
            SearchIntention.COMMERCIAL: 0.1,
        }
    )

    # 활동 시간대
    active_hours: List[int] = field(default_factory=lambda: list(range(9, 22)))
    peak_hours: List[int] = field(default_factory=lambda: [12, 19, 21])

    # 메타데이터
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def primary_interests(self) -> List[InterestItem]:
        """핵심 관심사"""
        return [i for i in self.interests if i.intensity == InterestIntensity.HIGH]

    @property
    def interest_topics(self) -> List[str]:
        """관심사 주제 목록"""
        return [i.topic for i in self.interests]

    @property
    def all_keywords(self) -> List[str]:
        """전체 키워드 목록"""
        keywords = []
        for interest in self.interests:
            keywords.extend(interest.keywords)
        return keywords

    def get_weighted_keyword(self) -> Optional[str]:
        """가중치 기반 키워드 선택"""
        if not self.interests:
            return None

        # 관심사별 가중치로 선택
        weights = [i.weight * (1.5 if i.intensity == InterestIntensity.HIGH else 1.0)
                   for i in self.interests]
        total = sum(weights)

        if total == 0:
            return None

        rand = random.random() * total
        cumulative = 0.0

        for interest, weight in zip(self.interests, weights):
            cumulative += weight
            if rand <= cumulative and interest.keywords:
                return random.choice(interest.keywords)

        return None

    def get_search_intention(self) -> SearchIntention:
        """검색 의도 선택"""
        rand = random.random()
        cumulative = 0.0

        for intention, prob in self.intention_distribution.items():
            cumulative += prob
            if rand <= cumulative:
                return intention

        return SearchIntention.INFORMATIONAL

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "archetype": self.archetype,
            "interests": [i.to_dict() for i in self.interests],
            "search_behavior": self.search_behavior.to_dict(),
            "intention_distribution": {
                k.value: v for k, v in self.intention_distribution.items()
            },
            "active_hours": self.active_hours,
            "peak_hours": self.peak_hours,
            "created_at": self.created_at.isoformat(),
        }


class InterestProfiler:
    """관심사 프로파일러"""

    # 원형별 기본 설정
    ARCHETYPE_CONFIGS = {
        "explorer": {
            "search_behavior": {
                "avg_keywords_per_query": 2.0,
                "refinement_rate": 0.4,
                "uses_autocomplete": 0.7,
                "avg_results_viewed": 7,
                "click_through_rate": 0.5,
                "searches_per_session": 5
            },
            "intention_distribution": {
                SearchIntention.INFORMATIONAL: 0.6,
                SearchIntention.NAVIGATIONAL: 0.2,
                SearchIntention.TRANSACTIONAL: 0.1,
                SearchIntention.COMMERCIAL: 0.1,
            }
        },
        "researcher": {
            "search_behavior": {
                "avg_keywords_per_query": 3.5,
                "refinement_rate": 0.5,
                "uses_autocomplete": 0.4,
                "avg_results_viewed": 10,
                "click_through_rate": 0.3,
                "searches_per_session": 8
            },
            "intention_distribution": {
                SearchIntention.INFORMATIONAL: 0.7,
                SearchIntention.NAVIGATIONAL: 0.15,
                SearchIntention.TRANSACTIONAL: 0.05,
                SearchIntention.COMMERCIAL: 0.1,
            }
        },
        "casual": {
            "search_behavior": {
                "avg_keywords_per_query": 2.0,
                "refinement_rate": 0.2,
                "uses_autocomplete": 0.8,
                "avg_results_viewed": 3,
                "click_through_rate": 0.6,
                "searches_per_session": 2
            },
            "intention_distribution": {
                SearchIntention.INFORMATIONAL: 0.4,
                SearchIntention.NAVIGATIONAL: 0.3,
                SearchIntention.TRANSACTIONAL: 0.2,
                SearchIntention.COMMERCIAL: 0.1,
            }
        },
        "shopper": {
            "search_behavior": {
                "avg_keywords_per_query": 3.0,
                "refinement_rate": 0.4,
                "uses_autocomplete": 0.6,
                "avg_results_viewed": 6,
                "click_through_rate": 0.5,
                "searches_per_session": 4
            },
            "intention_distribution": {
                SearchIntention.INFORMATIONAL: 0.2,
                SearchIntention.NAVIGATIONAL: 0.1,
                SearchIntention.TRANSACTIONAL: 0.5,
                SearchIntention.COMMERCIAL: 0.2,
            }
        },
        "local": {
            "search_behavior": {
                "avg_keywords_per_query": 2.5,
                "refinement_rate": 0.3,
                "uses_autocomplete": 0.7,
                "avg_results_viewed": 5,
                "click_through_rate": 0.5,
                "searches_per_session": 3
            },
            "intention_distribution": {
                SearchIntention.INFORMATIONAL: 0.4,
                SearchIntention.NAVIGATIONAL: 0.3,
                SearchIntention.TRANSACTIONAL: 0.2,
                SearchIntention.COMMERCIAL: 0.1,
            }
        },
        "professional": {
            "search_behavior": {
                "avg_keywords_per_query": 3.0,
                "refinement_rate": 0.5,
                "uses_autocomplete": 0.5,
                "avg_results_viewed": 8,
                "click_through_rate": 0.4,
                "searches_per_session": 5
            },
            "intention_distribution": {
                SearchIntention.INFORMATIONAL: 0.5,
                SearchIntention.NAVIGATIONAL: 0.25,
                SearchIntention.TRANSACTIONAL: 0.1,
                SearchIntention.COMMERCIAL: 0.15,
            }
        },
    }

    # 시간대별 활동 패턴
    TIME_PATTERNS = {
        "morning_person": {
            "active_hours": list(range(6, 20)),
            "peak_hours": [7, 8, 9, 12]
        },
        "night_owl": {
            "active_hours": list(range(11, 24)),
            "peak_hours": [20, 21, 22, 23]
        },
        "office_worker": {
            "active_hours": list(range(9, 23)),
            "peak_hours": [12, 13, 19, 20]
        },
        "flexible": {
            "active_hours": list(range(8, 23)),
            "peak_hours": [10, 14, 19, 21]
        }
    }

    def __init__(self):
        self._profile_counter = 0

    async def create_profile(
        self,
        interests: List[str],
        keywords: List[str],
        archetype: str = "casual",
        time_pattern: Optional[str] = None
    ) -> InterestProfile:
        """
        관심사 프로필 생성

        Args:
            interests: 관심사 주제 목록
            keywords: 키워드 목록
            archetype: 페르소나 원형
            time_pattern: 시간 패턴 (없으면 랜덤)

        Returns:
            InterestProfile: 생성된 프로필
        """
        self._profile_counter += 1
        profile_id = f"ip_{self._profile_counter:04d}"

        # 원형 설정 가져오기
        config = self.ARCHETYPE_CONFIGS.get(archetype, self.ARCHETYPE_CONFIGS["casual"])

        # 검색 행동 생성
        sb_config = config["search_behavior"]
        search_behavior = SearchBehavior(
            avg_keywords_per_query=sb_config["avg_keywords_per_query"] + random.uniform(-0.3, 0.3),
            refinement_rate=sb_config["refinement_rate"] + random.uniform(-0.1, 0.1),
            uses_autocomplete=sb_config["uses_autocomplete"] + random.uniform(-0.1, 0.1),
            avg_results_viewed=sb_config["avg_results_viewed"] + random.randint(-1, 2),
            click_through_rate=sb_config["click_through_rate"] + random.uniform(-0.1, 0.1),
            searches_per_session=sb_config["searches_per_session"] + random.randint(-1, 1)
        )

        # 관심사 항목 생성
        interest_items = self._create_interest_items(interests, keywords)

        # 시간 패턴 선택
        if time_pattern is None:
            time_pattern = random.choice(list(self.TIME_PATTERNS.keys()))
        time_config = self.TIME_PATTERNS.get(time_pattern, self.TIME_PATTERNS["flexible"])

        # 프로필 생성
        profile = InterestProfile(
            profile_id=profile_id,
            archetype=archetype,
            interests=interest_items,
            search_behavior=search_behavior,
            intention_distribution=config["intention_distribution"].copy(),
            active_hours=time_config["active_hours"],
            peak_hours=time_config["peak_hours"],
            metadata={
                "time_pattern": time_pattern,
                "keyword_count": len(keywords)
            }
        )

        logger.debug(f"Created interest profile: {profile_id} ({archetype})")
        return profile

    def _create_interest_items(
        self,
        interests: List[str],
        keywords: List[str]
    ) -> List[InterestItem]:
        """관심사 항목 생성"""
        items = []

        # 관심사별 키워드 매핑
        interest_keywords: Dict[str, List[str]] = {i: [] for i in interests}

        for keyword in keywords:
            keyword_lower = keyword.lower()
            for interest in interests:
                if interest.lower() in keyword_lower:
                    interest_keywords[interest].append(keyword)
                    break
            else:
                # 매칭되지 않은 키워드는 첫 번째 관심사에 할당
                if interests and keywords:
                    interest_keywords[interests[0]].append(keyword)

        # 관심사 항목 생성
        for i, interest in enumerate(interests):
            kw_list = interest_keywords.get(interest, [])

            # 강도 결정 (상위 관심사일수록 높음)
            if i < len(interests) * 0.2:
                intensity = InterestIntensity.HIGH
            elif i < len(interests) * 0.5:
                intensity = InterestIntensity.MEDIUM
            else:
                intensity = InterestIntensity.LOW

            # 가중치 계산
            weight = 1.0 + (len(interests) - i) * 0.1

            items.append(InterestItem(
                topic=interest,
                intensity=intensity,
                keywords=kw_list[:20],  # 상위 20개
                weight=weight,
                search_frequency=random.randint(3, 10),
                preferred_time=random.sample(range(9, 23), 3)
            ))

        return items

    async def update_profile(
        self,
        profile: InterestProfile,
        new_keywords: List[str],
        search_history: Optional[List[Dict]] = None
    ) -> InterestProfile:
        """프로필 업데이트"""
        # 새 키워드를 관심사에 분배
        for keyword in new_keywords:
            added = False
            for interest in profile.interests:
                if interest.topic.lower() in keyword.lower():
                    if keyword not in interest.keywords:
                        interest.keywords.append(keyword)
                    added = True
                    break

            if not added and profile.interests:
                # 첫 번째 관심사에 추가
                profile.interests[0].keywords.append(keyword)

        # 검색 히스토리 기반 행동 패턴 조정
        if search_history:
            profile.search_behavior = self._analyze_search_history(
                profile.search_behavior, search_history
            )

        profile.metadata["last_updated"] = datetime.now().isoformat()
        return profile

    def _analyze_search_history(
        self,
        current: SearchBehavior,
        history: List[Dict]
    ) -> SearchBehavior:
        """검색 히스토리 분석"""
        if not history:
            return current

        # 평균 검색어 길이
        query_lengths = [len(h.get("query", "").split()) for h in history]
        if query_lengths:
            current.avg_keywords_per_query = sum(query_lengths) / len(query_lengths)

        # 결과 확인 수
        results_viewed = [h.get("results_viewed", 0) for h in history]
        if results_viewed:
            current.avg_results_viewed = int(sum(results_viewed) / len(results_viewed))

        return current

    def generate_search_sequence(
        self,
        profile: InterestProfile,
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """검색 시퀀스 생성"""
        sequence = []

        for _ in range(count):
            keyword = profile.get_weighted_keyword()
            if not keyword:
                continue

            intention = profile.get_search_intention()

            # 검색어 변형
            query = self._vary_query(keyword, profile.search_behavior)

            sequence.append({
                "query": query,
                "intention": intention.value,
                "expected_dwell_time": random.randint(30, 180),
                "expected_clicks": random.randint(1, profile.search_behavior.avg_results_viewed),
            })

        return sequence

    def _vary_query(self, keyword: str, behavior: SearchBehavior) -> str:
        """검색어 변형"""
        # 기본 키워드 반환 (변형 없음)
        if random.random() > behavior.refinement_rate:
            return keyword

        # 수식어 추가
        modifiers = ["추천", "후기", "비교", "가격", "방법", "정리"]

        if random.random() > 0.5:
            return f"{keyword} {random.choice(modifiers)}"

        return keyword
