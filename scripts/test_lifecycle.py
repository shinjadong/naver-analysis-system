#!/usr/bin/env python3
"""
Action Lifecycle 테스트

SmartExecutor의 OBSERVE → ACT → VERIFY 워크플로우 테스트
"""

import asyncio
import argparse
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.shared.smart_executor import SmartExecutor, ExecutorConfig

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)


async def test_lifecycle(device_serial: str):
    """Lifecycle 테스트"""

    print("\n" + "=" * 60)
    print("  Action Lifecycle 테스트")
    print("=" * 60)

    # Lifecycle 활성화된 설정
    config = ExecutorConfig(
        device_serial=device_serial,
        lifecycle_enabled=True,
        capture_before=True,
        capture_after=True,
        capture_screenshot=False,  # 스크린샷은 일단 비활성
        log_actions=True
    )

    executor = SmartExecutor(config=config)
    await executor.setup()

    print(f"\n[설정]")
    print(f"  Lifecycle: {config.lifecycle_enabled}")
    print(f"  Before 스냅샷: {config.capture_before}")
    print(f"  After 스냅샷: {config.capture_after}")
    print(f"  스크린샷: {config.capture_screenshot}")

    # 테스트 1: URL 열기
    print("\n" + "-" * 60)
    print("[테스트 1] URL 열기 (execute)")
    print("-" * 60)

    ctx = await executor.execute(
        "open_url",
        url="https://m.search.naver.com/search.naver?query=서울맛집"
    )

    print(f"  성공: {ctx.success}")
    print(f"  메시지: {ctx.result.message if ctx.result else 'N/A'}")
    if ctx.snapshot_before:
        print(f"  [BEFORE] 요소: {ctx.snapshot_before.total_elements}개")
    if ctx.snapshot_after:
        print(f"  [AFTER] 요소: {ctx.snapshot_after.total_elements}개")

    await asyncio.sleep(4)

    # 테스트 2: 블로그 탭 클릭
    print("\n" + "-" * 60)
    print("[테스트 2] 텍스트로 탭 (블로그)")
    print("-" * 60)

    ctx = await executor.execute(
        "tap_text",
        text="블로그",
        exact=True
    )

    print(f"  성공: {ctx.success}")
    print(f"  메시지: {ctx.result.message if ctx.result else 'N/A'}")
    if ctx.snapshot_before:
        print(f"  [BEFORE] 클릭 가능: {ctx.snapshot_before.clickable_count}개")
        print(f"  [BEFORE] 상위 요소:")
        for elem in ctx.snapshot_before.elements_summary[:5]:
            print(f"    - '{elem['text']}' at {elem['center']}")
    if ctx.snapshot_after:
        print(f"  [AFTER] 클릭 가능: {ctx.snapshot_after.clickable_count}개")

    await asyncio.sleep(3)

    # 테스트 3: 스크롤
    print("\n" + "-" * 60)
    print("[테스트 3] 스크롤")
    print("-" * 60)

    ctx = await executor.execute(
        "scroll",
        direction="down",
        distance=400
    )

    print(f"  성공: {ctx.success}")
    print(f"  메시지: {ctx.result.message if ctx.result else 'N/A'}")
    if ctx.snapshot_before and ctx.snapshot_after:
        before_count = ctx.snapshot_before.clickable_count
        after_count = ctx.snapshot_after.clickable_count
        print(f"  요소 변화: {before_count} → {after_count}")

    await asyncio.sleep(1)

    # 테스트 4: 블로그 포스트 탭
    print("\n" + "-" * 60)
    print("[테스트 4] 블로그 포스트 탭")
    print("-" * 60)

    ctx = await executor.execute(
        "tap_blog",
        index=0
    )

    print(f"  성공: {ctx.success}")
    print(f"  메시지: {ctx.result.message if ctx.result else 'N/A'}")
    if ctx.result and ctx.result.element:
        print(f"  탭한 제목: {ctx.result.element.text[:50]}...")
    if ctx.snapshot_before:
        print(f"  [BEFORE] 블로그 목록에서 {ctx.snapshot_before.clickable_count}개 요소")
    if ctx.snapshot_after:
        print(f"  [AFTER] 블로그 내부에서 {ctx.snapshot_after.clickable_count}개 요소")

    # 전체 로그 출력
    print("\n" + "-" * 60)
    print("[액션 로그]")
    print("-" * 60)
    print(executor.get_action_log(ctx))

    # 테스트 5: 뒤로가기
    print("\n" + "-" * 60)
    print("[테스트 5] 뒤로가기")
    print("-" * 60)

    ctx = await executor.execute("back")
    print(f"  성공: {ctx.success}")

    print("\n" + "=" * 60)
    print("  테스트 완료")
    print("=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="Action Lifecycle Test")
    parser.add_argument("--device", "-d", required=True, help="Device serial")
    args = parser.parse_args()

    await test_lifecycle(args.device)


if __name__ == "__main__":
    asyncio.run(main())
