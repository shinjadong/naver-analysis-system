#!/usr/bin/env python3
"""
DeepSeek 스토리라인 실행 v3 - SmartExecutor 통합

Portal UI 파싱 + 베지어 모션이 완전히 통합된 버전입니다.

Usage:
    DEEPSEEK_API_KEY=your_key python scripts/run_deepseek_storyline_v3.py --device <serial>
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.shared.storyline_generator import (
    StorylineGenerator,
    Action
)
from src.shared.smart_executor import SmartExecutor


async def execute_storyline_v3(
    device_serial: str,
    keyword: str = "서울 맛집 추천",
    persona_type: str = "curious_reader"
):
    """스토리라인 생성 및 실행 (SmartExecutor 통합)"""

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("[ERROR] DEEPSEEK_API_KEY 환경변수가 설정되지 않았습니다.")
        return False

    print("\n" + "=" * 60)
    print("DeepSeek 스토리라인 실행 v3 (SmartExecutor 통합)")
    print("=" * 60)

    # 1. SmartExecutor 초기화
    print("\n[1] SmartExecutor 초기화")
    executor = SmartExecutor(device_serial=device_serial)
    await executor.setup()

    screen_size = executor.screen_size
    print(f"  화면 크기: {screen_size}")

    status = await executor.get_status()
    print(f"  Portal 준비: {status['portal'].get('ready', False)}")
    print(f"  베지어 모션: {status['use_bezier']}")

    # 2. 네이버 검색 열기 + 블로그 탭 클릭
    print("\n[2] 네이버 검색 열기")
    search_url = f"https://m.search.naver.com/search.naver?query={keyword}"
    result = await executor.open_url(search_url)
    print(f"  결과: {result.message}")
    print("  로딩 대기 (4초)...")
    await asyncio.sleep(4)

    # 블로그 탭 클릭
    print("\n[2.1] 블로그 탭 클릭")
    result = await executor.tap_by_text("블로그", exact=True)
    print(f"  결과: {result.message}")
    await asyncio.sleep(3)

    # 3. UI 컨텍스트 확인
    print("\n[3] UI 컨텍스트 확인")
    context = await executor.get_ui_context()
    if "error" not in context:
        print(f"  전체 요소: {context['total_elements']}개")
        print(f"  클릭 가능: {context['clickable_count']}개")
        print("  상위 요소:")
        for elem in context['elements'][:5]:
            text = elem['text'][:40] if elem['text'] else "(no text)"
            print(f"    - '{text}' at {elem['center']}")
    else:
        print(f"  [ERROR] {context['error']}")

    # 4. DeepSeek 스토리라인 생성
    print("\n[4] DeepSeek 스토리라인 생성")
    generator = StorylineGenerator(api_key)

    storyline = await generator.generate_storyline(
        persona_name="Test_Persona",
        persona_type=persona_type,
        interests=["맛집", "여행", "카페"],
        keyword=keyword,
        current_page="naver_blog_search",
        session_goal="블로그 2개 방문 및 읽기",
        screen_size=screen_size,
        current_app="com.android.chrome",
        battery_level=80
    )

    print(f"  스토리라인 ID: {storyline.storyline_id}")
    print(f"  생성된 액션: {len(storyline.actions)}개")

    # 5. 액션 실행
    print("\n[5] 액션 실행 (SmartExecutor)")
    print("-" * 60)

    total_time = 0

    for i, action in enumerate(storyline.actions, 1):
        print(f"\n  [{i}/{len(storyline.actions)}] {action.type.upper()}")
        target_preview = action.target[:50] + "..." if len(action.target) > 50 else action.target
        print(f"      대상: {target_preview}")

        if action.type == "wait":
            print(f"      대기: {action.duration_ms}ms")
            await asyncio.sleep(action.duration_ms / 1000)
            print("      [완료]")

        elif action.type == "scroll":
            direction = action.parameters.get("direction", "down")
            distance = action.parameters.get("distance", 400)

            # SmartExecutor의 스크롤 사용
            result = await executor.scroll(
                direction=direction,
                distance=distance,
                speed="medium"
            )
            print(f"      {result.message}")
            await asyncio.sleep(0.5)

        elif action.type == "tap":
            # 핵심: SmartExecutor의 텍스트 기반 탭 사용
            target_lower = action.target.lower()

            # 블로그 포스트 탭인지 확인
            if any(kw in target_lower for kw in ['블로그', 'blog', '결과', 'result', '포스트', 'post', '첫 번째', '두 번째']):
                # 블로그 포스트 전용 탭
                blog_index = 0
                if '두 번째' in action.target or '두번째' in action.target or 'second' in target_lower:
                    blog_index = 1
                elif '세 번째' in action.target or '세번째' in action.target:
                    blog_index = 2

                result = await executor.tap_blog_post(index=blog_index)
                if result.success:
                    print(f"      블로그 포스트 탭 성공: {result.message}")
                    if result.element:
                        print(f"      제목: {result.element.text[:40]}...")
                else:
                    print(f"      [WARN] {result.message}")

            else:
                # 일반 텍스트 기반 탭
                result = await executor.tap_by_text(
                    text=action.target,
                    exact=False,
                    clickable_only=False
                )

                if result.success:
                    print(f"      텍스트 매칭 성공: {result.message}")
                    if result.coordinates:
                        print(f"      좌표: {result.coordinates}")
                else:
                    # 폴백: 키워드 기반 탭
                    keywords = [keyword.split()[0]] if keyword else []
                    keywords.extend(["맛집", "추천", "베스트", "리뷰"])
                    print(f"      텍스트 매칭 실패, 키워드 탭 시도...")
                    result = await executor.tap_first_match(
                        keywords=keywords,
                        region=(0.2, 0.75, 0.0, 1.0)
                    )
                    if result.success:
                        print(f"      키워드 매칭 성공: {result.message}")
                    else:
                        print(f"      [WARN] {result.message}")

            await asyncio.sleep(2)

        elif action.type == "read":
            print(f"      읽기: {action.duration_ms}ms")
            read_time = action.duration_ms / 1000
            scroll_count = max(1, int(read_time / 3))

            for j in range(scroll_count):
                await asyncio.sleep(read_time / scroll_count * 0.7)
                # 작은 스크롤
                await executor.scroll(
                    direction="down",
                    distance=150,
                    speed="slow"
                )
                await asyncio.sleep(0.3)

            print("      [완료]")

        elif action.type == "back":
            print("      뒤로가기")
            result = await executor.back()
            print(f"      {result.message}")
            await asyncio.sleep(1)

        total_time += action.duration_ms
        generator.record_action(action)

    # 6. 결과 요약
    print("\n" + "=" * 60)
    print("실행 완료")
    print("=" * 60)
    print(f"  총 액션: {len(storyline.actions)}개")
    print(f"  총 시간: {total_time / 1000:.1f}초")
    print(f"  페르소나: {persona_type}")

    # 최종 UI 상태
    print("\n[최종 UI 상태]")
    final_context = await executor.get_ui_context()
    if "error" not in final_context:
        print(f"  클릭 가능 요소: {final_context['clickable_count']}개")
        print("  상위 요소:")
        for elem in final_context['elements'][:3]:
            text = elem['text'][:30] if elem['text'] else "(no text)"
            print(f"    - '{text}'")

    return True


async def main():
    parser = argparse.ArgumentParser(description="DeepSeek Storyline Executor v3 (SmartExecutor)")
    parser.add_argument("--device", "-d", help="Android device serial")
    parser.add_argument("--keyword", "-k", default="서울 맛집", help="Search keyword")
    parser.add_argument(
        "--persona", "-p",
        default="curious_reader",
        choices=["curious_reader", "speed_scanner", "deep_researcher"],
        help="Persona type"
    )

    args = parser.parse_args()

    await execute_storyline_v3(
        device_serial=args.device,
        keyword=args.keyword,
        persona_type=args.persona
    )


if __name__ == "__main__":
    asyncio.run(main())
