#!/usr/bin/env python3
"""
SmartExecutor 테스트

Portal UI 파싱 + 베지어 모션 통합 테스트

Usage:
    python scripts/test_smart_executor.py --device <serial>
"""

import asyncio
import argparse
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.shared.smart_executor import SmartExecutor


async def test_smart_executor(device_serial: str):
    """SmartExecutor 테스트"""

    print("=" * 60)
    print("  SmartExecutor 테스트")
    print("=" * 60)

    # 1. 초기화
    print("\n[1] SmartExecutor 초기화")
    executor = SmartExecutor(device_serial=device_serial)
    await executor.setup()
    print(f"  화면 크기: {executor.screen_size}")

    # 2. 상태 확인
    print("\n[2] 상태 확인")
    status = await executor.get_status()
    print(f"  설정 완료: {status['is_setup']}")
    print(f"  Portal 상태: {status['portal']}")
    print(f"  베지어 사용: {status['use_bezier']}")

    # 3. URL 열기
    print("\n[3] 네이버 블로그 검색 열기")
    result = await executor.open_url(
        "https://m.search.naver.com/search.naver?where=m_blog&query=서울 맛집"
    )
    print(f"  결과: {result.message}")
    await asyncio.sleep(5)  # 로딩 대기

    # 4. UI 컨텍스트 획득
    print("\n[4] UI 컨텍스트 획득")
    context = await executor.get_ui_context()
    if "error" not in context:
        print(f"  화면 크기: {context['screen_size']}")
        print(f"  전체 요소: {context['total_elements']}개")
        print(f"  클릭 가능: {context['clickable_count']}개")
        print("\n  상위 클릭 가능 요소:")
        for elem in context['elements'][:8]:
            text = elem['text'][:40] if elem['text'] else "(no text)"
            print(f"    - '{text}' at {elem['center']}")
    else:
        print(f"  [ERROR] {context['error']}")

    # 5. 화면 요약 (DeepSeek 프롬프트용)
    print("\n[5] 화면 요약 (DeepSeek 프롬프트용)")
    summary = await executor.get_screen_summary()
    print(summary)

    # 6. 스크롤 테스트
    print("\n[6] 스크롤 테스트")
    result = await executor.scroll(direction="down", distance=400, speed="medium")
    print(f"  결과: {result.message}")
    await asyncio.sleep(1)

    # 7. 키워드 기반 탭 테스트
    print("\n[7] 키워드 기반 첫 번째 요소 탭")
    result = await executor.tap_first_match(
        keywords=["맛집", "추천", "베스트", "리뷰", "서울"],
        region=(0.2, 0.75, 0.0, 1.0)  # 화면 상단 20% ~ 75%
    )
    if result.success:
        print(f"  성공: {result.message}")
        print(f"  좌표: {result.coordinates}")
        if result.element:
            print(f"  요소 텍스트: {result.element.text[:50]}")
    else:
        print(f"  실패: {result.message}")

    await asyncio.sleep(3)  # 페이지 로딩 대기

    # 8. 탭 후 UI 확인
    print("\n[8] 탭 후 UI 상태")
    context = await executor.get_ui_context()
    if "error" not in context:
        print(f"  클릭 가능 요소: {context['clickable_count']}개")
        print("  상위 요소:")
        for elem in context['elements'][:5]:
            text = elem['text'][:30] if elem['text'] else "(no text)"
            print(f"    - '{text}'")

    # 9. 뒤로가기
    print("\n[9] 뒤로가기")
    result = await executor.back()
    print(f"  결과: {result.message}")

    print("\n" + "=" * 60)
    print("  테스트 완료")
    print("=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="SmartExecutor Test")
    parser.add_argument("--device", "-d", required=True, help="Device serial")
    args = parser.parse_args()

    await test_smart_executor(args.device)


if __name__ == "__main__":
    asyncio.run(main())
