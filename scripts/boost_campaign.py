#!/usr/bin/env python3
"""
boost_campaign.py - 트래픽 부스팅 캠페인 러너 (Supabase 페르소나)

Supabase personas 테이블(1000+개)에서 랜덤 페르소나를 가져와
CDP referrer + 휴먼라이크 스크롤로 블로그 방문을 시뮬레이션합니다.

컴포넌트:
- Supabase personas  → 랜덤 페르소나 선택 (android_id, behavior_profile)
- DeviceIdentityManager → ANDROID_ID 변경 (루팅)
- EnhancedAdbTools     → 휴먼라이크 스크롤/탭 (베지어 커브)
- CdpClient            → CDP referrer 네비게이션

세션 리셋 (FRE 방지):
- root rm 쿠키/캐시만 삭제 (pm clear 절대 금지)
- svc data disable/enable IP 회전 (airplane mode X → ADB 끊김)

사용법:
    # 단일 테스트
    python scripts/boost_campaign.py --target 1

    # 즉시 실행
    python scripts/boost_campaign.py --target 50 --now

    # 자동 모드 (x1.23 일일 성장)
    python scripts/boost_campaign.py --auto

    # 상태 확인
    python scripts/boost_campaign.py --status
"""

import argparse
import asyncio
import logging
import os
import random
import subprocess
import sys
import time
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, Any

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from supabase import create_client

from src.shared.persona_manager.device_identity import DeviceIdentityManager
from src.shared.device_tools.adb_enhanced import EnhancedAdbTools, AdbConfig
from src.shared.naver_chrome_use.cdp_client import CdpClient

# ============================================================================
# 설정
# ============================================================================

DEVICE_SERIAL = "R3CW60BHSAT"
CDP_PORT = 9333  # 9222는 블로그포스팅 cron 점유

BLOG_URL = "https://m.blog.naver.com/tlswkehd_/224174022465"
REFERRER_BASE = "https://m.search.naver.com/search.naver?where=m_blog&query="

KEYWORDS = [
    "ktcctv가격",
    "ktcctv설치가격",
    "cctv설치가격",
    "cctv설치비용",
]

# 캠페인 시작일 (일일 목표 계산 기준)
CAMPAIGN_START_DATE = date(2026, 2, 6)
DAILY_BASE = 50
GROWTH_RATE = 1.23

# Chrome 데이터 경로 (루팅)
CHROME_DATA_DIR = "/data/data/com.android.chrome/app_chrome/Default"
CHROME_PACKAGE = "com.android.chrome"

# 체류시간 범위 (초)
MIN_DWELL = 60
MAX_DWELL = 180

# 방문 간 쿨다운 범위 (초) - --now 모드 전용
MIN_VISIT_GAP = 15
MAX_VISIT_GAP = 35

# 분산 모드 (--auto) 시간 설정
SPREAD_START_HOUR = 7   # 방문 시작 시각
SPREAD_END_HOUR = 23    # 방문 종료 시각
SPREAD_MIN_GAP = 120    # 최소 간격 (2분)
SPREAD_MAX_GAP = 900    # 최대 간격 (15분)

# 시간대별 트래픽 가중치 (높을수록 해당 시간에 방문 집중)
# 점심·저녁 피크, 아침·심야 낮음 → 자연스러운 검색 유입 패턴
HOURLY_WEIGHTS = {
    7: 0.5,  8: 0.7,  9: 1.0, 10: 1.2, 11: 1.3,
    12: 1.5, 13: 1.3, 14: 1.0, 15: 0.9, 16: 0.9,
    17: 1.1, 18: 1.3, 19: 1.5, 20: 1.4, 21: 1.2, 22: 0.7,
}

# ============================================================================
# 로깅
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("boost")


# ============================================================================
# Supabase 페르소나 관리
# ============================================================================

# 페르소나 Supabase 프로젝트 (pkehcfbjotctvneordob)
# .env의 SUPABASE_URL은 블로그 프로젝트(gtokhmxsloucrvetmurm)를 가리키므로
# 페르소나 전용 환경변수를 우선 사용
PERSONA_SUPABASE_URL = "https://pkehcfbjotctvneordob.supabase.co"
PERSONA_SUPABASE_KEY = os.getenv("PERSONA_SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_SERVICE_KEY_PERSONA", ""))


def get_supabase():
    """페르소나 Supabase 클라이언트 생성"""
    url = os.getenv("PERSONA_SUPABASE_URL", PERSONA_SUPABASE_URL)
    key = os.getenv("PERSONA_SUPABASE_SERVICE_KEY", PERSONA_SUPABASE_KEY)
    if not key:
        # CLAUDE.md에 문서화된 서비스 키 사용
        key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBrZWhjZmJqb3RjdHZuZW9yZG9iIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzE5MjY4MSwiZXhwIjoyMDY4NzY4NjgxfQ.fn1IxRxjJZ6gihy_SCvyQrT6Vx3xb1yMaVzztOsLeyk"
    return create_client(url, key)


def fetch_random_persona(
    sb,
    used_ids: set = None,
    max_retries: int = 10,
) -> Optional[Dict[str, Any]]:
    """
    Supabase에서 중복 없이 랜덤 페르소나 1개 가져오기
    used_ids에 포함된 페르소나는 건너뛴다.
    """
    if used_ids is None:
        used_ids = set()

    count_resp = (
        sb.table("personas")
        .select("id", count="exact")
        .eq("status", "idle")
        .execute()
    )
    total = count_resp.count or 0
    if total == 0:
        logger.error("idle 페르소나 없음")
        return None

    for _ in range(max_retries):
        offset = random.randint(0, max(0, total - 1))
        resp = (
            sb.table("personas")
            .select("*")
            .eq("status", "idle")
            .range(offset, offset)
            .execute()
        )
        if resp.data and resp.data[0]["id"] not in used_ids:
            return resp.data[0]

    # 최대 재시도 초과 시 아무거나 반환
    if resp and resp.data:
        return resp.data[0]
    return None


def update_persona_after_visit(
    sb,
    persona_id: str,
    dwell_sec: int,
    scroll_count: int,
    scroll_depth: float,
    success: bool,
    keyword: str,
):
    """방문 후 Supabase 페르소나 통계 업데이트 + persona_sessions 기록"""
    now = datetime.now().isoformat()

    # 페르소나 통계 업데이트
    update_data = {"last_active_at": now, "updated_at": now}
    if success:
        cur = sb.table("personas").select("total_sessions, total_dwell_time").eq("id", persona_id).execute()
        if cur.data:
            update_data["total_sessions"] = (cur.data[0].get("total_sessions") or 0) + 1
            update_data["total_dwell_time"] = (cur.data[0].get("total_dwell_time") or 0) + dwell_sec
    sb.table("personas").update(update_data).eq("id", persona_id).execute()

    # persona_sessions 기록
    sb.table("persona_sessions").insert({
        "persona_id": persona_id,
        "device_serial": DEVICE_SERIAL,
        "mission": {
            "type": "blog_boost",
            "keyword": keyword,
            "blog_url": BLOG_URL,
        },
        "success": success,
        "duration_sec": dwell_sec,
        "scroll_count": scroll_count,
        "scroll_depth": float(scroll_depth),
        "started_at": now,
        "completed_at": now,
        "status": "completed" if success else "failed",
        "campaign_type": "traffic",
    }).execute()


# ============================================================================
# ADB 유틸리티
# ============================================================================

def _adb(*args: str, timeout: int = 15) -> str:
    """ADB 명령 실행 유틸리티"""
    cmd = ["adb", "-s", DEVICE_SERIAL, *args]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""
    except Exception as e:
        logger.warning(f"ADB error: {e}")
        return ""


def _adb_root(shell_cmd: str, timeout: int = 15) -> str:
    """루트 ADB 쉘 명령"""
    return _adb("shell", f"su -c '{shell_cmd}'", timeout=timeout)


# ============================================================================
# 세션 리셋 (FRE 방지 - pm clear 사용 안 함)
# ============================================================================

def reset_session_cookies():
    """
    Chrome 쿠키/캐시만 삭제 (FRE 방지)

    pm clear 사용 시 Chrome First Run Experience가 다시 나타나므로
    루트로 쿠키/캐시 파일만 직접 삭제합니다.
    """
    _adb("shell", "am", "force-stop", CHROME_PACKAGE)
    time.sleep(1)

    _adb_root(f"rm -rf {CHROME_DATA_DIR}/Cookies*")
    _adb_root(f"rm -rf {CHROME_DATA_DIR}/Cache*")
    _adb_root(f"rm -rf {CHROME_DATA_DIR}/GPUCache*")
    _adb_root(f"rm -rf {CHROME_DATA_DIR}/Session*")
    _adb_root(f"rm -rf {CHROME_DATA_DIR}/Web\\ Data*")

    logger.debug("쿠키/캐시 삭제 완료")


def rotate_ip():
    """
    모바일 데이터 재연결로 IP 회전

    airplane mode는 ADB 연결이 끊기므로
    svc data disable/enable 사용
    """
    _adb("shell", "svc", "data", "disable")
    time.sleep(2)
    _adb("shell", "svc", "data", "enable")
    time.sleep(5)
    logger.debug("IP 회전 완료")


# ============================================================================
# 휴먼라이크 체류 시뮬레이션
# ============================================================================

async def simulate_dwell(
    adb_tools: EnhancedAdbTools,
    behavior: Dict[str, Any],
) -> tuple[int, int, float]:
    """
    Supabase behavior_profile 기반 휴먼라이크 체류 시뮬레이션

    behavior 구조:
        scroll_speed: float (0.5~2.0)
        avg_dwell_time: int (초)
        pause_probability: float (0~0.5)
    """
    scroll_speed = behavior.get("scroll_speed", 1.0)
    avg_dwell = behavior.get("avg_dwell_time", 120)
    pause_prob = behavior.get("pause_probability", 0.2)

    dwell_sec = random.randint(
        max(MIN_DWELL, int(avg_dwell * 0.6)),
        min(MAX_DWELL, int(avg_dwell * 1.4)),
    )

    scroll_interval = max(2, int(4 / scroll_speed))
    num_scrolls = max(4, dwell_sec // scroll_interval)

    start = time.time()
    scroll_count = 0
    max_scroll_y = 0

    # 화면 크기
    sw = adb_tools.config.screen_width or 1080
    sh = adb_tools.config.screen_height or 2400
    center_x = sw // 2

    await asyncio.sleep(random.uniform(1, 2.5))

    for i in range(num_scrolls):
        elapsed = time.time() - start
        if elapsed >= dwell_sec:
            break

        roll = random.random()

        if roll < 0.15 and scroll_count > 2:
            # 위로 스크롤 (되돌아 읽기) - input swipe (빠름)
            dist = random.randint(200, 400)
            start_y = int(sh * 0.3)
            dur = random.randint(300, 600)
            await adb_tools.swipe(center_x, start_y, center_x, start_y + dist,
                                  duration_ms=dur, use_curved_path=False)
        elif roll < 0.25 and scroll_count > 0:
            # 읽기 멈춤
            await asyncio.sleep(random.uniform(1.5, 4))
        # elif roll < 0.35 and scroll_count > 1:
        #     # 탭 액션 (비활성화 - 이미지 뷰어 문제)
        #     tap_x = random.randint(int(sw * 0.1), int(sw * 0.9))
        #     tap_y = random.randint(int(sh * 0.25), int(sh * 0.75))
        #     await adb_tools.tap(tap_x, tap_y)
        #     await asyncio.sleep(random.uniform(0.5, 1.5))
        #     _adb("shell", "input", "keyevent", "KEYCODE_BACK")
        else:
            # 아래로 스크롤 - input swipe (빠름)
            dist = random.randint(300, 700)
            start_y = int(sh * 0.7)
            dur = random.randint(300, 600)
            await adb_tools.swipe(center_x, start_y, center_x, start_y - dist,
                                  duration_ms=dur, use_curved_path=False)
            scroll_count += 1
            max_scroll_y += dist

        pause_base = scroll_interval + random.uniform(-1, 1)
        if random.random() < pause_prob:
            pause_base += random.uniform(1, 3)

        await asyncio.sleep(max(0.8, pause_base))

    actual_dwell = int(time.time() - start)
    scroll_depth = min(1.0, max_scroll_y / 12000)

    return actual_dwell, scroll_count, scroll_depth


# ============================================================================
# 단일 방문 실행
# ============================================================================

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
    tag = f"[{visit_num}/{total}]"

    try:
        # --- 1. 세션 리셋 (2번째 방문부터) ---
        if visit_num > 1:
            logger.info(f"{tag} 세션 리셋...")
            reset_session_cookies()
            rotate_ip()
        else:
            # 첫 방문: Chrome 강제종료 + 쿠키 삭제 (깨끗한 상태)
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

        # 사용 기록
        if used_persona_ids is not None:
            used_persona_ids.add(persona_id)

        if not android_id or len(android_id) != 16:
            logger.error(f"{tag} 잘못된 android_id: {android_id}")
            return False

        # --- 3. ANDROID_ID 변경 ---
        _adb("shell", "am", "force-stop", CHROME_PACKAGE)
        time.sleep(0.5)

        result = await identity_mgr.set_android_id(android_id)
        if not result.success:
            logger.error(f"{tag} ANDROID_ID 변경 실패: {result.error_message}")
            return False

        region = location.get("region", "?")
        logger.info(f"{tag} ID={android_id[:8]} persona={persona_name} loc={region}")

        # --- 4. CDP referrer 네비게이션 ---
        _adb("shell", "am", "start", "-a", "android.intent.action.VIEW",
             "-d", "about:blank", CHROME_PACKAGE)
        await asyncio.sleep(3)

        # CDP 재연결 (Chrome 재시작 후 WebSocket URL 변경됨)
        cdp._connected = False
        ok = await cdp.connect()
        if not ok:
            logger.error(f"{tag} CDP 연결 실패")
            return False

        # --- 4-1. CDP 위치 오버라이드 (페르소나 지역 반영) ---
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


# ============================================================================
# 캠페인 실행
# ============================================================================

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

    # 현재 시간대 가중치 적용 (가중치 높으면 간격 짧게 → 방문 집중)
    hour = now.hour
    weight = HOURLY_WEIGHTS.get(hour, 1.0)
    adjusted_gap = base_gap / weight

    # ±40% 랜덤 변동
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
        logger.info(f"분산 시간: {now.strftime('%H:%M')}~{SPREAD_END_HOUR}:00, "
                     f"평균 간격 {avg_gap/60:.1f}분")

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

    # 루트 확인
    await identity_mgr.ensure_root()

    success_count = 0
    fail_streak = 0
    used_persona_ids: set = set()

    for i in range(1, target + 1):
        keyword = random.choice(KEYWORDS)
        logger.info(f"--- [{i}/{target}] \"{keyword}\" ---")

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


# ============================================================================
# 상태 확인
# ============================================================================

def show_status():
    """Supabase 페르소나 및 캠페인 상태 출력"""
    sb = get_supabase()

    # 페르소나 상태별 수
    idle_resp = sb.table("personas").select("id", count="exact").eq("status", "idle").execute()
    active_resp = sb.table("personas").select("id", count="exact").eq("status", "active").execute()
    total_resp = sb.table("personas").select("id", count="exact").execute()

    idle_count = idle_resp.count or 0
    active_count = active_resp.count or 0
    total_count = total_resp.count or 0

    # 오늘 세션 수
    today = date.today().isoformat()
    sessions_resp = (
        sb.table("persona_sessions")
        .select("id", count="exact")
        .gte("started_at", f"{today}T00:00:00")
        .eq("campaign_type", "traffic")
        .execute()
    )
    today_sessions = sessions_resp.count or 0

    success_resp = (
        sb.table("persona_sessions")
        .select("id", count="exact")
        .gte("started_at", f"{today}T00:00:00")
        .eq("campaign_type", "traffic")
        .eq("success", True)
        .execute()
    )
    today_success = success_resp.count or 0

    # 일일 목표 계산
    days = (date.today() - CAMPAIGN_START_DATE).days
    daily_target = int(DAILY_BASE * (GROWTH_RATE ** max(0, days)))

    print(f"\n{'='*60}")
    print(f"  부스팅 캠페인 상태 (Supabase)")
    print(f"{'='*60}")
    print(f"  캠페인 시작일: {CAMPAIGN_START_DATE}")
    print(f"  경과일: D+{days}")
    print(f"  오늘 목표: {daily_target}회")
    print(f"  성장률: x{GROWTH_RATE}")
    print(f"{'='*60}")
    print(f"  페르소나 총: {total_count}개")
    print(f"    idle: {idle_count}")
    print(f"    active: {active_count}")
    print(f"{'='*60}")
    print(f"  오늘 세션: {today_sessions}회")
    print(f"    성공: {today_success}")
    print(f"    실패: {today_sessions - today_success}")
    print(f"    잔여: {max(0, daily_target - today_success)}")
    print(f"{'='*60}\n")


# ============================================================================
# 자동 모드
# ============================================================================

def get_today_success_count(sb) -> int:
    """오늘 성공한 세션 수 (Supabase)"""
    today = date.today().isoformat()
    resp = (
        sb.table("persona_sessions")
        .select("id", count="exact")
        .gte("started_at", f"{today}T00:00:00")
        .eq("campaign_type", "traffic")
        .eq("success", True)
        .execute()
    )
    return resp.count or 0


async def run_auto():
    """
    자동 모드: 일일 목표를 계산하고, 이미 완료된 분량을 차감하여 실행

    cron:
    0 7 * * * cd /home/tlswkehd/projects/cctv/ai-project && \
      .venv/bin/python scripts/boost_campaign.py --auto 2>&1 >> logs/boost.log
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


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="트래픽 부스팅 캠페인 러너 (Supabase)")
    parser.add_argument("--target", type=int, default=0, help="방문 목표 수")
    parser.add_argument("--now", action="store_true", help="즉시 실행")
    parser.add_argument("--auto", action="store_true", help="자동 모드 (일일 목표 계산)")
    parser.add_argument("--status", action="store_true", help="상태 확인")

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.auto:
        asyncio.run(run_auto())
    elif args.target > 0:
        asyncio.run(run_campaign(target=args.target, now_mode=args.now))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
