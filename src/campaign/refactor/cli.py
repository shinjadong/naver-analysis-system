"""
CLI 엔트리포인트
"""

import argparse
import asyncio
import logging
import os
from pathlib import Path
from datetime import date
from typing import Optional

from supabase import create_client

from .campaigns import CampaignRunner


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cli")


# 캠페인 파일 경로
CAMPAIGN_FILE = Path(__file__).parent / "campaigns" / "blog_boost.yaml"

# Supabase
SUPABASE_URL = "https://pkehcfbjotctvneordob.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("PERSONA_SUPABASE_SERVICE_KEY")
if not SUPABASE_KEY:
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBrZWhjZmJqb3RjdHZuZW9yZG9iIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzE5MjY4MSwiZXhwIjoyMDY4NzY4NjgxfQ.fn1IxRxjJZ6gihy_SCvyQrT6Vx3xb1yMaVzztOsLeyk"

# 자동 모드 설정
CAMPAIGN_START_DATE = date(2026, 2, 6)
DAILY_BASE = 50
GROWTH_RATE = 1.23


def get_supabase():
    """Supabase 클라이언트 생성"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_today_success_count(sb) -> int:
    """오늘 성공한 세션 수"""
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
    print(f"  부스팅 캠페인 상태 (모듈화 버전)")
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


async def run_auto():
    """자동 모드: 일일 목표 계산 후 실행"""
    days = (date.today() - CAMPAIGN_START_DATE).days
    daily_target = int(DAILY_BASE * (GROWTH_RATE ** max(0, days)))

    sb = get_supabase()
    done = get_today_success_count(sb)
    remaining = max(0, daily_target - done)

    logger.info(f"자동 모드: D+{days}, 목표={daily_target}, 완료={done}, 잔여={remaining}")

    if remaining <= 0:
        logger.info("오늘 목표 달성 완료!")
        return

    runner = CampaignRunner(str(CAMPAIGN_FILE))
    await runner.run_campaign(target=remaining, now_mode=False)


def main():
    """CLI 메인"""
    parser = argparse.ArgumentParser(
        description="트래픽 부스팅 캠페인 러너 (모듈화 버전)"
    )
    parser.add_argument("--target", type=int, default=0, help="방문 목표 수")
    parser.add_argument("--now", action="store_true", help="즉시 실행")
    parser.add_argument("--auto", action="store_true", help="자동 모드 (일일 목표 계산)")
    parser.add_argument("--status", action="store_true", help="상태 확인")
    parser.add_argument("--campaign", type=str, default=None,
                        help="캠페인 YAML 파일 (기본: blog_boost.yaml)")

    args = parser.parse_args()

    # 캠페인 파일 결정
    if args.campaign:
        campaign_path = Path(args.campaign)
        if not campaign_path.is_absolute():
            # 상대 경로면 campaigns 디렉토리에서 찾기
            campaign_path = Path(__file__).parent / "campaigns" / args.campaign
        if not campaign_path.exists():
            print(f"캠페인 파일 없음: {campaign_path}")
            return
        campaign_file = str(campaign_path)
    else:
        campaign_file = str(CAMPAIGN_FILE)

    if args.status:
        show_status()
    elif args.auto:
        asyncio.run(run_auto())
    elif args.target > 0:
        runner = CampaignRunner(campaign_file)
        asyncio.run(runner.run_campaign(target=args.target, now_mode=args.now))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
