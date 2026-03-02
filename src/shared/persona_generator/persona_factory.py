"""
Persona Factory

페르소나 자동 생성:
- 클러스터 기반 페르소나 생성
- 행동 프로필 생성
- ANDROID_ID 자동 할당
"""

import logging
import random
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

from .keyword_clusterer import KeywordCluster, ClusterCategory
from .interest_profiler import InterestProfile, InterestProfiler

logger = logging.getLogger(__name__)


class PersonaArchetype(Enum):
    """페르소나 원형"""
    EXPLORER = "explorer"          # 탐험가 - 다양한 검색
    RESEARCHER = "researcher"      # 연구자 - 깊은 탐색
    CASUAL = "casual"              # 캐주얼 - 가벼운 브라우징
    SHOPPER = "shopper"            # 쇼퍼 - 구매 목적
    LOCAL = "local"                # 로컬 - 지역 정보
    PROFESSIONAL = "professional"  # 전문가 - 업무 관련


@dataclass
class BehaviorProfile:
    """행동 프로필"""
    # 읽기 패턴
    reading_speed: str = "medium"  # slow, medium, fast
    scroll_style: str = "smooth"   # smooth, jerky, precise
    avg_dwell_time: int = 90       # 초

    # 상호작용
    interaction_frequency: float = 0.5  # 0-1
    click_tendency: float = 0.6         # 0-1
    back_button_usage: float = 0.3      # 0-1

    # 시간 패턴
    active_hours: List[int] = field(default_factory=lambda: list(range(9, 22)))
    peak_hours: List[int] = field(default_factory=lambda: [12, 13, 19, 20, 21])

    # 세션 패턴
    session_duration_min: int = 5    # 분
    session_duration_max: int = 30   # 분
    sessions_per_day: int = 3

    def to_dict(self) -> dict:
        return {
            "reading_speed": self.reading_speed,
            "scroll_style": self.scroll_style,
            "avg_dwell_time": self.avg_dwell_time,
            "interaction_frequency": self.interaction_frequency,
            "click_tendency": self.click_tendency,
            "active_hours": self.active_hours,
            "peak_hours": self.peak_hours,
            "session_duration_min": self.session_duration_min,
            "session_duration_max": self.session_duration_max,
            "sessions_per_day": self.sessions_per_day,
        }


@dataclass
class GeneratedPersona:
    """생성된 페르소나"""
    persona_id: str
    name: str
    android_id: str

    # 프로필
    archetype: PersonaArchetype
    interests: List[str]
    keywords: List[str]
    behavior_profile: BehaviorProfile
    interest_profile: InterestProfile

    # 할당된 클러스터
    assigned_clusters: List[str] = field(default_factory=list)

    # 메타데이터
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "persona_id": self.persona_id,
            "name": self.name,
            "android_id": self.android_id,
            "archetype": self.archetype.value,
            "interests": self.interests,
            "keywords": self.keywords,
            "behavior_profile": self.behavior_profile.to_dict(),
            "assigned_clusters": self.assigned_clusters,
            "created_at": self.created_at.isoformat(),
        }


class PersonaFactory:
    """페르소나 팩토리"""

    # 한국 이름 생성용
    SURNAMES = ['김', '이', '박', '최', '정', '강', '조', '윤', '장', '임']
    GIVEN_NAMES = [
        '민준', '서준', '예준', '도윤', '시우', '하준', '지호', '준서',
        '서연', '서윤', '지우', '서현', '민서', '하은', '하윤', '윤서',
        '지민', '수민', '지현', '예진', '현우', '민재', '준영', '성민'
    ]

    # 원형별 행동 특성
    ARCHETYPE_BEHAVIORS = {
        PersonaArchetype.EXPLORER: {
            "reading_speed": "fast",
            "scroll_style": "smooth",
            "avg_dwell_time": 60,
            "interaction_frequency": 0.7,
            "sessions_per_day": 5
        },
        PersonaArchetype.RESEARCHER: {
            "reading_speed": "slow",
            "scroll_style": "precise",
            "avg_dwell_time": 180,
            "interaction_frequency": 0.4,
            "sessions_per_day": 2
        },
        PersonaArchetype.CASUAL: {
            "reading_speed": "medium",
            "scroll_style": "jerky",
            "avg_dwell_time": 45,
            "interaction_frequency": 0.3,
            "sessions_per_day": 4
        },
        PersonaArchetype.SHOPPER: {
            "reading_speed": "medium",
            "scroll_style": "smooth",
            "avg_dwell_time": 120,
            "interaction_frequency": 0.8,
            "sessions_per_day": 3
        },
        PersonaArchetype.LOCAL: {
            "reading_speed": "medium",
            "scroll_style": "smooth",
            "avg_dwell_time": 90,
            "interaction_frequency": 0.6,
            "sessions_per_day": 3
        },
        PersonaArchetype.PROFESSIONAL: {
            "reading_speed": "fast",
            "scroll_style": "precise",
            "avg_dwell_time": 150,
            "interaction_frequency": 0.5,
            "sessions_per_day": 2
        }
    }

    def __init__(self):
        self.interest_profiler = InterestProfiler()
        self._used_android_ids: set = set()

    async def generate_personas(
        self,
        clusters: List[KeywordCluster],
        count: int = 10,
        distribution: Optional[Dict[PersonaArchetype, float]] = None
    ) -> List[GeneratedPersona]:
        """
        페르소나 생성

        Args:
            clusters: 키워드 클러스터 목록
            count: 생성할 페르소나 수
            distribution: 원형별 분포 (없으면 균등)

        Returns:
            List[GeneratedPersona]: 생성된 페르소나 목록
        """
        personas = []

        # 원형 분포 결정
        if distribution is None:
            distribution = {arch: 1.0 / len(PersonaArchetype) for arch in PersonaArchetype}

        # 클러스터 분배
        cluster_assignments = self._distribute_clusters(clusters, count)

        for i in range(count):
            # 원형 선택
            archetype = self._select_archetype(distribution)

            # 할당할 클러스터
            assigned = cluster_assignments.get(i, [])

            # 관심사 추출
            interests = self._extract_interests(assigned)

            # 키워드 추출
            keywords = self._extract_keywords(assigned)

            # 행동 프로필 생성
            behavior = self._generate_behavior_profile(archetype)

            # 관심사 프로필 생성
            interest_profile = await self.interest_profiler.create_profile(
                interests=interests,
                keywords=keywords,
                archetype=archetype.value
            )

            # 페르소나 생성
            persona = GeneratedPersona(
                persona_id=f"persona_{uuid.uuid4().hex[:8]}",
                name=self._generate_name(),
                android_id=self._generate_android_id(),
                archetype=archetype,
                interests=interests,
                keywords=keywords[:50],  # 상위 50개
                behavior_profile=behavior,
                interest_profile=interest_profile,
                assigned_clusters=[c.cluster_id for c in assigned],
                metadata={
                    "total_keywords": len(keywords),
                    "cluster_count": len(assigned),
                    "total_volume": sum(c.total_volume for c in assigned)
                }
            )

            personas.append(persona)

        logger.info(f"Generated {len(personas)} personas from {len(clusters)} clusters")
        return personas

    def _distribute_clusters(
        self,
        clusters: List[KeywordCluster],
        persona_count: int
    ) -> Dict[int, List[KeywordCluster]]:
        """클러스터를 페르소나에 분배"""
        distribution: Dict[int, List[KeywordCluster]] = {i: [] for i in range(persona_count)}

        # 검색량 기준 정렬
        sorted_clusters = sorted(clusters, key=lambda c: c.total_volume, reverse=True)

        # 라운드 로빈 방식으로 분배
        for i, cluster in enumerate(sorted_clusters):
            persona_idx = i % persona_count
            distribution[persona_idx].append(cluster)

        return distribution

    def _select_archetype(
        self,
        distribution: Dict[PersonaArchetype, float]
    ) -> PersonaArchetype:
        """원형 선택 (가중 랜덤)"""
        total = sum(distribution.values())
        rand = random.random() * total

        cumulative = 0.0
        for archetype, weight in distribution.items():
            cumulative += weight
            if rand <= cumulative:
                return archetype

        return PersonaArchetype.CASUAL

    def _extract_interests(self, clusters: List[KeywordCluster]) -> List[str]:
        """클러스터에서 관심사 추출"""
        interests = set()

        for cluster in clusters:
            # 카테고리 추가
            interests.add(cluster.category.value)

            # 클러스터 이름에서 추출
            name_parts = cluster.name.split()
            interests.update(p for p in name_parts if len(p) > 1)

            # 센터 키워드
            if cluster.center_keyword:
                interests.add(cluster.center_keyword)

        return list(interests)[:10]

    def _extract_keywords(self, clusters: List[KeywordCluster]) -> List[str]:
        """클러스터에서 키워드 추출"""
        all_keywords = []

        for cluster in clusters:
            for kw in cluster.keywords:
                all_keywords.append((kw.keyword, kw.volume))

        # 검색량 기준 정렬
        sorted_kw = sorted(all_keywords, key=lambda x: x[1], reverse=True)

        return [kw for kw, _ in sorted_kw]

    def _generate_behavior_profile(
        self,
        archetype: PersonaArchetype
    ) -> BehaviorProfile:
        """행동 프로필 생성"""
        base = self.ARCHETYPE_BEHAVIORS.get(archetype, {})

        # 약간의 랜덤 변형 추가
        return BehaviorProfile(
            reading_speed=base.get("reading_speed", "medium"),
            scroll_style=base.get("scroll_style", "smooth"),
            avg_dwell_time=base.get("avg_dwell_time", 90) + random.randint(-15, 15),
            interaction_frequency=base.get("interaction_frequency", 0.5) + random.uniform(-0.1, 0.1),
            click_tendency=0.5 + random.uniform(-0.2, 0.2),
            back_button_usage=0.3 + random.uniform(-0.1, 0.1),
            active_hours=list(range(
                random.randint(7, 10),
                random.randint(20, 24)
            )),
            peak_hours=random.sample(range(9, 23), 3),
            session_duration_min=random.randint(3, 10),
            session_duration_max=random.randint(20, 45),
            sessions_per_day=base.get("sessions_per_day", 3) + random.randint(-1, 1)
        )

    def _generate_name(self) -> str:
        """한국 이름 생성"""
        surname = random.choice(self.SURNAMES)
        given = random.choice(self.GIVEN_NAMES)
        return f"{surname}{given}"

    def _generate_android_id(self) -> str:
        """고유한 ANDROID_ID 생성"""
        while True:
            android_id = ''.join(
                random.choices('0123456789abcdef', k=16)
            )
            if android_id not in self._used_android_ids:
                self._used_android_ids.add(android_id)
                return android_id

    async def create_single_persona(
        self,
        name: str,
        interests: List[str],
        keywords: List[str],
        archetype: PersonaArchetype = PersonaArchetype.CASUAL
    ) -> GeneratedPersona:
        """단일 페르소나 직접 생성"""
        behavior = self._generate_behavior_profile(archetype)
        interest_profile = await self.interest_profiler.create_profile(
            interests=interests,
            keywords=keywords,
            archetype=archetype.value
        )

        return GeneratedPersona(
            persona_id=f"persona_{uuid.uuid4().hex[:8]}",
            name=name,
            android_id=self._generate_android_id(),
            archetype=archetype,
            interests=interests,
            keywords=keywords,
            behavior_profile=behavior,
            interest_profile=interest_profile
        )
