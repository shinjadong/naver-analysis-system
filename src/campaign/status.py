"""
상태 확인
"""

from datetime import date

from .config import CAMPAIGN_START_DATE, DAILY_BASE, GROWTH_RATE
from .persona import get_supabase


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


def show_status():
    """Supabase 페르소나 및 캠페인 상태 출력"""
    sb = get_supabase()

    idle_resp = sb.table("personas").select("id", count="exact").eq("status", "idle").execute()
    active_resp = sb.table("personas").select("id", count="exact").eq("status", "active").execute()
    total_resp = sb.table("personas").select("id", count="exact").execute()

    idle_count = idle_resp.count or 0
    active_count = active_resp.count or 0
    total_count = total_resp.count or 0

    today = date.today().isoformat()
    sessions_resp = (
        sb.table("persona_sessions")
        .select("id", count="exact")
        .gte("started_at", f"{today}T00:00:00")
        .eq("campaign_type", "traffic")
        .execute()
    )
    today_sessions = sessions_resp.count or 0

    today_success = get_today_success_count(sb)

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
