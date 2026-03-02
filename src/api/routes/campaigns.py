"""
캠페인 관리 API

엔드포인트:
- GET /campaigns - 캠페인 목록
- GET /campaigns/{id} - 캠페인 상세
- POST /campaigns/{id}/control - 캠페인 제어 (시작/정지)
- GET /campaigns/{id}/stats - 일별 통계
"""

import logging
from typing import Optional, List
from enum import Enum

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...shared.supabase_client import (
    get_supabase,
    CampaignStatus,
    is_supabase_available
)
from ...scheduler import get_scheduler

logger = logging.getLogger(__name__)
router = APIRouter()


# ========== 요청/응답 모델 ==========

class CampaignListItem(BaseModel):
    """캠페인 목록 아이템"""
    id: str
    name: str
    target_keyword: str
    blog_url: Optional[str] = None
    blog_title: Optional[str] = None
    utm_campaign: str
    status: str
    target_traffic: int
    daily_quota: int
    total_traffic: int
    successful_traffic: int
    total_visitors: int
    total_conversions: int
    conversion_rate: float
    today_executions: int
    remaining_today: int
    progress_percent: float


class CampaignDetail(CampaignListItem):
    """캠페인 상세 정보"""
    target_dwell_time: int = 120
    target_scroll_depth: float = 0.8
    avg_dwell_time: float = 0.0
    avg_scroll_depth: float = 0.0
    devices: List[str] = []
    persona_count: int = 20


class ControlAction(str, Enum):
    """캠페인 제어 액션"""
    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"


class ControlRequest(BaseModel):
    """캠페인 제어 요청"""
    action: ControlAction


class ControlResponse(BaseModel):
    """캠페인 제어 응답"""
    status: str
    campaign_id: str
    message: str = ""
    scheduled: bool = False  # 스케줄러 등록 여부
    scheduler_status: Optional[dict] = None  # 스케줄러 상태


class DailyStatsItem(BaseModel):
    """일별 통계 아이템"""
    execution_date: str
    total_executions: int
    successful: int
    failed: int
    success_rate: float
    avg_duration: Optional[float] = None
    avg_scroll: Optional[float] = None
    unique_personas: int
    unique_ips: int


class StatsResponse(BaseModel):
    """통계 응답"""
    campaign_id: str
    daily_stats: List[DailyStatsItem]


# ========== 엔드포인트 ==========

@router.get("", response_model=List[CampaignListItem])
async def list_campaigns(
    status: Optional[str] = Query(None, description="필터링할 상태 (draft, active, paused, completed)")
):
    """
    캠페인 목록 조회

    - **status**: 필터링할 상태 (선택)
    """
    if not is_supabase_available():
        raise HTTPException(500, "Supabase not available")

    try:
        db = get_supabase()

        # 상태 필터
        status_filter = None
        if status:
            try:
                status_filter = CampaignStatus(status)
            except ValueError:
                raise HTTPException(400, f"Invalid status: {status}")

        campaigns = db.get_campaigns(status_filter)

        return [
            CampaignListItem(
                id=c.id,
                name=c.name,
                target_keyword=c.target_keyword,
                blog_url=c.blog_url,
                blog_title=c.blog_title,
                utm_campaign=c.utm_campaign,
                status=c.status.value,
                target_traffic=c.target_traffic,
                daily_quota=c.daily_quota,
                total_traffic=c.total_traffic,
                successful_traffic=c.successful_traffic,
                total_visitors=c.total_visitors,
                total_conversions=c.total_conversions,
                conversion_rate=c.conversion_rate,
                today_executions=c.today_executions,
                remaining_today=c.remaining_today,
                progress_percent=c.progress_percent,
            )
            for c in campaigns
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list campaigns: {e}")
        raise HTTPException(500, str(e))


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(campaign_id: str):
    """
    캠페인 상세 조회

    - **campaign_id**: 캠페인 UUID
    """
    if not is_supabase_available():
        raise HTTPException(500, "Supabase not available")

    try:
        db = get_supabase()
        campaign = db.get_campaign(campaign_id)

        if not campaign:
            raise HTTPException(404, f"Campaign not found: {campaign_id}")

        return CampaignDetail(
            id=campaign.id,
            name=campaign.name,
            target_keyword=campaign.target_keyword,
            blog_url=campaign.blog_url,
            blog_title=campaign.blog_title,
            utm_campaign=campaign.utm_campaign,
            status=campaign.status.value,
            target_traffic=campaign.target_traffic,
            daily_quota=campaign.daily_quota,
            total_traffic=campaign.total_traffic,
            successful_traffic=campaign.successful_traffic,
            total_visitors=campaign.total_visitors,
            total_conversions=campaign.total_conversions,
            conversion_rate=campaign.conversion_rate,
            today_executions=campaign.today_executions,
            remaining_today=campaign.remaining_today,
            progress_percent=campaign.progress_percent,
            target_dwell_time=campaign.target_dwell_time,
            target_scroll_depth=campaign.target_scroll_depth,
            avg_dwell_time=campaign.avg_dwell_time,
            avg_scroll_depth=campaign.avg_scroll_depth,
            devices=campaign.devices,
            persona_count=campaign.persona_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get campaign: {e}")
        raise HTTPException(500, str(e))


@router.post("/{campaign_id}/control", response_model=ControlResponse)
async def control_campaign(campaign_id: str, request: ControlRequest):
    """
    캠페인 제어 (시작/정지/재개)

    - **campaign_id**: 캠페인 UUID
    - **action**: 제어 액션 (start, pause, resume, stop)

    캠페인 시작 시 자동으로 스케줄러에 등록되어 트래픽이 실행됩니다.
    """
    if not is_supabase_available():
        raise HTTPException(500, "Supabase not available")

    try:
        db = get_supabase()
        campaign = db.get_campaign(campaign_id)

        if not campaign:
            raise HTTPException(404, f"Campaign not found: {campaign_id}")

        action = request.action
        current_status = campaign.status
        scheduler = get_scheduler()

        # 액션별 처리
        if action == ControlAction.START:
            if current_status not in [CampaignStatus.DRAFT, CampaignStatus.PAUSED]:
                raise HTTPException(
                    400,
                    f"Cannot start campaign in '{current_status.value}' status. "
                    f"Only 'draft' or 'paused' campaigns can be started."
                )

            # 1. DB 상태 변경
            db.update_campaign_status(campaign_id, CampaignStatus.ACTIVE)

            # 2. 스케줄러에 캠페인 등록
            campaign_data = {
                "id": campaign.id,
                "target_keyword": campaign.target_keyword,
                "blog_url": campaign.blog_url,
                "blog_title": campaign.blog_title,
                "daily_quota": campaign.daily_quota,
                "today_executions": campaign.today_executions
            }
            scheduled = await scheduler.add_campaign(campaign_data)

            # 3. 스케줄러 시작 (아직 안 되어 있으면)
            if not scheduler._running:
                await scheduler.start()

            scheduler_status = scheduler.get_campaign_status(campaign_id)

            logger.info(f"Campaign started and scheduled: {campaign_id}")
            return ControlResponse(
                status="started",
                campaign_id=campaign_id,
                message="Campaign started and scheduled for automatic traffic execution",
                scheduled=scheduled,
                scheduler_status=scheduler_status
            )

        elif action == ControlAction.PAUSE:
            if current_status != CampaignStatus.ACTIVE:
                raise HTTPException(
                    400,
                    f"Cannot pause campaign in '{current_status.value}' status. "
                    f"Only 'active' campaigns can be paused."
                )

            # 1. DB 상태 변경
            db.update_campaign_status(campaign_id, CampaignStatus.PAUSED)

            # 2. 스케줄러에서 일시정지
            await scheduler.pause_campaign(campaign_id)

            logger.info(f"Campaign paused: {campaign_id}")
            return ControlResponse(
                status="paused",
                campaign_id=campaign_id,
                message="Campaign paused",
                scheduled=False
            )

        elif action == ControlAction.RESUME:
            if current_status != CampaignStatus.PAUSED:
                raise HTTPException(
                    400,
                    f"Cannot resume campaign in '{current_status.value}' status. "
                    f"Only 'paused' campaigns can be resumed."
                )

            # 1. DB 상태 변경
            db.update_campaign_status(campaign_id, CampaignStatus.ACTIVE)

            # 2. 스케줄러에서 재개
            await scheduler.resume_campaign(campaign_id)

            scheduler_status = scheduler.get_campaign_status(campaign_id)

            logger.info(f"Campaign resumed: {campaign_id}")
            return ControlResponse(
                status="resumed",
                campaign_id=campaign_id,
                message="Campaign resumed",
                scheduled=True,
                scheduler_status=scheduler_status
            )

        elif action == ControlAction.STOP:
            if current_status == CampaignStatus.COMPLETED:
                raise HTTPException(400, "Campaign is already completed")

            # 1. DB 상태 변경
            db.update_campaign_status(campaign_id, CampaignStatus.COMPLETED)

            # 2. 스케줄러에서 제거
            await scheduler.remove_campaign(campaign_id)

            logger.info(f"Campaign stopped: {campaign_id}")
            return ControlResponse(
                status="stopped",
                campaign_id=campaign_id,
                message="Campaign stopped and marked as completed",
                scheduled=False
            )

        else:
            raise HTTPException(400, f"Unknown action: {action}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to control campaign: {e}")
        raise HTTPException(500, str(e))


@router.get("/{campaign_id}/stats", response_model=StatsResponse)
async def get_campaign_stats(
    campaign_id: str,
    days: int = Query(7, ge=1, le=90, description="조회할 일수")
):
    """
    캠페인 일별 통계

    - **campaign_id**: 캠페인 UUID
    - **days**: 조회할 일수 (기본 7일, 최대 90일)
    """
    if not is_supabase_available():
        raise HTTPException(500, "Supabase not available")

    try:
        db = get_supabase()

        # 캠페인 존재 확인
        campaign = db.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(404, f"Campaign not found: {campaign_id}")

        # 일별 통계 조회
        daily_stats = db.get_daily_stats(campaign_id, days)

        return StatsResponse(
            campaign_id=campaign_id,
            daily_stats=[
                DailyStatsItem(
                    execution_date=str(d.get("execution_date", "")),
                    total_executions=d.get("total_executions", 0),
                    successful=d.get("successful", 0),
                    failed=d.get("failed", 0),
                    success_rate=(
                        d.get("successful", 0) / d.get("total_executions", 1) * 100
                        if d.get("total_executions", 0) > 0 else 0
                    ),
                    avg_duration=d.get("avg_duration"),
                    avg_scroll=d.get("avg_scroll"),
                    unique_personas=d.get("unique_personas", 0),
                    unique_ips=d.get("unique_ips", 0),
                )
                for d in daily_stats
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get campaign stats: {e}")
        raise HTTPException(500, str(e))
