"""
단일 방문 실행
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional

from src.shared.persona_manager.device_identity import DeviceIdentityManager
from src.shared.device_tools.adb_enhanced import EnhancedAdbTools
from src.shared.naver_chrome_use.cdp_client import CdpClient

from .adb_utils import adb
from .config import BLOG_URL, CHROME_PACKAGE, REFERRER_BASE
from .dwell import simulate_dwell
from .persona import update_persona_after_visit
from .session import reset_session_cookies, rotate_ip

logger = logging.getLogger("boost")


async def set_geolocation(cdp: CdpClient, location: Dict[str, Any]):
    """CDP Emulation.setGeolocationOverride로 브라우저 위치 설정"""
    lat = location.get("latitude")
    lng = location.get("longitude")
    acc = location.get("accuracy", 10)
    if lat is None or lng is None:
        return
    try:
        await cdp._send_cdp_command("Emulation.setGeolocationOverride", {
            "latitude": float(lat),
            "longitude": float(lng),
            "accuracy": float(acc),
        })
        logger.debug(f"위치 설정: {lat:.4f}, {lng:.4f}")
    except Exception as e:
        logger.debug(f"위치 설정 실패 (무시): {e}")


async def execute_single_visit(
    visit_num: int,
    total: int,
    sb,
    identity_mgr: DeviceIdentityManager,
    adb_tools: EnhancedAdbTools,
    cdp: CdpClient,
    keyword: str,
    used_persona_ids: set = None,
) -> bool:
    """
    단일 블로그 방문 실행

    1. Supabase에서 랜덤 페르소나 가져오기
    2. ANDROID_ID 변경
    3. 쿠키 삭제 + IP 회전
    4. CDP referrer 네비게이션
    5. 휴먼라이크 체류
    6. Supabase에 방문 기록 저장
    """
    from .persona import fetch_random_persona

    tag = f"[{visit_num}/{total}]"

    try:
        # --- 1. 세션 리셋 (2번째 방문부터) ---
        if visit_num > 1:
            logger.info(f"{tag} 세션 리셋...")
            reset_session_cookies()
            rotate_ip()
        else:
            reset_session_cookies()

        # --- 2. Supabase에서 랜덤 페르소나 (중복 방지) ---
        persona = fetch_random_persona(sb, used_ids=used_persona_ids)
        if not persona:
            logger.error(f"{tag} 페르소나 없음")
            return False

        device_config = persona.get("device_config", {})
        android_id = device_config.get("android_id", "")
        persona_name = persona.get("name", "unknown")
        persona_id = persona["id"]
        behavior = persona.get("behavior_profile", {})
        location = persona.get("location", {})

        if used_persona_ids is not None:
            used_persona_ids.add(persona_id)

        if not android_id or len(android_id) != 16:
            logger.error(f"{tag} 잘못된 android_id: {android_id}")
            return False

        # --- 3. ANDROID_ID 변경 ---
        adb("shell", "am", "force-stop", CHROME_PACKAGE)
        time.sleep(0.5)

        result = await identity_mgr.set_android_id(android_id)
        if not result.success:
            logger.error(f"{tag} ANDROID_ID 변경 실패: {result.error_message}")
            return False

        region = location.get("region", "?")
        logger.info(f"{tag} ID={android_id[:8]} persona={persona_name} loc={region}")

        # --- 4. CDP referrer 네비게이션 ---
        adb("shell", "am", "start", "-a", "android.intent.action.VIEW",
            "-d", "about:blank", CHROME_PACKAGE)
        await asyncio.sleep(3)

        cdp._connected = False
        ok = await cdp.connect()
        if not ok:
            logger.error(f"{tag} CDP 연결 실패")
            return False

        # --- 4-1. CDP 위치 오버라이드 ---
        if location:
            await set_geolocation(cdp, location)

        referrer = REFERRER_BASE + keyword.replace(" ", "+")
        ok = await cdp.navigate_with_referrer(
            url=BLOG_URL,
            referrer=referrer,
            wait_load=5,
        )

        if not ok:
            logger.error(f"{tag} CDP navigate 실패")
            return False

        doc_ref = await cdp.get_document_referrer()
        logger.info(f'{tag} referrer="{doc_ref}" kw="{keyword}"')

        # --- 5. 휴먼라이크 체류 ---
        dwell_sec, scroll_count, scroll_depth = await simulate_dwell(
            adb_tools, behavior
        )
        logger.info(f"{tag} 체류 {dwell_sec}s ({scroll_count}회 스크롤)")

        # --- 6. Supabase에 기록 ---
        try:
            update_persona_after_visit(
                sb, persona_id, dwell_sec, scroll_count, scroll_depth,
                success=True, keyword=keyword,
            )
        except Exception as e:
            logger.warning(f"{tag} Supabase 기록 실패: {e}")

        logger.info(f"{tag} 방문 완료 ({dwell_sec}s)")
        return True

    except Exception as e:
        logger.error(f"{tag} 오류: {e}", exc_info=True)
        return False
