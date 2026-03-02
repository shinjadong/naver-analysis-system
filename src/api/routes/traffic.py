"""
트래픽 실행 API

엔드포인트:
- POST /traffic/execute - 단일 트래픽 실행 (Pipeline 모드)
- POST /traffic/execute-ai - AI 모드 트래픽 실행 (권장)
- POST /traffic/batch - 배치 트래픽 실행
- GET /traffic/logs/{campaign_id} - 트래픽 로그 조회
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from ...shared.supabase_client import (
    get_supabase,
    CampaignStatus,
    is_supabase_available
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ========== 요청/응답 모델 ==========

class ExecuteRequest(BaseModel):
    """트래픽 실행 요청"""
    campaign_id: str = Field(..., description="캠페인 UUID")
    persona_id: Optional[str] = Field(None, description="사용할 페르소나 ID (없으면 자동 선택)")
    device_serial: Optional[str] = Field(None, description="사용할 디바이스 (없으면 자동 선택)")


class ExecuteAIRequest(BaseModel):
    """AI 모드 트래픽 실행 요청"""
    campaign_id: str = Field(..., description="캠페인 UUID")
    keyword: Optional[str] = Field(None, description="검색 키워드 (없으면 캠페인에서 조회)")
    blog_title: Optional[str] = Field(None, description="타겟 블로그 포스트 제목")
    blogger_name: Optional[str] = Field(None, description="블로거 이름")
    blog_url: Optional[str] = Field(None, description="폴백용 블로그 URL")
    device_serial: Optional[str] = Field(None, description="사용할 디바이스 (없으면 자동 선택)")


class ExecuteResponse(BaseModel):
    """트래픽 실행 응답"""
    success: bool
    execution_id: Optional[str] = None
    message: str = ""
    campaign_id: str = ""
    persona_id: Optional[str] = None
    device_serial: Optional[str] = None


class BatchExecuteRequest(BaseModel):
    """배치 트래픽 실행 요청"""
    campaign_id: str
    count: int = Field(1, ge=1, le=10, description="실행 횟수 (1-10)")


class BatchExecuteResponse(BaseModel):
    """배치 트래픽 실행 응답"""
    queued: int
    campaign_id: str
    message: str = ""


class TrafficLogItem(BaseModel):
    """트래픽 로그 아이템"""
    id: str
    persona_id: str
    device_serial: str
    success: bool
    duration_sec: int
    scroll_depth: float
    ip_address: Optional[str] = None
    error_message: Optional[str] = None
    executed_at: str


class TrafficLogsResponse(BaseModel):
    """트래픽 로그 응답"""
    campaign_id: str
    total: int
    logs: List[TrafficLogItem]


# ========== 백그라운드 작업 ==========

async def execute_traffic_task(
    campaign_id: str,
    persona_id: Optional[str],
    device_serial: Optional[str]
):
    """
    백그라운드에서 트래픽 실행

    NaverSessionPipeline을 통해 실제 트래픽을 생성합니다.
    1. 페르소나 선택 (없으면 least_recent 전략)
    2. 세션 리셋 (IP 회전 + 쿠키 삭제)
    3. 네이버 검색/블로그 방문 (휴먼라이크)
    4. 결과 로깅
    """
    logger.info(f"Executing traffic for campaign {campaign_id}")

    try:
        from ..services.traffic_executor import get_traffic_executor

        # TrafficExecutor를 통해 실행
        executor = get_traffic_executor(device_serial)
        result = await executor.execute_for_campaign(
            campaign_id=campaign_id,
            persona_id=persona_id
        )

        # 통계 업데이트
        if is_supabase_available() and result.success:
            db = get_supabase()
            db.increment_today_executions(campaign_id)
            db.update_campaign_stats(campaign_id)

        if result.success:
            logger.info(
                f"Traffic execution completed for campaign {campaign_id} "
                f"(persona={result.persona_id}, duration={result.duration_sec}s)"
            )
        else:
            logger.warning(
                f"Traffic execution failed for campaign {campaign_id}: "
                f"{result.error_message}"
            )

    except ImportError as e:
        logger.error(f"TrafficExecutor import failed: {e}")

        # 폴백: 기존 스텁 동작 (테스트용)
        if is_supabase_available():
            db = get_supabase()
            db.log_traffic_execution(
                campaign_id=campaign_id,
                persona_id=persona_id or "fallback_persona",
                device_serial=device_serial or "fallback_device",
                success=False,
                error_message=f"TrafficExecutor not available: {e}"
            )

    except Exception as e:
        logger.error(f"Traffic execution failed: {e}")

        # 실패 로그 기록
        if is_supabase_available():
            db = get_supabase()
            db.log_traffic_execution(
                campaign_id=campaign_id,
                persona_id=persona_id or "error_persona",
                device_serial=device_serial or "error_device",
                success=False,
                error_message=str(e)
            )


# ========== 엔드포인트 ==========

@router.post("/execute", response_model=ExecuteResponse)
async def execute_traffic(
    request: ExecuteRequest,
    background_tasks: BackgroundTasks
):
    """
    단일 트래픽 실행

    지정된 캠페인에 대해 트래픽을 1회 실행합니다.
    실행은 백그라운드에서 비동기로 처리됩니다.

    - **campaign_id**: 캠페인 UUID (필수)
    - **persona_id**: 사용할 페르소나 ID (선택, 없으면 자동)
    - **device_serial**: 사용할 디바이스 (선택, 없으면 자동)
    """
    if not is_supabase_available():
        raise HTTPException(500, "Supabase not available")

    try:
        db = get_supabase()

        # 캠페인 조회
        campaign = db.get_campaign(request.campaign_id)
        if not campaign:
            raise HTTPException(404, f"Campaign not found: {request.campaign_id}")

        # 상태 확인
        if campaign.status != CampaignStatus.ACTIVE:
            raise HTTPException(
                400,
                f"Campaign is not active. Current status: {campaign.status.value}"
            )

        # 쿼터 확인
        if not campaign.is_quota_available:
            raise HTTPException(
                400,
                f"Daily quota exhausted. Today: {campaign.today_executions}/{campaign.daily_quota}"
            )

        # 백그라운드 작업 등록
        background_tasks.add_task(
            execute_traffic_task,
            request.campaign_id,
            request.persona_id,
            request.device_serial
        )

        return ExecuteResponse(
            success=True,
            message="Traffic execution queued",
            campaign_id=request.campaign_id,
            persona_id=request.persona_id,
            device_serial=request.device_serial
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue traffic execution: {e}")
        raise HTTPException(500, str(e))


@router.post("/execute-ai", response_model=ExecuteResponse)
async def execute_traffic_ai(request: ExecuteAIRequest):
    """
    AI 모드 트래픽 실행 (권장)

    droidrun 기반의 동적 UI 탐지 + 휴먼라이크 액션으로
    실제 사용자 행동을 시뮬레이션합니다.

    Pipeline 모드와 달리 네이버의 동적 UI를 실시간으로 탐지하여
    더 정확한 타겟팅이 가능합니다.

    - **campaign_id**: 캠페인 UUID (필수)
    - **keyword**: 검색 키워드 (없으면 캠페인에서 조회)
    - **blog_title**: 타겟 블로그 포스트 제목
    - **blogger_name**: 블로거 이름
    - **blog_url**: 폴백용 블로그 URL
    - **device_serial**: 사용할 디바이스 (없으면 자동 선택)
    """
    if not is_supabase_available():
        raise HTTPException(500, "Supabase not available")

    try:
        db = get_supabase()

        # 캠페인 조회
        campaign = db.get_campaign(request.campaign_id)
        if not campaign:
            raise HTTPException(404, f"Campaign not found: {request.campaign_id}")

        # 상태 확인
        if campaign.status != CampaignStatus.ACTIVE:
            raise HTTPException(
                400,
                f"Campaign is not active. Current status: {campaign.status.value}"
            )

        # 쿼터 확인
        if not campaign.is_quota_available:
            raise HTTPException(
                400,
                f"Daily quota exhausted. Today: {campaign.today_executions}/{campaign.daily_quota}"
            )

        from ..services.traffic_executor import get_traffic_executor

        # AI 워크플로우 실행 (동기 실행 - 결과를 바로 반환)
        executor = get_traffic_executor(request.device_serial)
        result = await executor.execute_ai_workflow(
            campaign_id=request.campaign_id,
            keyword=request.keyword,
            blog_title=request.blog_title,
            blogger_name=request.blogger_name,
            blog_url=request.blog_url
        )

        # 통계 업데이트
        if result.success:
            db.increment_today_executions(request.campaign_id)
            db.update_campaign_stats(request.campaign_id)

        return ExecuteResponse(
            success=result.success,
            message="AI workflow completed" if result.success else f"AI workflow failed: {result.error_message}",
            campaign_id=request.campaign_id,
            persona_id=result.persona_id,
            device_serial=result.device_serial
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI execution failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/batch", response_model=BatchExecuteResponse)
async def execute_traffic_batch(
    request: BatchExecuteRequest,
    background_tasks: BackgroundTasks
):
    """
    배치 트래픽 실행

    지정된 캠페인에 대해 여러 번의 트래픽을 실행합니다.
    각 실행은 백그라운드에서 순차적으로 처리됩니다.

    - **campaign_id**: 캠페인 UUID (필수)
    - **count**: 실행 횟수 (1-10, 기본값 1)
    """
    if not is_supabase_available():
        raise HTTPException(500, "Supabase not available")

    try:
        db = get_supabase()

        # 캠페인 조회
        campaign = db.get_campaign(request.campaign_id)
        if not campaign:
            raise HTTPException(404, f"Campaign not found: {request.campaign_id}")

        # 상태 확인
        if campaign.status != CampaignStatus.ACTIVE:
            raise HTTPException(
                400,
                f"Campaign is not active. Current status: {campaign.status.value}"
            )

        # 쿼터 확인
        available = campaign.remaining_today
        actual_count = min(request.count, available)

        if actual_count == 0:
            raise HTTPException(
                400,
                f"Daily quota exhausted. Today: {campaign.today_executions}/{campaign.daily_quota}"
            )

        # 배치 작업 등록
        for i in range(actual_count):
            background_tasks.add_task(
                execute_traffic_task,
                request.campaign_id,
                None,  # 자동 선택
                None   # 자동 선택
            )

        return BatchExecuteResponse(
            queued=actual_count,
            campaign_id=request.campaign_id,
            message=f"Queued {actual_count} traffic executions"
            + (f" (requested {request.count}, limited by quota)" if actual_count < request.count else "")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue batch execution: {e}")
        raise HTTPException(500, str(e))


@router.get("/logs/{campaign_id}", response_model=TrafficLogsResponse)
async def get_traffic_logs(
    campaign_id: str,
    limit: int = Query(20, ge=1, le=100, description="조회 개수")
):
    """
    트래픽 로그 조회

    지정된 캠페인의 최근 트래픽 실행 로그를 반환합니다.

    - **campaign_id**: 캠페인 UUID
    - **limit**: 조회 개수 (1-100, 기본값 20)
    """
    if not is_supabase_available():
        raise HTTPException(500, "Supabase not available")

    try:
        db = get_supabase()

        # 캠페인 존재 확인
        campaign = db.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(404, f"Campaign not found: {campaign_id}")

        # 로그 조회
        logs = db.get_recent_traffic_logs(campaign_id, limit)

        return TrafficLogsResponse(
            campaign_id=campaign_id,
            total=len(logs),
            logs=[
                TrafficLogItem(
                    id=log["id"],
                    persona_id=log.get("persona_id", ""),
                    device_serial=log.get("device_serial", ""),
                    success=log.get("success", False),
                    duration_sec=log.get("duration_sec", 0),
                    scroll_depth=log.get("scroll_depth", 0),
                    ip_address=log.get("ip_address"),
                    error_message=log.get("error_message"),
                    executed_at=str(log.get("executed_at", ""))
                )
                for log in logs
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get traffic logs: {e}")
        raise HTTPException(500, str(e))
