#!/usr/bin/env python3
"""
DeviceSessionManager & EngagementSimulator 테스트 스크립트

테스트 항목:
1. 기본 모듈 로드 테스트
2. ADB 연결 테스트
3. IP 확인 테스트
4. 세션 리셋 테스트 (비행기 모드 + 쿠키 삭제)
5. 인게이지먼트 시뮬레이션 테스트

사용법:
    python test_session_manager.py           # 전체 테스트
    python test_session_manager.py module    # 모듈 로드만
    python test_session_manager.py ip        # IP 확인만
    python test_session_manager.py reset     # 세션 리셋
    python test_session_manager.py engage    # 인게이지먼트 테스트
"""

import asyncio
import sys
import time
from pathlib import Path

# 프로젝트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def test_module_import():
    """모듈 임포트 테스트"""
    print("\n" + "=" * 60)
    print("[TEST] Module Import")
    print("=" * 60)

    try:
        from shared.session_manager import (
            DeviceSessionManager,
            SessionConfig,
            SessionState,
            SessionResetResult,
            EngagementSimulator,
            EngagementConfig,
            EngagementResult,
        )
        print("[OK] DeviceSessionManager imported")
        print("[OK] SessionConfig imported")
        print("[OK] SessionState imported")
        print("[OK] EngagementSimulator imported")
        print("[OK] EngagementConfig imported")

        # 인스턴스 생성 테스트
        config = SessionConfig()
        print(f"[OK] SessionConfig created: cooldown={config.cooldown_minutes}min")

        manager = DeviceSessionManager(config)
        print(f"[OK] DeviceSessionManager created")

        eng_config = EngagementConfig()
        print(f"[OK] EngagementConfig created: dwell={eng_config.dwell_time_min}-{eng_config.dwell_time_max}s")

        simulator = EngagementSimulator(eng_config)
        print(f"[OK] EngagementSimulator created")

        print("\n[RESULT] All modules loaded successfully!")
        return True

    except Exception as e:
        print(f"[ERROR] Module import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_device_connection():
    """디바이스 연결 테스트"""
    print("\n" + "=" * 60)
    print("[TEST] Device Connection")
    print("=" * 60)

    from shared.session_manager import DeviceSessionManager, SessionConfig

    manager = DeviceSessionManager(SessionConfig())

    # 연결 확인
    connected = await manager.check_device_connected()
    if connected:
        print("[OK] Device connected")
    else:
        print("[ERROR] No device connected")
        return False

    # 네트워크 타입 확인
    network = await manager.get_network_type()
    print(f"[OK] Network type: {network}")

    print("\n[RESULT] Device connection test passed!")
    return True


async def test_ip_check():
    """IP 확인 테스트"""
    print("\n" + "=" * 60)
    print("[TEST] IP Check")
    print("=" * 60)

    from shared.session_manager import DeviceSessionManager, SessionConfig

    manager = DeviceSessionManager(SessionConfig())

    # 현재 IP 확인
    ip = await manager.get_current_ip()
    if ip:
        print(f"[OK] Current IP: {ip}")
    else:
        print("[WARN] Could not get IP (might be on WiFi or no internet)")

    # 네트워크 타입
    network = await manager.get_network_type()
    print(f"[OK] Network: {network}")

    print("\n[RESULT] IP check test completed!")
    return True


async def test_session_reset():
    """세션 리셋 테스트 (비행기 모드 + 쿠키 삭제)"""
    print("\n" + "=" * 60)
    print("[TEST] Session Reset (IP Rotation + Cookie Clear)")
    print("=" * 60)
    print("[WARN] This will:")
    print("  - Toggle airplane mode (change IP)")
    print("  - Clear Chrome browser data")
    print()

    from shared.session_manager import DeviceSessionManager, SessionConfig

    config = SessionConfig(
        airplane_mode_wait_sec=5,
        ip_change_verify=True
    )
    manager = DeviceSessionManager(config)

    # 연결 확인
    if not await manager.check_device_connected():
        print("[ERROR] No device connected")
        return False

    # 세션 리셋 실행
    print("[1/3] Creating new identity...")
    start_time = time.time()

    result = await manager.create_new_identity()

    duration = time.time() - start_time

    print(f"\n[RESULT] Session Reset:")
    print(f"  - Success: {result.success}")
    print(f"  - Old IP: {result.old_ip}")
    print(f"  - New IP: {result.new_ip}")
    print(f"  - IP Changed: {result.ip_changed}")
    print(f"  - Cookies Cleared: {result.cookies_cleared}")
    print(f"  - Duration: {duration:.1f}s")

    if result.error_message:
        print(f"  - Error: {result.error_message}")

    # 세션 통계
    stats = manager.get_session_stats()
    print(f"\n[SESSION STATS]")
    print(f"  - Session ID: {stats['current_session']}")
    print(f"  - State: {stats['current_state']}")

    return result.success


async def test_engagement():
    """인게이지먼트 시뮬레이션 테스트"""
    print("\n" + "=" * 60)
    print("[TEST] Engagement Simulation")
    print("=" * 60)
    print("[INFO] This will:")
    print("  - Search for a keyword on Naver")
    print("  - Click first result")
    print("  - Simulate natural reading (scrolling)")
    print("  - Go back")
    print()

    from shared.session_manager import EngagementSimulator, EngagementConfig

    config = EngagementConfig(
        dwell_time_min=30,   # 테스트용 짧은 시간
        dwell_time_max=45,
        scroll_count_min=3,
        scroll_count_max=5
    )
    simulator = EngagementSimulator(config)
    simulator.start_session("test_session_001")

    # 검색 + 방문 시뮬레이션
    keyword = "맛집 추천"
    print(f"[1/2] Simulating search: '{keyword}'")

    result = await simulator.simulate_search_and_visit(keyword, result_index=0)

    print(f"\n[RESULT] Engagement:")
    print(f"  - Success: {result.success}")
    print(f"  - URL: {result.url}")
    print(f"  - Dwell Time: {result.dwell_time_sec:.1f}s")
    print(f"  - Scroll Count: {result.scroll_count}")

    if result.error_message:
        print(f"  - Error: {result.error_message}")

    # 세션 통계
    stats = simulator.end_session()
    if stats:
        print(f"\n[SESSION STATS]")
        print(f"  - Total Engagements: {stats.total_engagements}")
        print(f"  - Total Dwell Time: {stats.total_dwell_time:.1f}s")
        print(f"  - Total Scrolls: {stats.total_scrolls}")

    return result.success


async def test_full_session():
    """전체 세션 테스트 (리셋 + 인게이지먼트)"""
    print("\n" + "=" * 60)
    print("[TEST] Full Session (Reset + Engagement)")
    print("=" * 60)
    print("[WARN] This is a complete session test:")
    print("  1. IP rotation (airplane mode)")
    print("  2. Cookie clear")
    print("  3. Search engagement simulation")
    print()

    from shared.session_manager.engagement_simulator import run_engagement_session

    keywords = ["서울 맛집", "제주도 여행"]

    print(f"[INFO] Keywords: {keywords}")
    print(f"[INFO] Starting full session...\n")

    stats = await run_engagement_session(
        keywords=keywords,
        pageviews_per_session=2
    )

    print(f"\n[FINAL RESULT]")
    print(f"  - Session ID: {stats.session_id}")
    print(f"  - Total Engagements: {stats.total_engagements}")
    print(f"  - Total Dwell Time: {stats.total_dwell_time:.1f}s")
    print(f"  - Total Scrolls: {stats.total_scrolls}")

    return stats.total_engagements > 0


def run_async_test(coro):
    """비동기 테스트 실행"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def main():
    """메인 함수"""
    print("=" * 60)
    print("[TEST SUITE] DeviceSessionManager & EngagementSimulator")
    print("=" * 60)

    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()

        if test_name == "module":
            test_module_import()
        elif test_name == "device":
            run_async_test(test_device_connection())
        elif test_name == "ip":
            run_async_test(test_ip_check())
        elif test_name == "reset":
            run_async_test(test_session_reset())
        elif test_name == "engage":
            run_async_test(test_engagement())
        elif test_name == "full":
            run_async_test(test_full_session())
        else:
            print(f"Unknown test: {test_name}")
            print("Available: module, device, ip, reset, engage, full")
    else:
        # 전체 테스트 (안전한 것만)
        results = []

        # 1. 모듈 임포트
        results.append(("Module Import", test_module_import()))

        # 2. 디바이스 연결
        results.append(("Device Connection", run_async_test(test_device_connection())))

        # 3. IP 확인
        results.append(("IP Check", run_async_test(test_ip_check())))

        # 결과 요약
        print("\n" + "=" * 60)
        print("[TEST SUMMARY]")
        print("=" * 60)
        for name, passed in results:
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status} {name}")

        all_passed = all(r[1] for r in results)
        print()
        if all_passed:
            print("[OK] All basic tests passed!")
            print()
            print("To run more tests:")
            print("  python test_session_manager.py reset   # IP rotation + cookie clear")
            print("  python test_session_manager.py engage  # Engagement simulation")
            print("  python test_session_manager.py full    # Complete session test")
        else:
            print("[WARN] Some tests failed")


if __name__ == "__main__":
    main()
