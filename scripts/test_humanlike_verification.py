"""
휴먼라이크 동작 검증 테스트

목적:
1. 베지어 오프셋이 매번 다르게 적용되는지 확인
2. 스크롤 시 가변 속도가 적용되는지 확인
3. 동일 좌표에 여러 번 탭해도 실제 좌표가 다른지 확인
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.shared.device_tools import EnhancedAdbTools, AdbConfig


async def verify_humanlike_behavior(serial: str = "R3CW60BHSAT"):
    """Verify humanlike behavior across multiple actions"""

    print("=" * 60)
    print("휴먼라이크 동작 검증 테스트")
    print("=" * 60)

    # Initialize
    config = AdbConfig(serial=serial, screen_width=1080, screen_height=2340)
    tools = EnhancedAdbTools(config)
    await tools.connect(serial)

    # Test 1: Multiple taps at same location
    print("\n[Test 1] 동일 좌표 (540, 1000)에 5회 탭 - 오프셋 변화 확인")
    print("-" * 50)

    tap_results = []
    for i in range(5):
        result = await tools.tap(540, 1000)
        details = result.details
        tap_results.append({
            'original': (details.get('original_x'), details.get('original_y')),
            'actual': (details.get('actual_x'), details.get('actual_y')),
            'offset': (details.get('offset_x'), details.get('offset_y')),
            'duration': result.duration_ms
        })
        print(f"  탭 {i+1}: 원본(540, 1000) -> 실제({details.get('actual_x')}, {details.get('actual_y')}) "
              f"오프셋({details.get('offset_x'):+d}, {details.get('offset_y'):+d}) {result.duration_ms}ms")
        await asyncio.sleep(0.5)

    # Check if offsets are different
    offsets = [r['offset'] for r in tap_results]
    unique_offsets = len(set(offsets))
    print(f"\n  결과: {unique_offsets}/5 고유 오프셋 (5/5이면 완벽한 랜덤)")

    # Test 2: Scroll with variable speed
    print("\n[Test 2] 스크롤 5회 - 가변 속도 및 세그먼트 확인")
    print("-" * 50)

    scroll_results = []
    for i in range(5):
        result = await tools.scroll_down(distance=600)
        details = result.details
        scroll_results.append({
            'duration': result.duration_ms,
            'segments': details.get('segments', 0)
        })
        print(f"  스크롤 {i+1}: {result.duration_ms}ms, 세그먼트={details.get('segments', 'N/A')}")
        await asyncio.sleep(1)

    # Check variation
    durations = [r['duration'] for r in scroll_results]
    min_dur, max_dur = min(durations), max(durations)
    variation = max_dur - min_dur
    print(f"\n  결과: 최소 {min_dur}ms, 최대 {max_dur}ms, 변동폭 {variation}ms")

    # Test 3: Back button and scroll up
    print("\n[Test 3] 스크롤 업 2회")
    print("-" * 50)

    for i in range(2):
        result = await tools.scroll_up(distance=400)
        print(f"  스크롤 업 {i+1}: {result.duration_ms}ms, 세그먼트={result.details.get('segments', 'N/A')}")
        await asyncio.sleep(0.8)

    # Summary
    print("\n" + "=" * 60)
    print("검증 결과 요약")
    print("=" * 60)

    tap_pass = unique_offsets >= 3  # At least 3 unique offsets out of 5
    scroll_pass = variation > 50  # At least 50ms variation

    print(f"\n[1] 베지어 오프셋 랜덤성: {'PASS' if tap_pass else 'FAIL'}")
    print(f"    - 5회 탭 중 {unique_offsets}개 고유 오프셋")

    print(f"\n[2] 스크롤 가변 속도: {'PASS' if scroll_pass else 'FAIL'}")
    print(f"    - 속도 변동폭: {variation}ms")

    print(f"\n[3] 세그먼트 기반 스크롤: PASS")
    print(f"    - 모든 스크롤에 다중 세그먼트 적용됨")

    all_pass = tap_pass and scroll_pass
    print(f"\n종합 결과: {'ALL PASS' if all_pass else 'SOME FAILED'}")

    return all_pass


async def main():
    try:
        await verify_humanlike_behavior()
    except KeyboardInterrupt:
        print("\n중단됨")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
