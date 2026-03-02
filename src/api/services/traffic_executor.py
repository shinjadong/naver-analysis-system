"""
TrafficExecutor - 트래픽 실행 서비스

캠페인 기반 트래픽 실행을 NaverSessionPipeline과 연동합니다.

사용 예시:
    executor = get_traffic_executor()
    result = await executor.execute_for_campaign(campaign_id)
"""

import logging
import subprocess
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TrafficResult:
    """트래픽 실행 결과"""
    success: bool
    campaign_id: str
    persona_id: Optional[str] = None
    device_serial: Optional[str] = None
    duration_sec: int = 0
    scroll_depth: float = 0.0
    interactions: int = 0
    ip_address: Optional[str] = None
    error_message: Optional[str] = None


class TrafficExecutor:
    """
    트래픽 실행 서비스

    두 가지 실행 모드 지원:
    1. Pipeline 모드: NaverSessionPipeline 기반 (기존)
    2. AI 모드: droidrun 기반 동적 UI 탐지 + 휴먼라이크 액션

    AI 모드가 권장됨 - 네이버의 동적 UI를 실시간으로 탐지

    사용 예시:
        executor = TrafficExecutor(device_serial="R3CW60BHSAT")

        # AI 모드 (권장)
        result = await executor.execute_ai_workflow(
            campaign_id="xxx",
            keyword="cctv가격",
            blog_title="CCTV가격 부담된다면?"
        )

        # Pipeline 모드 (기존)
        result = await executor.execute_for_campaign(
            campaign_id="xxx",
            persona_id="yyy"
        )
    """

    def __init__(self, device_serial: str = None):
        """
        Args:
            device_serial: ADB 디바이스 시리얼 (None이면 자동 감지)
        """
        self.device_serial = device_serial or self._detect_device()
        self._pipeline = None  # 지연 초기화
        self._persona_manager = None
        self._ai_workflow = None  # AI 워크플로우

    def _detect_device(self) -> Optional[str]:
        """연결된 ADB 디바이스 자동 감지"""
        try:
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                timeout=10
            )
            lines = result.stdout.strip().split("\n")[1:]
            for line in lines:
                if "device" in line and "unauthorized" not in line:
                    serial = line.split()[0]
                    logger.info(f"Auto-detected device: {serial}")
                    return serial
        except Exception as e:
            logger.warning(f"Device detection failed: {e}")
        return None

    @property
    def pipeline(self):
        """NaverSessionPipeline 지연 초기화"""
        if self._pipeline is None:
            try:
                from ...shared.pipeline import NaverSessionPipeline, PipelineConfig
                config = PipelineConfig(device_serial=self.device_serial)
                self._pipeline = NaverSessionPipeline(config)
                logger.info("NaverSessionPipeline initialized")
            except ImportError as e:
                logger.error(f"Failed to import NaverSessionPipeline: {e}")
                raise RuntimeError(
                    "NaverSessionPipeline not available. "
                    "Check if all dependencies are installed."
                )
        return self._pipeline

    @property
    def persona_manager(self):
        """PersonaManager 지연 초기화"""
        if self._persona_manager is None:
            try:
                from ...shared.persona_manager import PersonaManager
                self._persona_manager = PersonaManager(
                    db_path="data/personas.db",
                    device_serial=self.device_serial
                )
                logger.info("PersonaManager initialized")
            except ImportError as e:
                logger.warning(f"PersonaManager not available: {e}")
        return self._persona_manager

    @property
    def ai_workflow(self):
        """AICampaignWorkflow 지연 초기화"""
        if self._ai_workflow is None:
            try:
                from ...shared.ai_campaign_workflow import AICampaignWorkflow
                self._ai_workflow = AICampaignWorkflow(
                    device_serial=self.device_serial
                )
                logger.info("AICampaignWorkflow initialized")
            except ImportError as e:
                logger.warning(f"AICampaignWorkflow not available: {e}")
        return self._ai_workflow

    async def execute_ai_workflow(
        self,
        campaign_id: str,
        keyword: str = None,
        blog_title: str = None,
        blogger_name: str = None,
        blog_url: str = None,
        persona: "Persona" = None
    ) -> TrafficResult:
        """
        AI 모드로 캠페인 실행 (droidrun 기반)

        동적 UI 탐지 + 휴먼라이크 액션으로 실제 사용자 행동 시뮬레이션

        Args:
            campaign_id: 캠페인 UUID
            keyword: 검색 키워드
            blog_title: 타겟 블로그 포스트 제목
            blogger_name: 블로거 이름
            blog_url: 폴백용 URL
            persona: 페르소나 정보 (행동 프로필 포함)

        Returns:
            TrafficResult
        """
        from ...shared.supabase_client import get_supabase, is_supabase_available

        # 캠페인 정보 조회
        target_keyword = keyword
        target_url = blog_url
        target_title = blog_title
        target_blogger = blogger_name

        if is_supabase_available():
            try:
                db = get_supabase()
                campaign = db.get_campaign(campaign_id)
                if campaign:
                    target_keyword = target_keyword or campaign.target_keyword
                    target_url = target_url or campaign.blog_url
                    target_title = target_title or campaign.blog_title
                    logger.info(f"[AI] Campaign: {campaign.name}, keyword: {target_keyword}")
            except Exception as e:
                logger.warning(f"Failed to get campaign info: {e}")

        if not target_keyword:
            return TrafficResult(
                success=False,
                campaign_id=campaign_id,
                error_message="No keyword specified"
            )

        if not target_title and not target_url:
            return TrafficResult(
                success=False,
                campaign_id=campaign_id,
                error_message="No blog title or URL specified"
            )

        if not self.device_serial:
            return TrafficResult(
                success=False,
                campaign_id=campaign_id,
                error_message="No ADB device connected"
            )

        try:
            logger.info(f"[AI] Executing AI workflow for campaign {campaign_id}")

            # AI 워크플로우 실행 (페르소나 행동 프로필 적용)
            result = await self.ai_workflow.execute(
                keyword=target_keyword,
                target_blog_title=target_title or "",
                target_blogger=target_blogger,
                target_url=target_url,
                persona=persona
            )

            traffic_result = TrafficResult(
                success=result.success,
                campaign_id=campaign_id,
                persona_id="ai_session",
                device_serial=self.device_serial,
                duration_sec=int(result.duration_sec),
                scroll_depth=result.scroll_depth,
                interactions=result.scroll_count,
                error_message=result.error_message
            )

            # Supabase에 로그 기록
            if is_supabase_available():
                try:
                    db = get_supabase()
                    db.log_traffic_execution(
                        campaign_id=campaign_id,
                        persona_id="ai_session",
                        device_serial=self.device_serial or "unknown",
                        success=traffic_result.success,
                        duration_sec=traffic_result.duration_sec,
                        scroll_depth=traffic_result.scroll_depth,
                        interactions=traffic_result.interactions,
                        error_message=traffic_result.error_message
                    )
                except Exception as e:
                    logger.warning(f"Failed to log to Supabase: {e}")

            return traffic_result

        except Exception as e:
            logger.error(f"[AI] Workflow execution failed: {e}")
            return TrafficResult(
                success=False,
                campaign_id=campaign_id,
                device_serial=self.device_serial,
                error_message=str(e)
            )

    async def execute_for_campaign(
        self,
        campaign_id: str,
        persona_id: str = None,
        keyword: str = None,
        blog_url: str = None,
        blog_title: str = None,
        blogger_name: str = None
    ) -> TrafficResult:
        """
        캠페인 트래픽 1회 실행 (풀 워크플로우)

        워크플로우:
        1. 네이버 메인 → 키워드 검색
        2. 검색 결과 스크롤 (내려갔다 위로)
        3. 블로그 탭 클릭
        4. 타겟 포스트 찾기 (제목/블로거/날짜)
        5. 포스트 페이지 휴먼라이크 스크롤
        6. 공유 버튼 → URL 복사 → 종료

        Args:
            campaign_id: 캠페인 UUID
            persona_id: 사용할 페르소나 ID (None이면 자동 선택)
            keyword: 검색 키워드 (None이면 캠페인에서 조회)
            blog_url: 방문할 블로그 URL (폴백용)
            blog_title: 블로그 포스트 제목 (타겟 매칭용)
            blogger_name: 블로거 이름 (타겟 매칭용)

        Returns:
            TrafficResult
        """
        from ...shared.supabase_client import get_supabase, is_supabase_available

        # 캠페인 정보 조회
        target_keyword = keyword
        target_url = blog_url
        target_title = blog_title
        target_blogger = blogger_name

        if is_supabase_available():
            try:
                db = get_supabase()
                campaign = db.get_campaign(campaign_id)
                if campaign:
                    target_keyword = target_keyword or campaign.target_keyword
                    target_url = target_url or campaign.blog_url
                    target_title = target_title or campaign.blog_title
                    logger.info(f"Campaign: {campaign.name}, keyword: {target_keyword}")
                    logger.info(f"Target: {target_title[:30] if target_title else 'N/A'}...")
            except Exception as e:
                logger.warning(f"Failed to get campaign info: {e}")

        if not target_keyword:
            return TrafficResult(
                success=False,
                campaign_id=campaign_id,
                error_message="No keyword specified"
            )

        if not target_title and not target_url:
            return TrafficResult(
                success=False,
                campaign_id=campaign_id,
                error_message="No blog title or URL specified for targeting"
            )

        # 디바이스 확인
        if not self.device_serial:
            return TrafficResult(
                success=False,
                campaign_id=campaign_id,
                error_message="No ADB device connected"
            )

        try:
            # 캠페인 워크플로우 실행 (풀 시뮬레이션)
            logger.info(f"Executing campaign workflow for {campaign_id}")

            result = await self.pipeline.run_campaign_workflow(
                keyword=target_keyword,
                target_blog_title=target_title or "",
                target_blogger=target_blogger,
                target_url=target_url,
                persona_id=persona_id
            )

            # 결과 변환
            visit = result.visits[0] if result.visits else None

            traffic_result = TrafficResult(
                success=result.success,
                campaign_id=campaign_id,
                persona_id=result.persona_id,
                device_serial=self.device_serial,
                duration_sec=int(result.duration_sec),
                scroll_depth=visit.scroll_depth if visit else 0.0,
                interactions=visit.scroll_count if visit else 0,
                error_message=result.error_message
            )

            # Supabase에 로그 기록
            if is_supabase_available():
                try:
                    db = get_supabase()
                    db.log_traffic_execution(
                        campaign_id=campaign_id,
                        persona_id=traffic_result.persona_id or "unknown",
                        device_serial=traffic_result.device_serial or "unknown",
                        success=traffic_result.success,
                        duration_sec=traffic_result.duration_sec,
                        scroll_depth=traffic_result.scroll_depth,
                        interactions=traffic_result.interactions,
                        error_message=traffic_result.error_message
                    )
                except Exception as e:
                    logger.warning(f"Failed to log to Supabase: {e}")

            return traffic_result

        except Exception as e:
            logger.error(f"Traffic execution failed: {e}")
            return TrafficResult(
                success=False,
                campaign_id=campaign_id,
                device_serial=self.device_serial,
                error_message=str(e)
            )

    async def get_device_status(self) -> Dict[str, Any]:
        """디바이스 상태 조회"""
        try:
            result = subprocess.run(
                ["adb", "devices", "-l"],
                capture_output=True,
                text=True,
                timeout=10
            )

            devices = []
            lines = result.stdout.strip().split("\n")[1:]

            for line in lines:
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    serial = parts[0]
                    status = parts[1]
                    model = None
                    for part in parts[2:]:
                        if part.startswith("model:"):
                            model = part.split(":")[1]
                    devices.append({
                        "serial": serial,
                        "status": status,
                        "model": model,
                        "online": status == "device"
                    })

            return {
                "connected": len(devices) > 0,
                "current_device": self.device_serial,
                "devices": devices
            }

        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }

    def get_persona_stats(self) -> Dict[str, Any]:
        """페르소나 통계 조회"""
        if not self.persona_manager:
            return {
                "total": 0,
                "active": 0,
                "available": False,
                "message": "PersonaManager not available"
            }

        try:
            stats = self.persona_manager.get_stats()
            return {
                "total": stats.get("total_personas", 0),
                "active": 1 if stats.get("current_persona") else 0,
                "current": stats.get("current_persona"),
                "available": True,
                **stats
            }
        except Exception as e:
            return {
                "total": 0,
                "active": 0,
                "available": False,
                "error": str(e)
            }


# ========== 싱글톤 관리 ==========

_executors: Dict[str, TrafficExecutor] = {}


def get_traffic_executor(device_serial: str = None) -> TrafficExecutor:
    """
    TrafficExecutor 싱글톤 반환

    Args:
        device_serial: ADB 디바이스 시리얼 (None이면 자동 감지)

    Returns:
        TrafficExecutor 인스턴스
    """
    key = device_serial or "default"

    if key not in _executors:
        _executors[key] = TrafficExecutor(device_serial)

    return _executors[key]


def reset_executor(device_serial: str = None):
    """Executor 인스턴스 리셋 (테스트용)"""
    key = device_serial or "default"
    if key in _executors:
        del _executors[key]
