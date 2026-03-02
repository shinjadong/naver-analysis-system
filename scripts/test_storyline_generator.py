#!/usr/bin/env python3
"""
스토리라인 생성기 테스트

Usage:
    # MotionPlanner 테스트 (API 키 없이)
    python scripts/test_storyline_generator.py --test-planner

    # DeepSeek API 테스트 (API 키 필요)
    DEEPSEEK_API_KEY=your_key python scripts/test_storyline_generator.py --test-api

    # 전체 테스트
    DEEPSEEK_API_KEY=your_key python scripts/test_storyline_generator.py --test-all
"""

import asyncio
import argparse
import json
import os
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.shared.storyline_generator import (
    StorylineGenerator,
    MotionPlanner,
    DeepSeekClient,
    Action,
    Storyline
)


def test_motion_planner():
    """MotionPlanner 테스트 (API 키 불필요)"""
    print("\n" + "=" * 60)
    print("MotionPlanner Test")
    print("=" * 60)

    planner = MotionPlanner(screen_size=(1080, 2400))

    # 1. 탭 테스트
    print("\n[1] Tap Motion")
    tap_plan = planner.plan_tap(540, 1200)
    print(f"  Touch points: {len(tap_plan.touch_points)}")
    if tap_plan.touch_points:
        tp = tap_plan.touch_points[0]
        print(f"  Position: ({tp.x}, {tp.y})")
        print(f"  Pressure: {tp.pressure:.2f}")
        print(f"  Duration: {tp.duration_ms}ms")

    commands = planner.to_adb_commands(tap_plan)
    print(f"  ADB commands: {len(commands)}")
    for cmd in commands:
        print(f"    - {cmd['command']}")

    # 2. 스크롤 테스트
    print("\n[2] Scroll Motion")
    scroll_plan = planner.plan_scroll(direction="down", distance=500, speed="medium")
    print(f"  Bezier curves: {len(scroll_plan.bezier_curves)}")
    if scroll_plan.bezier_curves:
        curve = scroll_plan.bezier_curves[0]
        print(f"  Start: {curve.start}")
        print(f"  End: {curve.end}")
        print(f"  Duration: {curve.duration_ms}ms")

    commands = planner.to_adb_commands(scroll_plan)
    print(f"  ADB commands: {len(commands)}")
    for cmd in commands:
        print(f"    - {cmd['command']}")

    # 3. 타이핑 테스트
    print("\n[3] Typing Motion")
    type_plan = planner.plan_typing("서울 맛집", typing_speed="medium")
    print(f"  Total duration: {type_plan.total_duration_ms}ms")
    print(f"  ADB commands: {type_plan.adb_commands}")

    # 4. 뒤로가기 테스트
    print("\n[4] Back Motion")
    back_plan = planner.plan_back()
    commands = planner.to_adb_commands(back_plan)
    for cmd in commands:
        print(f"    - {cmd['command']}")

    # 5. 읽기 패턴 테스트
    print("\n[5] Natural Reading Pattern")
    reading_plans = planner.generate_natural_reading_pattern(
        content_height=2000,
        reading_time_sec=30
    )
    print(f"  Generated {len(reading_plans)} motion plans")
    for i, plan in enumerate(reading_plans[:5], 1):
        print(f"    {i}. {plan.action_type}: {plan.total_duration_ms}ms")

    # 6. 베지어 커브 포인트 테스트
    print("\n[6] Bezier Curve Points")
    if scroll_plan.bezier_curves:
        curve = scroll_plan.bezier_curves[0]
        points = curve.get_points(segments=5)
        print(f"  Curve points:")
        for i, (x, y) in enumerate(points):
            print(f"    t={i/5:.1f}: ({x}, {y})")

    print("\n[PASS] MotionPlanner test completed!")
    return True


async def test_deepseek_api():
    """DeepSeek API 테스트"""
    print("\n" + "=" * 60)
    print("DeepSeek API Test")
    print("=" * 60)

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("\n[!] DEEPSEEK_API_KEY 환경변수가 설정되지 않았습니다.")
        print("    테스트를 건너뜁니다.")
        return None

    client = DeepSeekClient(api_key)

    # 1. Health check
    print("\n[1] Health Check")
    healthy = await client.health_check()
    print(f"  API Status: {'OK' if healthy else 'FAILED'}")

    if not healthy:
        print("\n[FAIL] API 연결 실패")
        return False

    # 2. 간단한 채팅
    print("\n[2] Simple Chat")
    response = await client.chat(
        user_prompt="Say 'Hello from DeepSeek' in Korean",
        max_tokens=50
    )
    print(f"  Response: {response}")

    # 3. JSON 응답
    print("\n[3] JSON Response")
    json_response = await client.generate_json(
        prompt='Generate a simple JSON with keys: "name", "type", "count"',
        temperature=0.3
    )
    print(f"  JSON: {json.dumps(json_response, ensure_ascii=False, indent=2)}")

    print("\n[PASS] DeepSeek API test completed!")
    return True


async def test_storyline_generator():
    """StorylineGenerator 테스트"""
    print("\n" + "=" * 60)
    print("StorylineGenerator Test")
    print("=" * 60)

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("\n[!] DEEPSEEK_API_KEY 환경변수가 설정되지 않았습니다.")
        print("    기본 스토리라인 생성만 테스트합니다.")

        # 기본 스토리라인 테스트
        generator = StorylineGenerator(api_key="dummy")
        storyline = generator._create_default_storyline(
            persona_type="curious_reader",
            interests=["맛집", "여행"],
            current_page="search_results"
        )

        print("\n[Default Storyline]")
        print(f"  ID: {storyline.storyline_id}")
        print(f"  Actions: {len(storyline.actions)}")
        for i, action in enumerate(storyline.actions, 1):
            print(f"    {i}. [{action.type}] {action.target} ({action.duration_ms}ms)")
            print(f"       Reasoning: {action.reasoning}")

        return True

    generator = StorylineGenerator(api_key)

    # 1. 스토리라인 생성
    print("\n[1] Generating Storyline")
    storyline = await generator.generate_storyline(
        persona_name="Test_Persona",
        persona_type="curious_reader",
        interests=["맛집", "여행", "IT"],
        keyword="서울 맛집 추천",
        current_page="search_results",
        session_goal="맛집 블로그 2개 방문",
        screen_size=(1080, 2400),
        current_app="com.android.chrome",
        battery_level=85
    )

    print(f"\n  Storyline ID: {storyline.storyline_id}")
    print(f"  Persona Context: {storyline.persona_context}")
    print(f"  Expected Signals: {storyline.expected_signals}")
    print(f"  Actions: {len(storyline.actions)}")

    for i, action in enumerate(storyline.actions, 1):
        print(f"\n  Action {i}:")
        print(f"    Type: {action.type}")
        print(f"    Target: {action.target}")
        print(f"    Duration: {action.duration_ms}ms")
        print(f"    Reasoning: {action.reasoning}")

    # 2. ADB 명령으로 변환
    print("\n[2] Refining to ADB Commands")
    if storyline.actions:
        action = storyline.actions[0]
        refined = await generator.refine_to_adb_commands(action)
        print(f"  Original: [{action.type}] {action.target}")
        print(f"  ADB Commands: {len(refined.adb_commands)}")
        for cmd in refined.adb_commands[:3]:
            print(f"    - {cmd}")

    # 3. 히스토리 기록
    print("\n[3] Recording History")
    for action in storyline.actions:
        generator.record_action(action)
    print(f"  Recorded {len(generator.action_history)} actions")

    # 4. 결과 기반 적응 (모의)
    print("\n[4] Adaptation from Result")
    if storyline.actions:
        adapted = await generator.adapt_from_result(
            execution_result={"status": "partial", "scroll_depth": 0.3},
            expected_result={"status": "success", "scroll_depth": 0.7},
            errors=["Element not found"]
        )
        print(f"  Adapted actions: {len(adapted)}")

    print("\n[PASS] StorylineGenerator test completed!")
    return True


async def test_all():
    """전체 테스트"""
    results = {}

    # 1. MotionPlanner (API 키 불필요)
    results["motion_planner"] = test_motion_planner()

    # 2. DeepSeek API
    api_result = await test_deepseek_api()
    results["deepseek_api"] = api_result if api_result is not None else "SKIPPED"

    # 3. StorylineGenerator
    results["storyline_generator"] = await test_storyline_generator()

    # 결과 요약
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, result in results.items():
        if result == "SKIPPED":
            status = "SKIPPED (no API key)"
        elif result:
            status = "PASS"
        else:
            status = "FAIL"
        print(f"  {test_name}: {status}")


async def main():
    parser = argparse.ArgumentParser(description="Storyline Generator Test")
    parser.add_argument(
        "--test-planner",
        action="store_true",
        help="Test MotionPlanner only (no API key needed)"
    )
    parser.add_argument(
        "--test-api",
        action="store_true",
        help="Test DeepSeek API (requires DEEPSEEK_API_KEY)"
    )
    parser.add_argument(
        "--test-generator",
        action="store_true",
        help="Test StorylineGenerator"
    )
    parser.add_argument(
        "--test-all",
        action="store_true",
        help="Run all tests"
    )

    args = parser.parse_args()

    if args.test_all:
        await test_all()
    elif args.test_planner:
        test_motion_planner()
    elif args.test_api:
        await test_deepseek_api()
    elif args.test_generator:
        await test_storyline_generator()
    else:
        # 기본: MotionPlanner 테스트
        test_motion_planner()


if __name__ == "__main__":
    asyncio.run(main())
