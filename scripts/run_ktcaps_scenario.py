#!/usr/bin/env python3
"""
KT캡스 블로그 체류 시나리오

목표:
1. "캡스 위약금" 검색
2. 메인 검색에서 특정 제목 찾기 (없으면 블로그 탭)
3. 블로그 글 진입
4. 불규칙 스크롤로 3분+ 체류
5. 공유버튼 클릭 후 종료
"""

import asyncio
import argparse
import random
import sys
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.shared.smart_executor import SmartExecutor, ExecutorConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# 타겟 블로그 제목 키워드
TARGET_KEYWORDS = [
    "위약금 노예",
    "KT캡스 계약",
    "렌탈 비용 폭탄",
    "숨겨진 렌탈",
    "따져봐야"
]


async def find_target_blog(executor: SmartExecutor) -> bool:
    """현재 화면에서 타겟 블로그 찾기"""
    await executor.refresh_ui()
    tree = executor._last_ui

    if not tree:
        return False

    for elem in tree.all_elements:
        text = elem.text.strip() if elem.text else ""
        if len(text) < 10:
            continue

        # 키워드 매칭
        matched = sum(1 for kw in TARGET_KEYWORDS if kw in text)
        if matched >= 2:  # 2개 이상 키워드 매칭
            logger.info(f"타겟 블로그 발견: {text[:50]}...")
            result = await executor._tap_element(elem)
            return result.success

    return False


async def irregular_scroll(executor: SmartExecutor, duration_sec: int = 180):
    """
    불규칙한 스크롤로 체류시간 확보

    - 스크롤 거리: 100~500px 랜덤
    - 대기 시간: 2~8초 랜덤
    - 가끔 위로 스크롤 (되돌아보기)
    - 중간에 멈춤 (읽는 시간)
    """
    start_time = asyncio.get_event_loop().time()
    scroll_count = 0

    logger.info(f"불규칙 스크롤 시작 (목표: {duration_sec}초)")

    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        remaining = duration_sec - elapsed

        if remaining <= 0:
            break

        scroll_count += 1

        # 스크롤 방향 결정 (10% 확률로 위로)
        direction = "up" if random.random() < 0.1 else "down"

        # 스크롤 거리 랜덤
        distance = random.randint(100, 450)

        # 스크롤 속도 랜덤
        speed = random.choice(["slow", "medium", "medium", "fast"])

        logger.info(
            f"[{scroll_count}] 스크롤 {direction} {distance}px ({speed}) "
            f"- 경과: {elapsed:.0f}초 / 남은: {remaining:.0f}초"
        )

        ctx = await executor.execute(
            "scroll",
            direction=direction,
            distance=distance,
            speed=speed
        )

        # 대기 시간 랜덤 (읽는 시간 시뮬레이션)
        wait_base = random.uniform(2, 6)

        # 가끔 더 오래 멈춤 (집중해서 읽는 척)
        if random.random() < 0.2:
            wait_base += random.uniform(3, 8)
            logger.info(f"  → 집중 읽기 모드: {wait_base:.1f}초 대기")

        await asyncio.sleep(wait_base)

    logger.info(f"스크롤 완료: 총 {scroll_count}회, {duration_sec}초 체류")


async def click_engagement_button(executor: SmartExecutor) -> bool:
    """
    참여 버튼 클릭 (공유, 이웃추가, 좋아요 등)

    Chrome 웹뷰에서는 공유 버튼이 없을 수 있으므로
    다양한 참여 버튼을 시도합니다.
    """
    logger.info("참여 버튼 찾는 중...")

    # 참여 버튼 키워드 (우선순위 순)
    engagement_keywords = [
        "이웃추가", "이웃 추가",
        "공유", "share",
        "좋아요", "like",
        "댓글", "comment",
        "구독", "팔로우"
    ]

    # 먼저 상단으로 올라가서 버튼 찾기
    logger.info("상단으로 이동...")
    for _ in range(5):
        await executor.scroll(direction="up", distance=800, speed="fast")
        await asyncio.sleep(0.5)

    await asyncio.sleep(1)
    await executor.refresh_ui()
    tree = executor._last_ui

    if not tree:
        return False

    # 모든 요소에서 참여 버튼 찾기
    for kw in engagement_keywords:
        for elem in tree.all_elements:
            text = (elem.text or elem.content_desc or "")
            if kw in text and elem.clickable:
                logger.info(f"참여 버튼 발견: '{text[:30]}' at {elem.center}")
                result = await executor._tap_element(elem)
                if result.success:
                    return True

    # 못 찾으면 브라우저 메뉴 버튼 시도 (점 3개)
    logger.info("브라우저 메뉴 버튼 시도...")
    for elem in tree.all_elements:
        text = (elem.text or elem.content_desc or "").lower()
        if "옵션" in text or "더보기" in text or "menu" in text:
            logger.info(f"메뉴 버튼 발견: {text[:30]}")
            result = await executor._tap_element(elem)
            return result.success

    logger.info("참여 버튼을 찾지 못함")
    return False


async def run_ktcaps_scenario(device_serial: str, dwell_time: int = 180):
    """
    KT캡스 블로그 체류 시나리오 실행

    Args:
        device_serial: 디바이스 시리얼
        dwell_time: 체류 시간 (초), 기본 180초 (3분)
    """
    print("\n" + "=" * 70)
    print("  KT캡스 블로그 체류 시나리오")
    print("=" * 70)
    print(f"  시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  목표 체류: {dwell_time}초 ({dwell_time // 60}분 {dwell_time % 60}초)")
    print("=" * 70)

    # 설정
    config = ExecutorConfig(
        device_serial=device_serial,
        lifecycle_enabled=True,
        capture_before=True,
        capture_after=True,
        log_actions=True
    )

    executor = SmartExecutor(config=config)
    await executor.setup()

    session_start = asyncio.get_event_loop().time()

    try:
        # Step 1: 네이버 검색
        print("\n[Step 1] 네이버 검색: '캡스 위약금'")
        ctx = await executor.execute(
            "open_url",
            url="https://m.search.naver.com/search.naver?query=캡스 위약금"
        )
        print(f"  결과: {ctx.result.message}")
        await asyncio.sleep(4)

        # Step 2: 메인 검색 결과에서 타겟 블로그 찾기
        print("\n[Step 2] 메인 검색 결과에서 타겟 블로그 찾기")

        found = await find_target_blog(executor)

        if found:
            print("  ✓ 메인 검색에서 타겟 블로그 발견!")
        else:
            # 스크롤해서 더 찾아보기
            print("  메인에서 미발견, 스크롤 후 재검색...")
            for i in range(3):
                await executor.scroll(direction="down", distance=500)
                await asyncio.sleep(1.5)
                found = await find_target_blog(executor)
                if found:
                    print(f"  ✓ 스크롤 {i + 1}회 후 발견!")
                    break

        if not found:
            # Step 2-1: 블로그 탭으로 이동
            print("\n[Step 2-1] 메인에서 미발견, 블로그 탭으로 이동")
            ctx = await executor.execute("tap_text", text="블로그", exact=True)
            print(f"  결과: {ctx.result.message}")
            await asyncio.sleep(3)

            # 블로그 탭에서 찾기
            print("\n[Step 2-2] 블로그 탭에서 타겟 찾기")
            for i in range(5):
                found = await find_target_blog(executor)
                if found:
                    print(f"  ✓ 블로그 탭에서 발견! (스크롤 {i}회)")
                    break

                await executor.scroll(direction="down", distance=400)
                await asyncio.sleep(2)

        if not found:
            print("  ✗ 타겟 블로그를 찾지 못했습니다.")
            print("  → 첫 번째 블로그 포스트로 대체")
            ctx = await executor.execute("tap_blog", index=0)
            print(f"  결과: {ctx.result.message}")

        await asyncio.sleep(3)

        # Step 3: 블로그 글 체류 (불규칙 스크롤)
        print(f"\n[Step 3] 블로그 글 체류 ({dwell_time}초)")
        print("-" * 50)

        await irregular_scroll(executor, duration_sec=dwell_time)

        # Step 4: 참여 버튼 클릭 (이웃추가, 공유, 좋아요 등)
        print("\n[Step 4] 참여 버튼 클릭")
        engagement_clicked = await click_engagement_button(executor)

        if engagement_clicked:
            print("  ✓ 참여 버튼 클릭 성공")
            await asyncio.sleep(2)
            # 다이얼로그 닫기
            await executor.back()
        else:
            print("  ✗ 참여 버튼을 찾지 못함 (정상 종료)")

        # 세션 종료
        session_end = asyncio.get_event_loop().time()
        total_time = session_end - session_start

        print("\n" + "=" * 70)
        print("  세션 완료")
        print("=" * 70)
        print(f"  종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  총 체류 시간: {total_time:.0f}초 ({total_time / 60:.1f}분)")
        print(f"  목표 달성: {'✓' if total_time >= dwell_time else '✗'}")
        print("=" * 70)

        return total_time >= dwell_time

    except Exception as e:
        logger.error(f"시나리오 실행 중 오류: {e}")
        raise


async def main():
    parser = argparse.ArgumentParser(description="KT캡스 블로그 체류 시나리오")
    parser.add_argument("--device", "-d", required=True, help="Device serial")
    parser.add_argument(
        "--dwell-time", "-t",
        type=int,
        default=180,
        help="체류 시간 (초), 기본 180초"
    )

    args = parser.parse_args()

    success = await run_ktcaps_scenario(
        device_serial=args.device,
        dwell_time=args.dwell_time
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
