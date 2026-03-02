"""
캠페인 실행 (분산/즉시/자동 모드)
"""

import asyncio
import logging
import random
from datetime import datetime, date

from src.shared.persona_manager.device_identity import DeviceIdentityManager
from src.shared.device_tools.adb_enhanced import EnhancedAdbTools, AdbConfig
from src.shared.naver_chrome_use.cdp_client import CdpClient

from .config import (
    DEVICE_SERIAL, CDP_PORT, BLOG_URL, KEYWORDS,
    CAMPAIGN_START_DATE, DAILY_BASE, GROWTH_RATE,
    MIN_VISIT_GAP, MAX_VISIT_GAP,
    SPREAD_END_HOUR, SPREAD_MIN_GAP, SPREAD_MAX_GAP,
    HOURLY_WEIGHTS,
)
from .persona import get_supabase
from .status import get_today_success_count
from .visit import execute_single_visit

logger = logging.getLogger("boost")


def _calc_spread_gap(target: int, remaining: int) -> float:
    """
    분산 모드 간격 계산

    현재 시각 ~ SPREAD_END_HOUR 사이에 remaining 회를 자연스럽게 분배.
    시간대별 가중치(HOURLY_WEIGHTS)로 점심/저녁 피크 반영.
    """
    now = datetime.now()
    end = now.replace(hour=SPREAD_END_HOUR, minute=0, second=0, microsecond=0)
    available_sec = max(0, (end - now).total_seconds())

    if available_sec < 300 or remaining <= 0:
        return random.randint(MIN_VISIT_GAP, MAX_VISIT_GAP)

    base_gap = available_sec / remaining

    hour = now.hour
    weight = HOURLY_WEIGHTS.get(hour, 1.0)
    adjusted_gap = base_gap / weight

    gap = adjusted_gap * random.uniform(0.6, 1.4)

    return max(SPREAD_MIN_GAP, min(gap, SPREAD_MAX_GAP))


async def run_campaign(target: int, now_mode: bool = False):
    """
    캠페인 실행

    now_mode=True:  짧은 간격(15~35초)으로 즉시 연속 실행 (테스트/수동)
    now_mode=False: 07~23시에 걸쳐 자연스럽게 분산 (시간대 가중치 적용)
    """
    mode_label = "즉시" if now_mode else "분산(07~23시)"
    logger.info(f"=== 부스팅 캠페인 시작 ({mode_label}) ===")
    logger.info(f"URL: {BLOG_URL}")
    logger.info(f"목표: {target}회")

    if not now_mode:
        now = datetime.now()
        end = now.replace(hour=SPREAD_END_HOUR, minute=0, second=0, microsecond=0)
        avail = max(0, (end - now).total_seconds())
        avg_gap = avail / target if target > 0 else 0
        logger.info(
            f"분산 시간: {now.strftime('%H:%M')}~{SPREAD_END_HOUR}:00, "
            f"평균 간격 {avg_gap/60:.1f}분"
        )

    sb = get_supabase()
    identity_mgr = DeviceIdentityManager(DEVICE_SERIAL)
    adb_tools = EnhancedAdbTools(AdbConfig(
        serial=DEVICE_SERIAL,
        action_interval_min_ms=50,
        action_interval_max_ms=150,
    ))
    cdp = CdpClient(device_serial=DEVICE_SERIAL, cdp_port=CDP_PORT)

    if not await adb_tools.connect(DEVICE_SERIAL):
        logger.error("ADB 연결 실패")
        return

    await identity_mgr.ensure_root()

    success_count = 0
    fail_streak = 0
    used_persona_ids: set = set()

    for i in range(1, target + 1):
        keyword = random.choice(KEYWORDS)
        logger.info(f'--- [{i}/{target}] "{keyword}" ---')

        ok = await execute_single_visit(
            visit_num=i,
            total=target,
            sb=sb,
            identity_mgr=identity_mgr,
            adb_tools=adb_tools,
            cdp=cdp,
            keyword=keyword,
            used_persona_ids=used_persona_ids,
        )

        if ok:
            success_count += 1
            fail_streak = 0
        else:
            fail_streak += 1
            if fail_streak >= 3:
                logger.warning("연속 3회 실패 - 60s 대기 후 CDP 재연결")
                await asyncio.sleep(60)
                cdp._connected = False
                await cdp.connect()
                fail_streak = 0

        if i < target:
            if now_mode:
                gap = random.randint(MIN_VISIT_GAP, MAX_VISIT_GAP)
            else:
                gap = _calc_spread_gap(target, remaining=target - i)

            gap_int = int(gap)
            logger.info(f"[{i}] 쿨다운 {gap_int}s ({gap_int/60:.1f}분)")
            await asyncio.sleep(gap)

    await cdp.disconnect()
    logger.info(f"=== 캠페인 완료: {success_count}/{target} 성공 ===")


async def run_auto():
    """
    자동 모드: 일일 목표를 계산하고, 이미 완료된 분량을 차감하여 실행
    """
    days = (date.today() - CAMPAIGN_START_DATE).days
    daily_target = int(DAILY_BASE * (GROWTH_RATE ** max(0, days)))

    sb = get_supabase()
    done = get_today_success_count(sb)
    remaining = max(0, daily_target - done)

    logger.info(f"자동 모드: D+{days}, 목표={daily_target}, 완료={done}, 잔여={remaining}")

    if remaining <= 0:
        logger.info("오늘 목표 달성 완료!")
        return

    await run_campaign(target=remaining, now_mode=False)
