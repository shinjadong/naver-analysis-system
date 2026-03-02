"""
Mission Schema and Definitions

미션 기반 인게이지먼트 시스템:
- 작업지시서(Mission) 정의
- 키워드 → 블로그 제목 → URL → 인게이지먼트 플로우
- 확장 가능한 미션 타입
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime
import json
import yaml
from pathlib import Path


class MissionType(Enum):
    """미션 타입"""
    BLOG_ENGAGEMENT = "blog_engagement"      # 블로그 방문 + 인게이지먼트
    SEARCH_CLICK = "search_click"            # 검색 후 특정 결과 클릭
    CAFE_ENGAGEMENT = "cafe_engagement"      # 카페 방문
    NEWS_READ = "news_read"                  # 뉴스 읽기
    SHOPPING_BROWSE = "shopping_browse"      # 쇼핑 브라우징
    CUSTOM = "custom"                        # 커스텀 시나리오


class MissionStatus(Enum):
    """미션 상태"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class EngagementTarget:
    """인게이지먼트 목표"""
    min_dwell_time_sec: int = 60           # 최소 체류 시간
    max_dwell_time_sec: int = 180          # 최대 체류 시간
    min_scroll_depth: float = 0.7          # 최소 스크롤 깊이 (0-1)
    min_interactions: int = 3              # 최소 상호작용 횟수
    read_comments: bool = False            # 댓글 읽기
    like_post: bool = False                # 좋아요 (로그인 필요)
    save_post: bool = False                # 저장 (로그인 필요)


@dataclass
class SearchTarget:
    """검색 타겟"""
    keyword: str                           # 검색 키워드
    search_type: str = "blog"              # blog, cafe, news, shop, all
    result_position: Optional[int] = None  # N번째 결과 클릭 (없으면 제목 매칭)
    title_contains: Optional[str] = None   # 제목에 포함된 텍스트
    title_exact: Optional[str] = None      # 정확한 제목
    author_name: Optional[str] = None      # 작성자 이름


@dataclass
class BlogTarget:
    """블로그 타겟"""
    url: Optional[str] = None              # 직접 URL
    blog_id: Optional[str] = None          # 블로그 ID
    post_id: Optional[str] = None          # 포스트 ID
    title: Optional[str] = None            # 포스트 제목


@dataclass
class MissionStep:
    """미션 단계"""
    step_id: str
    action: str                            # search, navigate, scroll, read, click, back, wait
    target: Dict[str, Any] = field(default_factory=dict)
    duration_range: tuple = (1000, 3000)   # (min_ms, max_ms)
    required: bool = True                  # 필수 단계 여부
    retry_count: int = 3                   # 실패 시 재시도 횟수
    success_condition: Optional[str] = None  # 성공 조건 (예: "url_contains:blog.naver.com")
    fallback_action: Optional[str] = None  # 실패 시 대안 행동


@dataclass
class Mission:
    """미션 정의"""
    mission_id: str
    mission_type: MissionType
    name: str
    description: str

    # 타겟 정보
    search_target: Optional[SearchTarget] = None
    blog_target: Optional[BlogTarget] = None
    engagement_target: EngagementTarget = field(default_factory=EngagementTarget)

    # 미션 단계
    steps: List[MissionStep] = field(default_factory=list)

    # 메타데이터
    priority: int = 5                      # 1-10 (1이 최고)
    persona_id: Optional[str] = None       # 할당된 페르소나
    scheduled_at: Optional[datetime] = None
    deadline: Optional[datetime] = None

    # 상태
    status: MissionStatus = MissionStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "mission_id": self.mission_id,
            "mission_type": self.mission_type.value,
            "name": self.name,
            "description": self.description,
            "search_target": {
                "keyword": self.search_target.keyword,
                "search_type": self.search_target.search_type,
                "title_contains": self.search_target.title_contains,
                "title_exact": self.search_target.title_exact,
            } if self.search_target else None,
            "blog_target": {
                "url": self.blog_target.url,
                "title": self.blog_target.title,
            } if self.blog_target else None,
            "engagement_target": {
                "min_dwell_time_sec": self.engagement_target.min_dwell_time_sec,
                "max_dwell_time_sec": self.engagement_target.max_dwell_time_sec,
                "min_scroll_depth": self.engagement_target.min_scroll_depth,
                "min_interactions": self.engagement_target.min_interactions,
            },
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Mission":
        """딕셔너리에서 생성"""
        search_target = None
        if data.get("search_target"):
            st = data["search_target"]
            search_target = SearchTarget(
                keyword=st["keyword"],
                search_type=st.get("search_type", "blog"),
                title_contains=st.get("title_contains"),
                title_exact=st.get("title_exact"),
                author_name=st.get("author_name"),
            )

        blog_target = None
        if data.get("blog_target"):
            bt = data["blog_target"]
            blog_target = BlogTarget(
                url=bt.get("url"),
                title=bt.get("title"),
                blog_id=bt.get("blog_id"),
            )

        engagement = EngagementTarget()
        if data.get("engagement_target"):
            et = data["engagement_target"]
            engagement = EngagementTarget(
                min_dwell_time_sec=et.get("min_dwell_time_sec", 60),
                max_dwell_time_sec=et.get("max_dwell_time_sec", 180),
                min_scroll_depth=et.get("min_scroll_depth", 0.7),
                min_interactions=et.get("min_interactions", 3),
            )

        return cls(
            mission_id=data["mission_id"],
            mission_type=MissionType(data.get("mission_type", "blog_engagement")),
            name=data["name"],
            description=data.get("description", ""),
            search_target=search_target,
            blog_target=blog_target,
            engagement_target=engagement,
            priority=data.get("priority", 5),
            persona_id=data.get("persona_id"),
        )


@dataclass
class MissionBatch:
    """미션 배치 (작업지시서)"""
    batch_id: str
    name: str
    missions: List[Mission]
    created_at: datetime = field(default_factory=datetime.now)

    # 배치 설정
    parallel_execution: bool = False       # 병렬 실행 여부
    stop_on_failure: bool = False          # 실패 시 중단
    cooldown_between_sec: int = 30         # 미션 간 쿨다운

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "MissionBatch":
        """YAML 작업지시서에서 로드"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        missions = [Mission.from_dict(m) for m in data.get("missions", [])]

        return cls(
            batch_id=data.get("batch_id", Path(yaml_path).stem),
            name=data.get("name", "Unnamed Batch"),
            missions=missions,
            parallel_execution=data.get("parallel_execution", False),
            stop_on_failure=data.get("stop_on_failure", False),
            cooldown_between_sec=data.get("cooldown_between_sec", 30),
        )

    def to_yaml(self, yaml_path: str) -> None:
        """YAML로 저장"""
        data = {
            "batch_id": self.batch_id,
            "name": self.name,
            "parallel_execution": self.parallel_execution,
            "stop_on_failure": self.stop_on_failure,
            "cooldown_between_sec": self.cooldown_between_sec,
            "missions": [m.to_dict() for m in self.missions],
        }

        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


# ============================================================
# 미션 팩토리 - 간편 생성
# ============================================================

class MissionFactory:
    """미션 간편 생성 팩토리"""

    @staticmethod
    def blog_engagement(
        keyword: str,
        blog_title: str,
        url: Optional[str] = None,
        dwell_time: int = 120,
        scroll_depth: float = 0.8
    ) -> Mission:
        """
        블로그 인게이지먼트 미션 생성

        Args:
            keyword: 검색 키워드
            blog_title: 찾을 블로그 제목 (부분 매칭)
            url: 직접 URL (있으면 검색 스킵)
            dwell_time: 체류 시간 (초)
            scroll_depth: 스크롤 깊이 (0-1)
        """
        import uuid

        search_target = SearchTarget(
            keyword=keyword,
            search_type="blog",
            title_contains=blog_title
        ) if not url else None

        blog_target = BlogTarget(
            url=url,
            title=blog_title
        )

        engagement = EngagementTarget(
            min_dwell_time_sec=int(dwell_time * 0.8),
            max_dwell_time_sec=int(dwell_time * 1.2),
            min_scroll_depth=scroll_depth,
            min_interactions=3
        )

        return Mission(
            mission_id=str(uuid.uuid4())[:8],
            mission_type=MissionType.BLOG_ENGAGEMENT,
            name=f"블로그 인게이지먼트: {blog_title[:20]}",
            description=f"키워드 '{keyword}'로 검색 후 '{blog_title}' 블로그 방문",
            search_target=search_target,
            blog_target=blog_target,
            engagement_target=engagement
        )

    @staticmethod
    def search_and_click(
        keyword: str,
        result_position: int = 1,
        search_type: str = "blog"
    ) -> Mission:
        """검색 후 N번째 결과 클릭 미션"""
        import uuid

        return Mission(
            mission_id=str(uuid.uuid4())[:8],
            mission_type=MissionType.SEARCH_CLICK,
            name=f"검색 클릭: {keyword} #{result_position}",
            description=f"'{keyword}' 검색 후 {result_position}번째 결과 클릭",
            search_target=SearchTarget(
                keyword=keyword,
                search_type=search_type,
                result_position=result_position
            ),
            engagement_target=EngagementTarget(
                min_dwell_time_sec=30,
                max_dwell_time_sec=60,
                min_scroll_depth=0.5,
                min_interactions=2
            )
        )

    @staticmethod
    def direct_url_visit(
        url: str,
        title: str = "",
        dwell_time: int = 90
    ) -> Mission:
        """URL 직접 방문 미션"""
        import uuid

        return Mission(
            mission_id=str(uuid.uuid4())[:8],
            mission_type=MissionType.BLOG_ENGAGEMENT,
            name=f"직접 방문: {title or url[:30]}",
            description=f"URL 직접 방문 및 인게이지먼트",
            blog_target=BlogTarget(url=url, title=title),
            engagement_target=EngagementTarget(
                min_dwell_time_sec=int(dwell_time * 0.8),
                max_dwell_time_sec=int(dwell_time * 1.2),
                min_scroll_depth=0.7,
                min_interactions=3
            )
        )


# ============================================================
# 작업지시서 파서
# ============================================================

class MissionParser:
    """작업지시서 파서 - 다양한 형식 지원"""

    @staticmethod
    def parse_csv_line(line: str) -> Mission:
        """
        CSV 한 줄 파싱: keyword,blog_title,url

        Example:
            서울맛집,강남 숨은 맛집 베스트10,https://blog.naver.com/xxx/123
        """
        parts = [p.strip() for p in line.split(",")]

        if len(parts) >= 3:
            keyword, blog_title, url = parts[0], parts[1], parts[2]
        elif len(parts) == 2:
            keyword, blog_title = parts[0], parts[1]
            url = None
        else:
            keyword = parts[0]
            blog_title = ""
            url = None

        return MissionFactory.blog_engagement(
            keyword=keyword,
            blog_title=blog_title,
            url=url if url else None
        )

    @staticmethod
    def parse_csv_file(csv_path: str) -> MissionBatch:
        """CSV 파일 파싱"""
        missions = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if i == 0 and "keyword" in line.lower():
                    continue  # 헤더 스킵

                try:
                    mission = MissionParser.parse_csv_line(line)
                    missions.append(mission)
                except Exception as e:
                    print(f"Warning: Failed to parse line {i+1}: {e}")

        return MissionBatch(
            batch_id=Path(csv_path).stem,
            name=f"CSV Import: {Path(csv_path).name}",
            missions=missions
        )

    @staticmethod
    def parse_simple_list(items: List[Dict[str, str]]) -> MissionBatch:
        """
        간단한 리스트 형식 파싱

        Example:
            [
                {"keyword": "서울맛집", "title": "강남 맛집", "url": "..."},
                {"keyword": "제주여행", "title": "제주 숙소 추천"},
            ]
        """
        import uuid

        missions = []
        for item in items:
            mission = MissionFactory.blog_engagement(
                keyword=item.get("keyword", ""),
                blog_title=item.get("title", item.get("blog_title", "")),
                url=item.get("url"),
                dwell_time=item.get("dwell_time", 120)
            )
            missions.append(mission)

        return MissionBatch(
            batch_id=str(uuid.uuid4())[:8],
            name="Simple List Import",
            missions=missions
        )
