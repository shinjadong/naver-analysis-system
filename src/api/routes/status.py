"""
시스템 상태 API

엔드포인트:
- GET /status/devices - 연결된 ADB 디바이스 상태
- GET /status/personas - 페르소나 현황
- GET /status/engine - 트래픽 엔진 상태
"""

import logging
import subprocess
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# ========== 응답 모델 ==========

class DeviceStatus(BaseModel):
    """디바이스 상태"""
    serial: str
    status: str  # device, offline, unauthorized
    model: Optional[str] = None
    online: bool = False


class PersonaDeviceInfo(BaseModel):
    """디바이스별 페르소나 정보"""
    count: int
    active: int = 0
    last_used: Optional[str] = None


class PersonaStatus(BaseModel):
    """페르소나 현황"""
    total: int
    active: int
    devices: Dict[str, PersonaDeviceInfo]


class RunningCampaign(BaseModel):
    """실행 중인 캠페인 정보"""
    campaign_id: str
    name: str
    pending_tasks: int
    completed_tasks: int


class EngineStatus(BaseModel):
    """트래픽 엔진 상태"""
    running: bool
    running_campaigns: int
    pending_tasks: int
    completed_today: int
    campaigns: List[RunningCampaign] = []


# ========== 엔드포인트 ==========

@router.get("/devices", response_model=List[DeviceStatus])
async def get_device_status():
    """
    연결된 ADB 디바이스 상태

    ADB를 통해 연결된 안드로이드 디바이스 목록을 반환합니다.
    """
    try:
        # adb devices -l 실행
        result = subprocess.run(
            ["adb", "devices", "-l"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            logger.error(f"ADB error: {result.stderr}")
            raise HTTPException(500, f"ADB error: {result.stderr}")

        devices = []
        lines = result.stdout.strip().split("\n")

        # 첫 번째 줄은 헤더 ("List of devices attached")
        for line in lines[1:]:
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            serial = parts[0]
            status = parts[1]

            # 모델명 추출 (model:xxx 형식)
            model = None
            for part in parts[2:]:
                if part.startswith("model:"):
                    model = part.split(":")[1]
                    break

            devices.append(DeviceStatus(
                serial=serial,
                status=status,
                model=model,
                online=status == "device"
            ))

        logger.info(f"Found {len(devices)} devices")
        return devices

    except subprocess.TimeoutExpired:
        logger.error("ADB timeout")
        raise HTTPException(500, "ADB command timeout")
    except FileNotFoundError:
        logger.error("ADB not found")
        raise HTTPException(500, "ADB not found. Install Android SDK.")
    except Exception as e:
        logger.error(f"Failed to get device status: {e}")
        raise HTTPException(500, str(e))


@router.get("/personas", response_model=PersonaStatus)
async def get_persona_status():
    """
    페르소나 현황

    각 디바이스에 설정된 페르소나 수와 상태를 반환합니다.
    PersonaManager에서 실제 데이터를 조회합니다.
    """
    try:
        from ..services.traffic_executor import get_traffic_executor

        # TrafficExecutor를 통해 PersonaManager 접근
        executor = get_traffic_executor()
        persona_stats = executor.get_persona_stats()

        # 연결된 디바이스 조회
        devices_result = await get_device_status()
        online_devices = [d for d in devices_result if d.online]

        devices_info = {}
        total_personas = persona_stats.get("total", 0)

        # PersonaManager가 사용 가능하면 실제 데이터 사용
        if persona_stats.get("available"):
            for device in online_devices:
                # 디바이스별 페르소나 정보
                devices_info[device.serial] = PersonaDeviceInfo(
                    count=persona_stats.get("total_personas", 20),
                    active=1 if persona_stats.get("current") else 0,
                    last_used=persona_stats.get("last_active")
                )
        else:
            # 폴백: 기본값
            for device in online_devices:
                devices_info[device.serial] = PersonaDeviceInfo(
                    count=20,
                    active=0,
                    last_used=None
                )
                total_personas += 20

        return PersonaStatus(
            total=total_personas if total_personas > 0 else len(online_devices) * 20,
            active=persona_stats.get("active", 0),
            devices=devices_info
        )

    except ImportError as e:
        logger.warning(f"TrafficExecutor not available: {e}")
        # 폴백: 기본 응답
        return PersonaStatus(
            total=40,
            active=0,
            devices={}
        )

    except Exception as e:
        logger.error(f"Failed to get persona status: {e}")
        # 에러 시에도 기본 응답 반환
        return PersonaStatus(
            total=40,
            active=0,
            devices={}
        )


@router.get("/engine", response_model=EngineStatus)
async def get_engine_status():
    """
    트래픽 엔진 상태

    현재 실행 중인 캠페인과 작업 현황을 반환합니다.
    """
    try:
        # TODO: CampaignOrchestrator에서 실제 데이터 조회
        # 현재는 기본값 반환

        from ...shared.supabase_client import get_supabase, is_supabase_available

        running_campaigns = []
        completed_today = 0

        if is_supabase_available():
            try:
                db = get_supabase()
                active_campaigns = db.get_active_campaigns()

                for campaign in active_campaigns:
                    running_campaigns.append(RunningCampaign(
                        campaign_id=campaign.id,
                        name=campaign.name,
                        pending_tasks=campaign.remaining_today,
                        completed_tasks=campaign.today_executions
                    ))
                    completed_today += campaign.today_executions

            except Exception as e:
                logger.warning(f"Failed to get campaigns from DB: {e}")

        return EngineStatus(
            running=len(running_campaigns) > 0,
            running_campaigns=len(running_campaigns),
            pending_tasks=sum(c.pending_tasks for c in running_campaigns),
            completed_today=completed_today,
            campaigns=running_campaigns
        )

    except Exception as e:
        logger.error(f"Failed to get engine status: {e}")
        return EngineStatus(
            running=False,
            running_campaigns=0,
            pending_tasks=0,
            completed_today=0,
            campaigns=[]
        )


@router.get("/health")
async def status_health():
    """상태 API 헬스체크"""
    return {"status": "ok"}
