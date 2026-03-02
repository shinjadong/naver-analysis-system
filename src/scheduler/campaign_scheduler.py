"""
CampaignScheduler - 캠페인 자동 실행 스케줄러

캠페인 시작 시 자동으로 트래픽을 실행합니다.
- daily_quota에 맞춰 실행 횟수 조절
- persona-manager와 연동하여 페르소나 선택/빙의
- AI 워크플로우로 실제 트래픽 실행
"""

import asyncio
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import random

logger = logging.getLogger(__name__)


@dataclass
class ScheduledCampaign:
    """스케줄링된 캠페인 정보"""
    campaign_id: str
    target_keyword: str
    blog_url: str
    blog_title: str
    daily_quota: int
    today_executions: int = 0
    last_execution: Optional[datetime] = None
    is_running: bool = False
    task: Optional[asyncio.Task] = field(default=None, repr=False)


class CampaignScheduler:
    """
    캠페인 자동 실행 스케줄러

    사용법:
        scheduler = CampaignScheduler()
        await scheduler.add_campaign(campaign_data)  # 캠페인 등록
        await scheduler.start()  # 스케줄러 시작
        await scheduler.stop()  # 스케줄러 중지
    """

    def __init__(
        self,
        min_interval_seconds: int = 300,  # 최소 실행 간격 (5분)
        max_interval_seconds: int = 900,  # 최대 실행 간격 (15분)
        check_interval_seconds: int = 60,  # 스케줄 체크 간격 (1분)
    ):
        self.min_interval = min_interval_seconds
        self.max_interval = max_interval_seconds
        self.check_interval = check_interval_seconds

        self._campaigns: Dict[str, ScheduledCampaign] = {}
        self._running = False
        self._main_task: Optional[asyncio.Task] = None

        # 의존성 (지연 초기화)
        self._persona_client = None
        self._traffic_executor = None

    @property
    def persona_client(self):
        """PersonaManagerClient 획득"""
        if self._persona_client is None:
            from ..clients.persona_client import get_persona_client
            self._persona_client = get_persona_client()
        return self._persona_client

    @property
    def traffic_executor(self):
        """TrafficExecutor 획득"""
        if self._traffic_executor is None:
            from ..api.services.traffic_executor import get_traffic_executor
            self._traffic_executor = get_traffic_executor()
        return self._traffic_executor

    # ========== 캠페인 관리 ==========

    async def add_campaign(self, campaign: Dict[str, Any]) -> bool:
        """
        캠페인 등록

        Args:
            campaign: 캠페인 정보 딕셔너리
                - id: 캠페인 UUID
                - target_keyword: 검색 키워드
                - blog_url: 타겟 블로그 URL
                - blog_title: 블로그 제목
                - daily_quota: 일일 실행 쿼터
                - today_executions: 오늘 실행 횟수

        Returns:
            등록 성공 여부
        """
        campaign_id = campaign.get("id")
        if not campaign_id:
            logger.error("Campaign ID is required")
            return False

        if campaign_id in self._campaigns:
            logger.warning(f"Campaign {campaign_id} already registered, updating...")

        scheduled = ScheduledCampaign(
            campaign_id=campaign_id,
            target_keyword=campaign.get("target_keyword", ""),
            blog_url=campaign.get("blog_url", ""),
            blog_title=campaign.get("blog_title", ""),
            daily_quota=campaign.get("daily_quota", 10),
            today_executions=campaign.get("today_executions", 0)
        )

        self._campaigns[campaign_id] = scheduled
        logger.info(f"Campaign {campaign_id} registered: {scheduled.target_keyword}")

        # 이미 실행 중이면 즉시 첫 실행 예약
        if self._running:
            asyncio.create_task(self._schedule_next_execution(campaign_id))

        return True

    async def remove_campaign(self, campaign_id: str) -> bool:
        """캠페인 제거"""
        if campaign_id not in self._campaigns:
            return False

        scheduled = self._campaigns[campaign_id]
        if scheduled.task and not scheduled.task.done():
            scheduled.task.cancel()

        del self._campaigns[campaign_id]
        logger.info(f"Campaign {campaign_id} removed from scheduler")
        return True

    async def pause_campaign(self, campaign_id: str) -> bool:
        """캠페인 일시정지"""
        if campaign_id not in self._campaigns:
            return False

        scheduled = self._campaigns[campaign_id]
        if scheduled.task and not scheduled.task.done():
            scheduled.task.cancel()
            scheduled.task = None

        logger.info(f"Campaign {campaign_id} paused")
        return True

    async def resume_campaign(self, campaign_id: str) -> bool:
        """캠페인 재개"""
        if campaign_id not in self._campaigns:
            return False

        if self._running:
            asyncio.create_task(self._schedule_next_execution(campaign_id))

        logger.info(f"Campaign {campaign_id} resumed")
        return True

    def get_campaign_status(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """캠페인 상태 조회"""
        if campaign_id not in self._campaigns:
            return None

        scheduled = self._campaigns[campaign_id]
        return {
            "campaign_id": scheduled.campaign_id,
            "target_keyword": scheduled.target_keyword,
            "daily_quota": scheduled.daily_quota,
            "today_executions": scheduled.today_executions,
            "remaining_today": max(0, scheduled.daily_quota - scheduled.today_executions),
            "is_running": scheduled.is_running,
            "last_execution": scheduled.last_execution.isoformat() if scheduled.last_execution else None,
            "has_pending_task": scheduled.task is not None and not scheduled.task.done()
        }

    def get_all_status(self) -> Dict[str, Any]:
        """전체 스케줄러 상태"""
        return {
            "running": self._running,
            "total_campaigns": len(self._campaigns),
            "campaigns": {
                cid: self.get_campaign_status(cid)
                for cid in self._campaigns
            }
        }

    # ========== 스케줄러 제어 ==========

    async def start(self):
        """스케줄러 시작"""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        logger.info("Campaign scheduler started")

        # 등록된 모든 캠페인에 대해 실행 예약
        for campaign_id in self._campaigns:
            asyncio.create_task(self._schedule_next_execution(campaign_id))

    async def stop(self):
        """스케줄러 중지"""
        self._running = False

        # 모든 대기 중인 작업 취소
        for scheduled in self._campaigns.values():
            if scheduled.task and not scheduled.task.done():
                scheduled.task.cancel()
                scheduled.task = None

        logger.info("Campaign scheduler stopped")

    # ========== 내부 실행 로직 ==========

    async def _schedule_next_execution(self, campaign_id: str):
        """다음 실행 예약"""
        if not self._running:
            return

        if campaign_id not in self._campaigns:
            return

        scheduled = self._campaigns[campaign_id]

        # 쿼터 확인
        if scheduled.today_executions >= scheduled.daily_quota:
            logger.info(f"Campaign {campaign_id} daily quota reached: {scheduled.today_executions}/{scheduled.daily_quota}")
            return

        # 랜덤 간격 계산
        delay = random.randint(self.min_interval, self.max_interval)

        # 첫 실행이면 바로 시작 (약간의 랜덤 딜레이)
        if scheduled.last_execution is None:
            delay = random.randint(5, 30)

        logger.info(f"Campaign {campaign_id} next execution in {delay} seconds")

        # 비동기 대기 후 실행
        scheduled.task = asyncio.create_task(
            self._delayed_execution(campaign_id, delay)
        )

    async def _delayed_execution(self, campaign_id: str, delay: int):
        """지연 후 실행"""
        try:
            await asyncio.sleep(delay)
            await self._execute_one(campaign_id)
        except asyncio.CancelledError:
            logger.info(f"Campaign {campaign_id} execution cancelled")
        except Exception as e:
            logger.error(f"Campaign {campaign_id} execution error: {e}")
        finally:
            # 다음 실행 예약
            if self._running and campaign_id in self._campaigns:
                asyncio.create_task(self._schedule_next_execution(campaign_id))

    async def _execute_one(self, campaign_id: str):
        """
        단일 트래픽 실행

        1. persona-manager에서 세션 시작 (페르소나 선택 + 빙의)
        2. AI 워크플로우 실행 (네이버 검색/방문)
        3. persona-manager에 세션 완료 통보
        """
        if campaign_id not in self._campaigns:
            return

        scheduled = self._campaigns[campaign_id]

        if scheduled.is_running:
            logger.warning(f"Campaign {campaign_id} already running, skipping")
            return

        scheduled.is_running = True
        logger.info(f"Executing campaign {campaign_id}: {scheduled.target_keyword}")

        session_id = None
        success = False
        duration_sec = 0
        scroll_depth = 0.0
        error_type = None
        error_message = None

        try:
            # 1. persona-manager에서 세션 시작
            session_response = await self.persona_client.start_session(
                campaign_id=campaign_id,
                mission={
                    "type": "search_and_click",
                    "target_keyword": scheduled.target_keyword,
                    "target_url": scheduled.blog_url,
                    "target_blog_title": scheduled.blog_title,
                    "min_dwell_time": 60,
                    "min_scroll_depth": 0.5
                }
            )

            session_id = session_response.session_id
            persona = session_response.persona

            logger.info(f"Session started: {session_id}, persona: {persona.name}")

            # 2. AI 워크플로우 실행 (페르소나 행동 프로필 적용)
            result = await self.traffic_executor.execute_ai_workflow(
                campaign_id=campaign_id,
                keyword=scheduled.target_keyword,
                blog_title=scheduled.blog_title,
                blog_url=scheduled.blog_url,
                persona=persona  # 행동 프로필 적용
            )

            success = result.success
            duration_sec = result.duration_sec
            scroll_depth = result.scroll_depth

            if not success:
                error_type = result.error_type
                error_message = result.error_message

        except Exception as e:
            logger.error(f"Campaign {campaign_id} execution failed: {e}")
            error_type = "execution_error"
            error_message = str(e)

        finally:
            # 3. persona-manager에 세션 완료 통보
            if session_id:
                try:
                    await self.persona_client.complete_session(
                        session_id=session_id,
                        success=success,
                        duration_sec=duration_sec,
                        scroll_depth=scroll_depth,
                        cooldown_minutes=30,
                        error_type=error_type,
                        error_message=error_message
                    )
                except Exception as e:
                    logger.error(f"Failed to complete session {session_id}: {e}")

            # 상태 업데이트
            scheduled.is_running = False
            scheduled.last_execution = datetime.now()
            if success:
                scheduled.today_executions += 1

            logger.info(
                f"Campaign {campaign_id} execution completed: "
                f"success={success}, duration={duration_sec}s, "
                f"today={scheduled.today_executions}/{scheduled.daily_quota}"
            )

    # ========== 수동 실행 ==========

    async def execute_now(self, campaign_id: str) -> Dict[str, Any]:
        """즉시 실행 (수동)"""
        if campaign_id not in self._campaigns:
            return {"success": False, "error": "Campaign not registered"}

        scheduled = self._campaigns[campaign_id]

        if scheduled.is_running:
            return {"success": False, "error": "Campaign already running"}

        if scheduled.today_executions >= scheduled.daily_quota:
            return {"success": False, "error": "Daily quota exhausted"}

        # 즉시 실행
        asyncio.create_task(self._execute_one(campaign_id))

        return {
            "success": True,
            "message": "Execution started",
            "campaign_id": campaign_id
        }


# 싱글톤 인스턴스
_scheduler: Optional[CampaignScheduler] = None


def get_scheduler() -> CampaignScheduler:
    """CampaignScheduler 싱글톤 획득"""
    global _scheduler
    if _scheduler is None:
        _scheduler = CampaignScheduler()
    return _scheduler
