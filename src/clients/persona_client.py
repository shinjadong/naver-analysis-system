"""
PersonaManagerClient - persona-manager API 클라이언트

persona-manager (포트 5002)와의 통신을 담당합니다.
세션 시작/완료, 페르소나 조회 등의 기능을 제공합니다.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)


@dataclass
class BehaviorProfile:
    """페르소나 행동 프로필"""
    scroll_speed: float = 1.0
    avg_dwell_time: int = 120
    reading_style: str = "normal"
    scroll_depth_preference: float = 0.5
    tap_accuracy: float = 0.9
    tap_delay_ms: Optional[List[int]] = None
    active_hours: Optional[List[int]] = None
    active_days: Optional[List[int]] = None
    typing_speed: float = 1.0


@dataclass
class Location:
    """위치 정보"""
    lat: float
    lng: float
    label: str
    accuracy: float = 10.0
    altitude: float = 0.0
    provider: str = "gps"


@dataclass
class DeviceConfig:
    """디바이스 설정"""
    android_id: str
    model: str
    manufacturer: str = "Samsung"
    sdk_version: int = 34
    imei: Optional[str] = None
    mac: Optional[str] = None
    build_fingerprint: Optional[str] = None


@dataclass
class Persona:
    """페르소나 정보"""
    id: str
    name: str
    tags: List[str]
    device_config: DeviceConfig
    location: Location
    behavior_profile: BehaviorProfile
    soul_file_path: Optional[str] = None
    trust_score: int = 0
    status: str = "idle"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Persona":
        """딕셔너리에서 Persona 객체 생성"""
        device_config = DeviceConfig(**data.get("device_config", {}))
        location = Location(**data.get("location", {"lat": 0, "lng": 0, "label": ""}))
        behavior_profile = BehaviorProfile(**data.get("behavior_profile", {}))

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            tags=data.get("tags", []),
            device_config=device_config,
            location=location,
            behavior_profile=behavior_profile,
            soul_file_path=data.get("soul_file_path"),
            trust_score=data.get("trust_score", 0),
            status=data.get("status", "idle")
        )


@dataclass
class Mission:
    """미션 정보"""
    type: str  # search_and_click, direct_visit, scroll_only
    target_keyword: str
    target_url: Optional[str] = None
    target_blog_title: Optional[str] = None
    min_dwell_time: int = 60
    min_scroll_depth: float = 0.5


@dataclass
class SessionResponse:
    """세션 시작 응답"""
    session_id: str
    persona: Persona
    mission: Optional[Mission] = None
    started_at: Optional[str] = None


class PersonaManagerError(Exception):
    """PersonaManager API 에러"""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"PersonaManager error {status_code}: {detail}")


class PersonaManagerClient:
    """
    persona-manager API 클라이언트

    세션 기반 페르소나 관리:
    1. start_session() - 페르소나 선택 + 빙의 시퀀스
    2. complete_session() - 세션 완료 + 영혼 백업
    3. abort_session() - 세션 중단
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0
    ):
        self.base_url = base_url or os.getenv("PERSONA_MANAGER_URL", "http://localhost:5002")
        self.api_key = api_key or os.getenv("PERSONA_MANAGER_API_KEY", "persona-manager-api-key-2026")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """HTTP 클라이언트 획득 (지연 초기화)"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": self.api_key
                }
            )
        return self._client

    async def close(self):
        """클라이언트 종료"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """HTTP 요청 실행"""
        client = await self._get_client()

        try:
            if method.upper() == "GET":
                response = await client.get(path, params=params)
            elif method.upper() == "POST":
                response = await client.post(path, json=data)
            elif method.upper() == "PUT":
                response = await client.put(path, json=data)
            elif method.upper() == "DELETE":
                response = await client.delete(path, params=params)
            else:
                raise ValueError(f"Unsupported method: {method}")

            if not response.is_success:
                detail = "Unknown error"
                try:
                    error_data = response.json()
                    detail = error_data.get("detail", str(error_data))
                except Exception:
                    detail = response.text
                raise PersonaManagerError(response.status_code, detail)

            return response.json()

        except httpx.RequestError as e:
            logger.error(f"PersonaManager request error: {e}")
            raise PersonaManagerError(0, f"Connection error: {e}")

    # ========== Health Check ==========

    async def health_check(self) -> bool:
        """헬스체크"""
        try:
            result = await self._request("GET", "/health")
            return result.get("status") == "ok"
        except Exception as e:
            logger.warning(f"PersonaManager health check failed: {e}")
            return False

    # ========== Session Management ==========

    async def start_session(
        self,
        campaign_id: str,
        mission: Dict[str, Any],
        min_trust_score: int = 0,
        location_label: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> SessionResponse:
        """
        세션 시작 - 페르소나 선택 + 빙의 시퀀스 실행

        Args:
            campaign_id: 캠페인 UUID
            mission: 미션 정보 {type, target_keyword, target_url, ...}
            min_trust_score: 최소 신뢰도
            location_label: 위치 필터 (예: "서울 강남구")
            tags: 태그 필터 (예: ["explorer", "morning_user"])

        Returns:
            SessionResponse: 세션 ID + 페르소나 정보
        """
        data = {
            "campaign_id": campaign_id,
            "mission": mission,
            "min_trust_score": min_trust_score
        }
        if location_label:
            data["location_label"] = location_label
        if tags:
            data["tags"] = tags

        result = await self._request("POST", "/sessions/start", data=data)

        persona_data = result.get("persona", {})
        persona = Persona.from_dict(persona_data)

        return SessionResponse(
            session_id=result.get("session_id", ""),
            persona=persona,
            started_at=result.get("started_at")
        )

    async def complete_session(
        self,
        session_id: str,
        success: bool,
        duration_sec: int = 0,
        scroll_count: int = 0,
        scroll_depth: float = 0.0,
        interactions: int = 0,
        cooldown_minutes: int = 30,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        세션 완료 - 영혼 백업 + 페르소나 체크인

        Args:
            session_id: 세션 UUID
            success: 성공 여부
            duration_sec: 수행 시간 (초)
            scroll_count: 스크롤 횟수
            scroll_depth: 스크롤 깊이 (0.0~1.0)
            interactions: 상호작용 횟수
            cooldown_minutes: 쿨다운 시간 (분)
            error_type: 에러 유형 (실패 시)
            error_message: 에러 메시지 (실패 시)
        """
        data = {
            "success": success,
            "duration_sec": duration_sec,
            "scroll_count": scroll_count,
            "scroll_depth": scroll_depth,
            "interactions": interactions,
            "cooldown_minutes": cooldown_minutes
        }
        if error_type:
            data["error_type"] = error_type
        if error_message:
            data["error_message"] = error_message

        return await self._request("POST", f"/sessions/{session_id}/complete", data=data)

    async def abort_session(self, session_id: str, reason: str = "aborted") -> Dict[str, Any]:
        """세션 중단"""
        return await self._request("POST", f"/sessions/{session_id}/abort", data={"reason": reason})

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """세션 상세 조회"""
        return await self._request("GET", f"/sessions/{session_id}")

    async def get_current_session_status(self) -> Dict[str, Any]:
        """현재 활성 세션 상태"""
        return await self._request("GET", "/sessions/current/status")

    # ========== Persona Management ==========

    async def list_personas(
        self,
        status: Optional[str] = None,
        min_trust_score: Optional[int] = None,
        location_label: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """페르소나 목록 조회"""
        params = {"limit": limit}
        if status:
            params["status"] = status
        if min_trust_score is not None:
            params["min_trust_score"] = min_trust_score
        if location_label:
            params["location_label"] = location_label

        return await self._request("GET", "/personas", params=params)

    async def get_persona(self, persona_id: str) -> Persona:
        """페르소나 상세 조회"""
        result = await self._request("GET", f"/personas/{persona_id}")
        return Persona.from_dict(result)

    async def get_stats(self) -> Dict[str, Any]:
        """전체 페르소나 통계"""
        return await self._request("GET", "/stats")


# 싱글톤 인스턴스
_persona_client: Optional[PersonaManagerClient] = None


def get_persona_client() -> PersonaManagerClient:
    """PersonaManagerClient 싱글톤 획득"""
    global _persona_client
    if _persona_client is None:
        _persona_client = PersonaManagerClient()
    return _persona_client
