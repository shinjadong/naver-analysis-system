"""
Module Protocols (Interfaces)

모듈 간 느슨한 결합을 위한 프로토콜 정의:
- 타입 힌트를 통한 인터페이스 정의
- 의존성 주입 지원
- 테스트 용이성 확보
"""

from typing import (
    Protocol, List, Dict, Optional, Any, Tuple,
    AsyncIterator, runtime_checkable
)
from dataclasses import dataclass
from datetime import datetime
from abc import abstractmethod


# ============================================================
# Data Transfer Objects (DTOs)
# ============================================================

@dataclass
class PersonaDTO:
    """페르소나 데이터 전송 객체"""
    persona_id: str
    name: str
    android_id: str
    status: str
    interests: List[str]
    keywords: List[str]
    behavior_profile: Dict[str, Any]
    created_at: datetime
    last_active: Optional[datetime] = None


@dataclass
class ProjectDTO:
    """프로젝트 데이터 전송 객체"""
    project_id: str
    name: str
    status: str
    targets: List[Dict[str, Any]]
    progress: float
    daily_quota: int
    created_at: datetime


@dataclass
class TargetDTO:
    """타겟 데이터 전송 객체"""
    target_id: str
    keyword: str
    blog_title: str
    url: Optional[str]
    target_clicks: int
    current_clicks: int
    progress: float


@dataclass
class StorylineDTO:
    """스토리라인 데이터 전송 객체"""
    storyline_id: str
    persona_id: str
    actions: List[Dict[str, Any]]
    expected_duration_sec: int
    created_at: datetime


@dataclass
class ExecutionResultDTO:
    """실행 결과 데이터 전송 객체"""
    execution_id: str
    project_id: str
    target_id: str
    persona_id: str
    success: bool
    duration_sec: int
    scroll_depth: float
    interactions: int
    ip_address: Optional[str]
    error_message: Optional[str]
    executed_at: datetime


@dataclass
class IPAssignmentDTO:
    """IP 할당 데이터 전송 객체"""
    success: bool
    ip_address: Optional[str]
    provider: str
    is_korea: bool
    expires_at: Optional[datetime]


# ============================================================
# Provider Protocols
# ============================================================

@runtime_checkable
class PersonaProvider(Protocol):
    """페르소나 제공자 프로토콜"""

    async def get_persona(self, persona_id: str) -> Optional[PersonaDTO]:
        """페르소나 조회"""
        ...

    async def list_personas(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[PersonaDTO]:
        """페르소나 목록 조회"""
        ...

    async def create_persona(
        self,
        name: str,
        interests: List[str],
        keywords: List[str],
        **kwargs
    ) -> PersonaDTO:
        """페르소나 생성"""
        ...

    async def activate_persona(
        self,
        persona_id: str,
        device_serial: str
    ) -> bool:
        """페르소나 활성화 (디바이스에 적용)"""
        ...

    async def deactivate_persona(
        self,
        persona_id: str,
        save_session: bool = True
    ) -> bool:
        """페르소나 비활성화"""
        ...

    async def get_next_available(
        self,
        exclude_ids: List[str] = None
    ) -> Optional[PersonaDTO]:
        """다음 사용 가능한 페르소나"""
        ...


@runtime_checkable
class IPProvider(Protocol):
    """IP 제공자 프로토콜"""

    async def assign_ip(
        self,
        persona_id: str,
        ip_type: Optional[str] = None
    ) -> IPAssignmentDTO:
        """IP 할당"""
        ...

    async def release_ip(self, persona_id: str) -> bool:
        """IP 해제"""
        ...

    async def verify_ip(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """현재 IP 확인 (is_korea, ip, country)"""
        ...

    async def rotate_ip(self, persona_id: str) -> IPAssignmentDTO:
        """IP 로테이션"""
        ...

    async def health_check(self) -> Dict[str, bool]:
        """IP Provider 헬스체크"""
        ...


@runtime_checkable
class StorylineProvider(Protocol):
    """스토리라인 제공자 프로토콜"""

    async def generate_storyline(
        self,
        persona: PersonaDTO,
        target: TargetDTO,
        context: Dict[str, Any]
    ) -> StorylineDTO:
        """스토리라인 생성"""
        ...

    async def adapt_storyline(
        self,
        storyline: StorylineDTO,
        execution_result: Dict[str, Any]
    ) -> StorylineDTO:
        """실행 결과에 따른 스토리라인 조정"""
        ...

    async def get_next_actions(
        self,
        storyline_id: str,
        current_step: int
    ) -> List[Dict[str, Any]]:
        """다음 액션 조회"""
        ...


@runtime_checkable
class ProjectProvider(Protocol):
    """프로젝트 제공자 프로토콜"""

    async def get_project(self, project_id: str) -> Optional[ProjectDTO]:
        """프로젝트 조회"""
        ...

    async def list_projects(
        self,
        status: Optional[str] = None
    ) -> List[ProjectDTO]:
        """프로젝트 목록"""
        ...

    async def get_next_target(
        self,
        project_id: str
    ) -> Optional[TargetDTO]:
        """다음 실행할 타겟"""
        ...

    async def record_execution(
        self,
        result: ExecutionResultDTO
    ) -> bool:
        """실행 결과 기록"""
        ...

    async def get_project_stats(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """프로젝트 통계"""
        ...


@runtime_checkable
class ExecutionProvider(Protocol):
    """실행 제공자 프로토콜"""

    async def execute_action(
        self,
        action: Dict[str, Any],
        device_serial: str
    ) -> bool:
        """단일 액션 실행"""
        ...

    async def execute_storyline(
        self,
        storyline: StorylineDTO,
        device_serial: str
    ) -> ExecutionResultDTO:
        """스토리라인 전체 실행"""
        ...

    async def get_device_status(
        self,
        device_serial: str
    ) -> Dict[str, Any]:
        """디바이스 상태"""
        ...


# ============================================================
# Generator Protocols
# ============================================================

@runtime_checkable
class PersonaGeneratorProtocol(Protocol):
    """페르소나 생성기 프로토콜"""

    async def parse_keywords(
        self,
        file_path: str
    ) -> List[Dict[str, Any]]:
        """키워드 파일 파싱"""
        ...

    async def cluster_keywords(
        self,
        keywords: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """키워드 클러스터링"""
        ...

    async def generate_personas(
        self,
        clusters: Dict[str, List[str]],
        count: int
    ) -> List[PersonaDTO]:
        """페르소나 생성"""
        ...

    async def assign_keywords_to_persona(
        self,
        persona_id: str,
        keywords: List[str]
    ) -> bool:
        """페르소나에 키워드 할당"""
        ...


# ============================================================
# Orchestrator Protocol
# ============================================================

@runtime_checkable
class OrchestratorProtocol(Protocol):
    """오케스트레이터 프로토콜"""

    async def start_campaign(
        self,
        project_id: str,
        config: Dict[str, Any]
    ) -> bool:
        """캠페인 시작"""
        ...

    async def pause_campaign(self, project_id: str) -> bool:
        """캠페인 일시정지"""
        ...

    async def resume_campaign(self, project_id: str) -> bool:
        """캠페인 재개"""
        ...

    async def stop_campaign(self, project_id: str) -> bool:
        """캠페인 중지"""
        ...

    async def get_campaign_status(
        self,
        project_id: str
    ) -> Dict[str, Any]:
        """캠페인 상태"""
        ...

    async def execute_single_mission(
        self,
        project_id: str,
        target_id: str,
        persona_id: str
    ) -> ExecutionResultDTO:
        """단일 미션 실행"""
        ...


# ============================================================
# Repository Protocols
# ============================================================

@runtime_checkable
class RepositoryProtocol(Protocol):
    """저장소 프로토콜"""

    async def save(self, entity: Any) -> str:
        """엔티티 저장"""
        ...

    async def get(self, entity_id: str) -> Optional[Any]:
        """엔티티 조회"""
        ...

    async def list(
        self,
        filters: Dict[str, Any] = None,
        limit: int = 50
    ) -> List[Any]:
        """엔티티 목록"""
        ...

    async def delete(self, entity_id: str) -> bool:
        """엔티티 삭제"""
        ...

    async def update(
        self,
        entity_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """엔티티 업데이트"""
        ...
