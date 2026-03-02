"""
CLI 엔트리포인트
"""

import argparse
import asyncio
import logging

from .runner import run_campaign, run_auto
from .status import show_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)


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
