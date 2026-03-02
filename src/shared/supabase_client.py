"""
Supabase 클라이언트 래퍼
캠페인/트래픽 로그 CRUD 담당

Usage:
    from src.shared.supabase_client import get_supabase, CampaignStatus

    db = get_supabase()
    campaigns = db.get_active_campaigns()
"""

import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# Supabase 클라이언트는 런타임에 임포트 (설치 안 된 경우 대비)
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("supabase-py not installed. Run: pip install supabase")


class CampaignStatus(str, Enum):
    """캠페인 상태"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass
class Campaign:
    """캠페인 데이터 클래스"""
    id: str
    name: str
    target_keyword: str
    utm_campaign: str
    status: CampaignStatus

    # 원고 정보
    blog_url: Optional[str] = None
    blog_title: Optional[str] = None

    # 목표 설정
    target_traffic: int = 100
    target_conversions: int = 5
    target_dwell_time: int = 120
    target_scroll_depth: float = 0.8

    # 실행 설정
    daily_quota: int = 10
    duration_days: int = 7
    cooldown_minutes: int = 30

    # 디바이스 설정
    devices: List[str] = field(default_factory=list)
    persona_count: int = 20

    # IP 설정
    ip_rotation: bool = True
    require_korea_ip: bool = True

    # 통계
    total_traffic: int = 0
    successful_traffic: int = 0
    total_visitors: int = 0
    total_conversions: int = 0
    conversion_rate: float = 0.0
    avg_dwell_time: float = 0.0
    avg_scroll_depth: float = 0.0

    # 오늘 실행 정보
    today_executions: int = 0
    last_execution_at: Optional[datetime] = None

    # 타임스탬프
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None

    @property
    def remaining_today(self) -> int:
        """오늘 남은 실행 횟수"""
        return max(0, self.daily_quota - self.today_executions)

    @property
    def progress_percent(self) -> float:
        """진행률 (%)"""
        if self.target_traffic <= 0:
            return 0.0
        return min(100.0, (self.total_traffic / self.target_traffic) * 100)

    @property
    def is_quota_available(self) -> bool:
        """오늘 쿼터가 남아있는지"""
        return self.remaining_today > 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Campaign":
        """딕셔너리에서 Campaign 객체 생성"""
        return cls(
            id=data["id"],
            name=data["name"],
            target_keyword=data["target_keyword"],
            utm_campaign=data["utm_campaign"],
            status=CampaignStatus(data["status"]),
            blog_url=data.get("blog_url"),
            blog_title=data.get("blog_title"),
            target_traffic=data.get("target_traffic", 100),
            target_conversions=data.get("target_conversions", 5),
            target_dwell_time=data.get("target_dwell_time", 120),
            target_scroll_depth=data.get("target_scroll_depth", 0.8),
            daily_quota=data.get("daily_quota", 10),
            duration_days=data.get("duration_days", 7),
            cooldown_minutes=data.get("cooldown_minutes", 30),
            devices=data.get("devices", []),
            persona_count=data.get("persona_count", 20),
            ip_rotation=data.get("ip_rotation", True),
            require_korea_ip=data.get("require_korea_ip", True),
            total_traffic=data.get("total_traffic", 0),
            successful_traffic=data.get("successful_traffic", 0),
            total_visitors=data.get("total_visitors", 0),
            total_conversions=data.get("total_conversions", 0),
            conversion_rate=data.get("conversion_rate", 0.0),
            avg_dwell_time=data.get("avg_dwell_time", 0.0),
            avg_scroll_depth=data.get("avg_scroll_depth", 0.0),
            today_executions=data.get("today_executions", 0),
            last_execution_at=_parse_datetime(data.get("last_execution_at")),
            created_at=_parse_datetime(data.get("created_at")),
            started_at=_parse_datetime(data.get("started_at")),
        )

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "name": self.name,
            "target_keyword": self.target_keyword,
            "utm_campaign": self.utm_campaign,
            "status": self.status.value,
            "blog_url": self.blog_url,
            "blog_title": self.blog_title,
            "target_traffic": self.target_traffic,
            "daily_quota": self.daily_quota,
            "total_traffic": self.total_traffic,
            "successful_traffic": self.successful_traffic,
            "total_visitors": self.total_visitors,
            "total_conversions": self.total_conversions,
            "conversion_rate": self.conversion_rate,
            "today_executions": self.today_executions,
            "remaining_today": self.remaining_today,
            "progress_percent": self.progress_percent,
        }


@dataclass
class TrafficLog:
    """트래픽 실행 로그"""
    id: str
    campaign_id: str
    persona_id: str
    device_serial: str
    success: bool
    duration_sec: int = 0
    scroll_depth: float = 0.0
    interactions: int = 0
    ip_address: Optional[str] = None
    ip_provider: Optional[str] = None
    error_message: Optional[str] = None
    executed_at: Optional[datetime] = None


@dataclass
class DailyStats:
    """일별 통계"""
    execution_date: date
    campaign_id: str
    campaign_name: str
    total_executions: int
    successful: int
    failed: int
    avg_duration: float
    avg_scroll: float
    unique_personas: int
    unique_ips: int


def _parse_datetime(value: Any) -> Optional[datetime]:
    """문자열을 datetime으로 파싱"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


class SupabaseClient:
    """
    Supabase 데이터베이스 클라이언트

    환경변수 필요:
    - SUPABASE_URL: Supabase 프로젝트 URL
    - SUPABASE_SERVICE_KEY: 서비스 키 (RLS 우회)
    """

    def __init__(self):
        if not SUPABASE_AVAILABLE:
            raise RuntimeError("supabase-py not installed")

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")

        if not url or not key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables required"
            )

        self.client: Client = create_client(url, key)
        logger.info("Supabase client initialized")

    # ========== 캠페인 CRUD ==========

    def get_campaigns(
        self,
        status: Optional[CampaignStatus] = None,
        limit: int = 100
    ) -> List[Campaign]:
        """
        캠페인 목록 조회

        Args:
            status: 필터링할 상태 (None이면 전체)
            limit: 최대 조회 개수

        Returns:
            Campaign 목록
        """
        query = self.client.table("campaigns").select("*")

        if status:
            query = query.eq("status", status.value)

        result = (
            query
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return [Campaign.from_dict(c) for c in result.data]

    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """
        캠페인 상세 조회

        Args:
            campaign_id: 캠페인 UUID

        Returns:
            Campaign 객체 또는 None
        """
        result = (
            self.client.table("campaigns")
            .select("*")
            .eq("id", campaign_id)
            .execute()
        )

        if result.data:
            return Campaign.from_dict(result.data[0])
        return None

    def get_campaign_by_utm(self, utm_campaign: str) -> Optional[Campaign]:
        """UTM 캠페인 값으로 조회"""
        result = (
            self.client.table("campaigns")
            .select("*")
            .eq("utm_campaign", utm_campaign)
            .execute()
        )

        if result.data:
            return Campaign.from_dict(result.data[0])
        return None

    def get_active_campaigns(self) -> List[Campaign]:
        """활성 캠페인 목록"""
        return self.get_campaigns(CampaignStatus.ACTIVE)

    def get_campaigns_with_quota(self) -> List[Campaign]:
        """오늘 쿼터가 남은 활성 캠페인"""
        campaigns = self.get_active_campaigns()
        return [c for c in campaigns if c.is_quota_available]

    def update_campaign_status(
        self,
        campaign_id: str,
        status: CampaignStatus
    ) -> bool:
        """
        캠페인 상태 업데이트

        Args:
            campaign_id: 캠페인 UUID
            status: 새 상태

        Returns:
            성공 여부
        """
        data: Dict[str, Any] = {"status": status.value}

        if status == CampaignStatus.ACTIVE:
            data["started_at"] = datetime.now().isoformat()
        elif status == CampaignStatus.PAUSED:
            data["paused_at"] = datetime.now().isoformat()
        elif status == CampaignStatus.COMPLETED:
            data["completed_at"] = datetime.now().isoformat()

        result = (
            self.client.table("campaigns")
            .update(data)
            .eq("id", campaign_id)
            .execute()
        )

        if result.data:
            logger.info(f"Campaign {campaign_id} status updated to {status.value}")
            return True
        return False

    def increment_today_executions(self, campaign_id: str) -> bool:
        """
        오늘 실행 횟수 증가

        Args:
            campaign_id: 캠페인 UUID

        Returns:
            성공 여부
        """
        # 현재 값 조회
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return False

        # 증가
        result = (
            self.client.table("campaigns")
            .update({
                "today_executions": campaign.today_executions + 1,
                "last_execution_at": datetime.now().isoformat()
            })
            .eq("id", campaign_id)
            .execute()
        )

        return len(result.data) > 0

    # ========== 트래픽 로그 ==========

    def log_traffic_execution(
        self,
        campaign_id: str,
        persona_id: str,
        device_serial: str,
        success: bool,
        duration_sec: int = 0,
        scroll_depth: float = 0.0,
        interactions: int = 0,
        ip_address: Optional[str] = None,
        ip_provider: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Optional[str]:
        """
        트래픽 실행 로그 기록

        Args:
            campaign_id: 캠페인 UUID
            persona_id: 페르소나 ID
            device_serial: 디바이스 시리얼
            success: 성공 여부
            duration_sec: 체류 시간 (초)
            scroll_depth: 스크롤 깊이 (0.0 ~ 1.0)
            interactions: 상호작용 횟수
            ip_address: 사용된 IP
            ip_provider: IP 제공자
            error_message: 에러 메시지 (실패 시)

        Returns:
            생성된 로그 ID
        """
        data = {
            "campaign_id": campaign_id,
            "persona_id": persona_id,
            "device_serial": device_serial,
            "success": success,
            "duration_sec": duration_sec,
            "scroll_depth": scroll_depth,
            "interactions": interactions,
            "ip_address": ip_address,
            "ip_provider": ip_provider,
            "error_message": error_message,
        }

        result = self.client.table("traffic_logs").insert(data).execute()

        if result.data:
            log_id = result.data[0]["id"]
            logger.debug(
                f"Traffic log created: {log_id} "
                f"(campaign={campaign_id}, success={success})"
            )
            return log_id
        return None

    def update_campaign_stats(self, campaign_id: str) -> None:
        """
        캠페인 통계 업데이트 (DB 함수 호출)

        트래픽 로그를 집계하여 캠페인의 통계 필드를 갱신합니다.

        Args:
            campaign_id: 캠페인 UUID
        """
        try:
            self.client.rpc(
                "update_campaign_stats",
                {"p_campaign_id": campaign_id}
            ).execute()
            logger.debug(f"Campaign stats updated: {campaign_id}")
        except Exception as e:
            logger.warning(f"Failed to update campaign stats: {e}")

    # ========== 통계 조회 ==========

    def get_campaign_dashboard(self, campaign_id: str) -> Dict[str, Any]:
        """
        대시보드용 캠페인 상세 정보

        Args:
            campaign_id: 캠페인 UUID

        Returns:
            대시보드 데이터 딕셔너리
        """
        result = (
            self.client.table("v_campaign_dashboard")
            .select("*")
            .eq("id", campaign_id)
            .execute()
        )

        return result.data[0] if result.data else {}

    def get_daily_stats(
        self,
        campaign_id: str,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        일별 통계 조회

        Args:
            campaign_id: 캠페인 UUID
            days: 조회할 일수

        Returns:
            일별 통계 목록
        """
        result = (
            self.client.table("v_campaign_daily_stats")
            .select("*")
            .eq("campaign_id", campaign_id)
            .order("execution_date", desc=True)
            .limit(days)
            .execute()
        )

        return result.data

    def get_conversion_funnel(self, campaign_id: str) -> Dict[str, Any]:
        """
        전환 퍼널 조회

        Args:
            campaign_id: 캠페인 UUID

        Returns:
            퍼널 데이터 (traffic, visitors, reservations, contracts)
        """
        result = (
            self.client.table("v_conversion_funnel")
            .select("*")
            .eq("campaign_id", campaign_id)
            .execute()
        )

        return result.data[0] if result.data else {}

    def get_recent_traffic_logs(
        self,
        campaign_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        최근 트래픽 로그 조회

        Args:
            campaign_id: 캠페인 UUID
            limit: 조회 개수

        Returns:
            트래픽 로그 목록
        """
        result = (
            self.client.table("traffic_logs")
            .select("*")
            .eq("campaign_id", campaign_id)
            .order("executed_at", desc=True)
            .limit(limit)
            .execute()
        )

        return result.data

    # ========== 유틸리티 ==========

    def reset_daily_executions(self) -> int:
        """
        모든 캠페인의 일일 실행 카운트 리셋

        매일 자정에 호출해야 함

        Returns:
            업데이트된 캠페인 수
        """
        result = (
            self.client.table("campaigns")
            .update({"today_executions": 0})
            .eq("status", CampaignStatus.ACTIVE.value)
            .execute()
        )

        count = len(result.data)
        logger.info(f"Reset daily executions for {count} campaigns")
        return count


# ========== 싱글톤 인스턴스 ==========

_client: Optional[SupabaseClient] = None


def get_supabase() -> SupabaseClient:
    """
    Supabase 클라이언트 싱글톤 반환

    Usage:
        db = get_supabase()
        campaigns = db.get_active_campaigns()
    """
    global _client
    if _client is None:
        _client = SupabaseClient()
    return _client


def is_supabase_available() -> bool:
    """Supabase 사용 가능 여부"""
    return SUPABASE_AVAILABLE
