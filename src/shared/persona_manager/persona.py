"""
Persona Data Structures - 가상 사용자 페르소나 데이터 구조

Author: Naver AI Evolution System
Created: 2025-12-15
"""

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class PersonaStatus(Enum):
    """페르소나 상태"""
    ACTIVE = "active"           # 활성 (사용 가능)
    IN_USE = "in_use"           # 현재 사용 중
    COOLING_DOWN = "cooling"    # 쿨다운 중
    SUSPENDED = "suspended"     # 일시 중지
    RETIRED = "retired"         # 은퇴 (더 이상 사용 안 함)


class ReadingStyle(Enum):
    """읽기 스타일"""
    SKIMMER = "skimmer"         # 훑어보기 (빠름, 낮은 스크롤 깊이)
    DEEP_READER = "deep_reader"  # 정독 (느림, 높은 스크롤 깊이)
    SCANNER = "scanner"          # 스캔 (중간, 특정 영역 집중)


@dataclass
class BehaviorProfile:
    """
    행동 특성 프로필 - 페르소나별 고유한 행동 패턴

    각 페르소나는 일관된 행동 패턴을 가지며,
    이를 통해 네이버가 "같은 사람"으로 인식하도록 합니다.
    """

    # === 스크롤 패턴 ===
    scroll_speed: float = 1.0           # 0.5 (느림) ~ 2.0 (빠름)
    scroll_depth_preference: float = 0.7  # 0.3 ~ 1.0 (얼마나 끝까지 읽는지)
    scroll_pause_frequency: float = 0.2   # 0.1 ~ 0.4 (멈춤 빈도)

    # === 읽기 패턴 ===
    avg_dwell_time: int = 120            # 평균 체류시간 (초) 60~300
    reading_style: str = "scanner"       # "skimmer", "deep_reader", "scanner"

    # === 탭 패턴 ===
    tap_accuracy: float = 0.92           # 0.85 ~ 0.98 (정확도)
    tap_speed: float = 1.0               # 0.8 ~ 1.2 (반응 속도)

    # === 세션 패턴 ===
    preferred_session_length: int = 8    # 선호 세션 길이 (분) 3~15
    pages_per_session: int = 4           # 세션당 페이지 수 2~8

    # === 시간 패턴 ===
    active_hours: List[int] = field(default_factory=lambda: list(range(9, 22)))
    active_days: List[int] = field(default_factory=lambda: list(range(5)))  # 월~금

    # === 관심사 ===
    preferred_categories: List[str] = field(default_factory=list)  # ["tech", "travel"]
    search_patterns: List[str] = field(default_factory=list)       # 자주 쓰는 검색 패턴

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "scroll_speed": self.scroll_speed,
            "scroll_depth_preference": self.scroll_depth_preference,
            "scroll_pause_frequency": self.scroll_pause_frequency,
            "avg_dwell_time": self.avg_dwell_time,
            "reading_style": self.reading_style,
            "tap_accuracy": self.tap_accuracy,
            "tap_speed": self.tap_speed,
            "preferred_session_length": self.preferred_session_length,
            "pages_per_session": self.pages_per_session,
            "active_hours": self.active_hours,
            "active_days": self.active_days,
            "preferred_categories": self.preferred_categories,
            "search_patterns": self.search_patterns,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BehaviorProfile":
        """딕셔너리에서 생성"""
        return cls(
            scroll_speed=data.get("scroll_speed", 1.0),
            scroll_depth_preference=data.get("scroll_depth_preference", 0.7),
            scroll_pause_frequency=data.get("scroll_pause_frequency", 0.2),
            avg_dwell_time=data.get("avg_dwell_time", 120),
            reading_style=data.get("reading_style", "scanner"),
            tap_accuracy=data.get("tap_accuracy", 0.92),
            tap_speed=data.get("tap_speed", 1.0),
            preferred_session_length=data.get("preferred_session_length", 8),
            pages_per_session=data.get("pages_per_session", 4),
            active_hours=data.get("active_hours", list(range(9, 22))),
            active_days=data.get("active_days", list(range(5))),
            preferred_categories=data.get("preferred_categories", []),
            search_patterns=data.get("search_patterns", []),
        )

    @classmethod
    def generate_random(cls) -> "BehaviorProfile":
        """랜덤 프로필 생성"""
        reading_style = random.choice(["skimmer", "deep_reader", "scanner"])

        # 읽기 스타일에 따른 파라미터 조정
        if reading_style == "skimmer":
            scroll_speed = random.uniform(1.2, 1.8)
            scroll_depth = random.uniform(0.3, 0.5)
            dwell_time = random.randint(60, 120)
        elif reading_style == "deep_reader":
            scroll_speed = random.uniform(0.6, 0.9)
            scroll_depth = random.uniform(0.8, 1.0)
            dwell_time = random.randint(180, 300)
        else:  # scanner
            scroll_speed = random.uniform(0.9, 1.3)
            scroll_depth = random.uniform(0.5, 0.8)
            dwell_time = random.randint(90, 180)

        return cls(
            scroll_speed=scroll_speed,
            scroll_depth_preference=scroll_depth,
            scroll_pause_frequency=random.uniform(0.1, 0.35),
            avg_dwell_time=dwell_time,
            reading_style=reading_style,
            tap_accuracy=random.uniform(0.88, 0.96),
            tap_speed=random.uniform(0.85, 1.15),
            preferred_session_length=random.randint(5, 12),
            pages_per_session=random.randint(3, 6),
            active_hours=sorted(random.sample(range(8, 23), random.randint(6, 10))),
            active_days=sorted(random.sample(range(7), random.randint(4, 6))),
        )


@dataclass
class VisitRecord:
    """
    방문 기록 - 페르소나의 개별 방문 기록
    """
    url: str
    domain: str                          # "blog.naver.com"
    content_type: str = "unknown"        # "blog", "news", "shopping", "cafe"
    timestamp: datetime = field(default_factory=datetime.now)
    dwell_time: int = 0                  # 체류시간 (초)
    scroll_depth: float = 0.0            # 0.0 ~ 1.0
    actions: List[str] = field(default_factory=list)  # ["scroll", "click_link", "back"]

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "url": self.url,
            "domain": self.domain,
            "content_type": self.content_type,
            "timestamp": self.timestamp.isoformat(),
            "dwell_time": self.dwell_time,
            "scroll_depth": self.scroll_depth,
            "actions": self.actions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VisitRecord":
        """딕셔너리에서 생성"""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()

        return cls(
            url=data.get("url", ""),
            domain=data.get("domain", ""),
            content_type=data.get("content_type", "unknown"),
            timestamp=timestamp,
            dwell_time=data.get("dwell_time", 0),
            scroll_depth=data.get("scroll_depth", 0.0),
            actions=data.get("actions", []),
        )


@dataclass
class Persona:
    """
    가상 사용자 페르소나

    네이버에 "재방문자"로 인식되기 위한 모든 정보를 포함합니다:
    - 디바이스 식별자 (ANDROID_ID)
    - 브라우저 상태 (Chrome 데이터 폴더)
    - 행동 프로필
    - 방문 기록
    """

    # === 식별자 ===
    persona_id: str                       # 내부 관리 ID (uuid)
    name: str                             # "직장인_30대_남성" 등 설명용 이름

    # === 디바이스 ID (루팅 필요) ===
    android_id: str                       # ANDROID_ID (16자 hex)
    advertising_id: str                   # 광고 ID (UUID 형식)

    # === Chrome 데이터 경로 ===
    chrome_data_path: str = ""            # 백업된 Chrome 데이터 경로

    # === 네이버 식별자 (자동 생성됨) ===
    nnb_cookie: str = ""                  # 네이버 NNB 쿠키 (첫 방문 시 생성)

    # === 행동 프로필 ===
    behavior_profile: BehaviorProfile = field(default_factory=BehaviorProfile)

    # === 상태 ===
    status: PersonaStatus = PersonaStatus.ACTIVE
    visit_history: List[VisitRecord] = field(default_factory=list)
    last_active: datetime = field(default_factory=datetime.now)
    cooldown_until: Optional[datetime] = None

    # === 통계 ===
    total_sessions: int = 0
    total_pageviews: int = 0
    total_dwell_time: int = 0             # 총 체류시간 (초)

    # === 메타데이터 ===
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)  # ["tech_lover", "shopping"]
    notes: str = ""                       # 관리자 메모

    def __post_init__(self):
        """초기화 후 처리"""
        if isinstance(self.status, str):
            self.status = PersonaStatus(self.status)
        if isinstance(self.behavior_profile, dict):
            self.behavior_profile = BehaviorProfile.from_dict(self.behavior_profile)

    @property
    def is_available(self) -> bool:
        """사용 가능 여부"""
        if self.status not in [PersonaStatus.ACTIVE]:
            return False
        if self.cooldown_until and datetime.now() < self.cooldown_until:
            return False
        return True

    @property
    def visit_count(self) -> int:
        """총 방문 횟수"""
        return len(self.visit_history)

    @property
    def avg_session_dwell_time(self) -> float:
        """세션당 평균 체류시간"""
        if self.total_sessions == 0:
            return 0.0
        return self.total_dwell_time / self.total_sessions

    def add_visit(self, record: VisitRecord):
        """방문 기록 추가"""
        self.visit_history.append(record)
        self.total_pageviews += 1
        self.total_dwell_time += record.dwell_time
        self.last_active = datetime.now()

    def start_session(self):
        """세션 시작"""
        self.status = PersonaStatus.IN_USE
        self.total_sessions += 1
        self.last_active = datetime.now()

    def end_session(self, cooldown_minutes: int = 30):
        """세션 종료"""
        from datetime import timedelta
        self.status = PersonaStatus.COOLING_DOWN
        self.cooldown_until = datetime.now() + timedelta(minutes=cooldown_minutes)
        self.last_active = datetime.now()

    def finish_cooldown(self):
        """쿨다운 완료"""
        self.status = PersonaStatus.ACTIVE
        self.cooldown_until = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (DB 저장용)"""
        return {
            "persona_id": self.persona_id,
            "name": self.name,
            "android_id": self.android_id,
            "advertising_id": self.advertising_id,
            "chrome_data_path": self.chrome_data_path,
            "nnb_cookie": self.nnb_cookie,
            "behavior_profile": self.behavior_profile.to_dict(),
            "status": self.status.value,
            "visit_history": [v.to_dict() for v in self.visit_history[-100:]],  # 최근 100개만
            "last_active": self.last_active.isoformat(),
            "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None,
            "total_sessions": self.total_sessions,
            "total_pageviews": self.total_pageviews,
            "total_dwell_time": self.total_dwell_time,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Persona":
        """딕셔너리에서 생성"""
        # 날짜 필드 파싱
        last_active = data.get("last_active")
        if isinstance(last_active, str):
            last_active = datetime.fromisoformat(last_active)

        cooldown_until = data.get("cooldown_until")
        if isinstance(cooldown_until, str):
            cooldown_until = datetime.fromisoformat(cooldown_until)

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        # 방문 기록 파싱
        visit_history = [
            VisitRecord.from_dict(v)
            for v in data.get("visit_history", [])
        ]

        return cls(
            persona_id=data["persona_id"],
            name=data["name"],
            android_id=data["android_id"],
            advertising_id=data.get("advertising_id", str(uuid.uuid4())),
            chrome_data_path=data.get("chrome_data_path", ""),
            nnb_cookie=data.get("nnb_cookie", ""),
            behavior_profile=BehaviorProfile.from_dict(data.get("behavior_profile", {})),
            status=PersonaStatus(data.get("status", "active")),
            visit_history=visit_history,
            last_active=last_active or datetime.now(),
            cooldown_until=cooldown_until,
            total_sessions=data.get("total_sessions", 0),
            total_pageviews=data.get("total_pageviews", 0),
            total_dwell_time=data.get("total_dwell_time", 0),
            created_at=created_at or datetime.now(),
            tags=data.get("tags", []),
            notes=data.get("notes", ""),
        )

    @classmethod
    def create_new(
        cls,
        name: str,
        tags: List[str] = None,
        behavior_profile: BehaviorProfile = None
    ) -> "Persona":
        """
        새 페르소나 생성

        Args:
            name: 페르소나 이름
            tags: 태그 목록
            behavior_profile: 행동 프로필 (None이면 랜덤 생성)

        Returns:
            새 Persona 인스턴스
        """
        return cls(
            persona_id=str(uuid.uuid4()),
            name=name,
            android_id=cls._generate_android_id(),
            advertising_id=str(uuid.uuid4()),
            behavior_profile=behavior_profile or BehaviorProfile.generate_random(),
            tags=tags or [],
        )

    @staticmethod
    def _generate_android_id() -> str:
        """16자 hex ANDROID_ID 생성"""
        return ''.join(random.choices('0123456789abcdef', k=16))
