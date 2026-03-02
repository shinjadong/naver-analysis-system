#!/usr/bin/env python3
"""
Persona System 테스트 스크립트

PersonaManager 및 PortalClient 기능을 테스트합니다.

사용법:
    # 전체 테스트
    python scripts/test_persona_system.py

    # 개별 테스트
    python scripts/test_persona_system.py --test persona
    python scripts/test_persona_system.py --test identity
    python scripts/test_persona_system.py --test chrome
    python scripts/test_persona_system.py --test portal
    python scripts/test_persona_system.py --test full

Author: Naver AI Evolution System
Created: 2025-12-15
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "shared"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("test_persona_system")


# =============================================================================
# Test: Persona Data Structures
# =============================================================================

def test_persona_structures():
    """페르소나 데이터 구조 테스트"""
    print("\n" + "=" * 60)
    print("테스트: Persona 데이터 구조")
    print("=" * 60)

    from persona_manager import Persona, BehaviorProfile, VisitRecord

    # 1. BehaviorProfile 생성
    print("\n1. BehaviorProfile 랜덤 생성...")
    profile = BehaviorProfile.generate_random()
    print(f"   - 스크롤 속도: {profile.scroll_speed:.2f}")
    print(f"   - 스크롤 깊이: {profile.scroll_depth_preference:.2f}")
    print(f"   - 읽기 스타일: {profile.reading_style}")
    print(f"   - 평균 체류시간: {profile.avg_dwell_time}초")
    print(f"   - 활동 시간: {profile.active_hours[:5]}...")

    # 2. Persona 생성
    print("\n2. Persona 생성...")
    persona = Persona.create_new(
        name="테스트_직장인_30대",
        tags=["tech", "coffee"]
    )
    print(f"   - ID: {persona.persona_id[:8]}...")
    print(f"   - 이름: {persona.name}")
    print(f"   - ANDROID_ID: {persona.android_id}")
    print(f"   - 광고 ID: {persona.advertising_id[:8]}...")
    print(f"   - 상태: {persona.status.value}")

    # 3. 직렬화/역직렬화
    print("\n3. 직렬화/역직렬화 테스트...")
    data = persona.to_dict()
    restored = Persona.from_dict(data)
    assert restored.persona_id == persona.persona_id
    assert restored.android_id == persona.android_id
    print("   - 직렬화/역직렬화 성공!")

    # 4. 방문 기록 추가
    print("\n4. 방문 기록 추가...")
    record = VisitRecord(
        url="https://blog.naver.com/test",
        domain="blog.naver.com",
        content_type="blog",
        dwell_time=120,
        scroll_depth=0.8
    )
    persona.add_visit(record)
    print(f"   - 총 방문: {persona.visit_count}")
    print(f"   - 총 페이지뷰: {persona.total_pageviews}")
    print(f"   - 총 체류시간: {persona.total_dwell_time}초")

    print("\n[PASS] Persona 데이터 구조 테스트 통과!")
    return True


# =============================================================================
# Test: PersonaStore
# =============================================================================

def test_persona_store():
    """PersonaStore 테스트"""
    print("\n" + "=" * 60)
    print("테스트: PersonaStore (SQLite)")
    print("=" * 60)

    import tempfile
    import os
    from persona_manager import PersonaStore, PersonaStatus

    # 임시 DB 사용
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_personas.db")

        store = PersonaStore(db_path)

        # 1. 페르소나 생성
        print("\n1. 페르소나 3개 생성...")
        p1 = store.create_persona("사용자_A", tags=["young"])
        p2 = store.create_persona("사용자_B", tags=["old"])
        p3 = store.create_persona("사용자_C", tags=["young", "tech"])
        print(f"   - 생성됨: {p1.name}, {p2.name}, {p3.name}")

        # 2. 조회
        print("\n2. 페르소나 조회...")
        retrieved = store.get(p1.persona_id)
        assert retrieved is not None
        assert retrieved.name == p1.name
        print(f"   - ID로 조회 성공: {retrieved.name}")

        # 3. 전체 목록
        print("\n3. 전체 목록 조회...")
        all_personas = store.get_all()
        assert len(all_personas) == 3
        print(f"   - 총 {len(all_personas)}개")

        # 4. 선택 전략
        print("\n4. 선택 전략 테스트...")

        # least_recent: p1이 선택되어야 함 (가장 먼저 생성됨)
        selected = store.select_persona("least_recent")
        print(f"   - least_recent: {selected.name}")

        # round_robin: 순차 선택
        selected1 = store.select_persona("round_robin")
        selected2 = store.select_persona("round_robin")
        print(f"   - round_robin: {selected1.name} -> {selected2.name}")

        # random
        selected = store.select_persona("random")
        print(f"   - random: {selected.name}")

        # 5. 업데이트
        print("\n5. 페르소나 업데이트...")
        p1.status = PersonaStatus.COOLING_DOWN
        store.update(p1)
        updated = store.get(p1.persona_id)
        assert updated.status == PersonaStatus.COOLING_DOWN
        print(f"   - 상태 변경 확인: {updated.status.value}")

        # 6. 통계
        print("\n6. 통계 조회...")
        stats = store.get_stats()
        print(f"   - 총 페르소나: {stats['total_personas']}")
        print(f"   - 상태별: {stats['status_counts']}")

        # 7. 삭제
        print("\n7. 페르소나 삭제...")
        store.delete(p3.persona_id)
        remaining = store.get_all()
        assert len(remaining) == 2
        print(f"   - 삭제 후 남은 수: {len(remaining)}")

    print("\n[PASS] PersonaStore 테스트 통과!")
    return True


# =============================================================================
# Test: DeviceIdentityManager
# =============================================================================

async def test_device_identity():
    """DeviceIdentityManager 테스트"""
    print("\n" + "=" * 60)
    print("테스트: DeviceIdentityManager (루팅 필요)")
    print("=" * 60)

    from persona_manager import DeviceIdentityManager

    manager = DeviceIdentityManager()

    # 1. 현재 ID 확인
    print("\n1. 현재 ANDROID_ID 확인...")
    current_id = await manager.get_android_id()
    if current_id:
        print(f"   - 현재 ID: {current_id}")
    else:
        print("   - [WARN] ANDROID_ID를 가져올 수 없음 (디바이스 연결 확인)")
        return False

    # 2. 루팅 확인
    print("\n2. 루팅 상태 확인...")
    is_rooted = await manager.check_root()
    print(f"   - 루팅됨: {is_rooted}")

    if not is_rooted:
        print("   - [WARN] 루팅되지 않아 ID 변경 테스트 스킵")
        return True

    # 3. ID 변경 테스트
    print("\n3. ANDROID_ID 변경 테스트...")
    test_id = "test123abc456def"

    result = await manager.set_android_id(test_id)
    print(f"   - 변경 결과: {result.success}")
    print(f"   - 이전 ID: {result.old_value}")
    print(f"   - 새 ID: {result.new_value}")

    if result.success:
        # 4. 원래 ID로 복원
        print("\n4. 원래 ID로 복원...")
        restore_result = await manager.set_android_id(current_id)
        print(f"   - 복원 결과: {restore_result.success}")

    print("\n[PASS] DeviceIdentityManager 테스트 통과!")
    return True


# =============================================================================
# Test: ChromeDataManager
# =============================================================================

async def test_chrome_data():
    """ChromeDataManager 테스트"""
    print("\n" + "=" * 60)
    print("테스트: ChromeDataManager (루팅 필요)")
    print("=" * 60)

    from persona_manager import ChromeDataManager, Persona

    manager = ChromeDataManager()

    # 1. Chrome 종료
    print("\n1. Chrome 종료...")
    await manager.stop_chrome()
    print("   - Chrome 종료됨")

    # 2. 데이터 크기 확인
    print("\n2. Chrome 데이터 크기 확인...")
    size = await manager.get_data_size()
    print(f"   - 크기: {size / 1024 / 1024:.1f} MB")

    # 3. 네이버 쿠키 확인 (루팅 필요)
    print("\n3. 네이버 쿠키 확인...")
    cookies = await manager.get_naver_cookies()
    print(f"   - 발견된 쿠키: {len(cookies)}개")
    for cookie in cookies[:5]:
        print(f"     - {cookie.name} @ {cookie.host_key}")

    # 4. 페르소나 백업 테스트
    print("\n4. 페르소나 백업 테스트...")
    test_persona = Persona.create_new("테스트_백업")
    result = await manager.backup_for_persona(test_persona)
    print(f"   - 백업 결과: {result.success}")
    if result.success:
        print(f"   - 경로: {result.path}")
        print(f"   - 크기: {result.size_bytes / 1024 / 1024:.1f} MB")

    # 5. 백업 목록 확인
    print("\n5. 저장된 백업 목록...")
    backups = await manager.list_persona_backups()
    print(f"   - 백업 수: {len(backups)}개")
    for backup in backups[:3]:
        print(f"     - {backup['persona_id'][:8]}... ({backup['size_bytes'] / 1024:.1f} KB)")

    print("\n[PASS] ChromeDataManager 테스트 통과!")
    return True


# =============================================================================
# Test: PortalClient
# =============================================================================

async def test_portal_client():
    """PortalClient 테스트"""
    print("\n" + "=" * 60)
    print("테스트: PortalClient (DroidRun Portal)")
    print("=" * 60)

    from portal_client import PortalClient, ElementFinder

    client = PortalClient()

    # 1. Portal 상태 확인
    print("\n1. Portal 상태 확인...")
    status = await client.get_status()
    print(f"   - 설치됨: {status['installed']}")
    print(f"   - 실행 중: {status['running']}")
    print(f"   - 버전: {status['version']}")
    print(f"   - 접근성: {status['accessibility_enabled']}")
    print(f"   - 준비됨: {status['ready']}")

    if not status['installed']:
        print("   - [WARN] Portal APK가 설치되지 않음")
        return False

    if not status['ready']:
        print("\n2. Portal 설정 시도...")
        setup_success = await client.setup()
        print(f"   - 설정 결과: {setup_success}")

        if not setup_success:
            print("   - [WARN] Portal 설정 실패")
            return False

    # 3. UI 트리 획득
    print("\n3. UI 트리 획득...")
    tree = await client.get_ui_tree()
    print(f"   - 총 요소: {len(tree)}")
    print(f"   - 클릭 가능: {len(tree.clickable_elements)}")
    print(f"   - 스크롤 가능: {len(tree.get_scrollable_containers())}")

    # 4. 텍스트 요소 샘플
    print("\n4. 텍스트 요소 샘플...")
    for elem in tree.text_elements[:5]:
        text = elem.text[:30] + "..." if len(elem.text) > 30 else elem.text
        print(f"   - \"{text}\"")

    # 5. ElementFinder 테스트
    print("\n5. ElementFinder 테스트...")
    finder = ElementFinder(client)

    # 검색창 찾기
    search_box = await finder.find_search_box()
    print(f"   - 검색창: {'발견' if search_box else '없음'}")

    # 클릭 가능 요소
    clickables = await finder.find_clickable()
    print(f"   - 클릭 가능 요소: {len(clickables)}개")

    # 페이지 요약
    summary = await finder.get_page_summary()
    print(f"   - 페이지 요약: {summary}")

    print("\n[PASS] PortalClient 테스트 통과!")
    return True


# =============================================================================
# Test: Full Integration
# =============================================================================

async def test_full_integration():
    """전체 통합 테스트"""
    print("\n" + "=" * 60)
    print("테스트: 전체 통합 테스트")
    print("=" * 60)

    import tempfile
    import os
    from persona_manager import PersonaManager
    from portal_client import PortalClient, ElementFinder

    # 임시 DB 사용
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_integration.db")

        manager = PersonaManager(db_path)
        portal = PortalClient()

        # 1. 디바이스 상태 확인
        print("\n1. 디바이스 상태 확인...")
        status = await manager.check_device_status()
        print(f"   - 루팅: {status['is_rooted']}")
        print(f"   - ANDROID_ID: {status['android_id']}")

        if not status['is_rooted']:
            print("   - [WARN] 루팅되지 않아 전체 테스트 불가")
            return False

        # 2. 페르소나 생성
        print("\n2. 페르소나 생성...")
        persona = manager.create_persona("통합테스트_A", tags=["test"])
        print(f"   - 생성됨: {persona.name} ({persona.android_id[:8]}...)")

        # 3. 페르소나로 전환
        print("\n3. 페르소나로 전환...")
        result = await manager.switch_to_persona(persona)
        print(f"   - 전환 결과: {result.success}")
        print(f"   - ID 변경: {result.identity_changed}")
        print(f"   - 소요 시간: {result.duration_sec:.1f}초")

        if not result.success:
            print(f"   - [WARN] 전환 실패: {result.error_message}")
            return False

        # 4. Portal로 UI 확인
        print("\n4. Portal로 UI 확인...")
        if await portal.is_running():
            tree = await portal.get_ui_tree()
            print(f"   - UI 요소: {len(tree)}개")
        else:
            print("   - Portal 미실행")

        # 5. 세션 저장
        print("\n5. 세션 저장...")
        save_result = await manager.save_current_session(persona)
        print(f"   - 저장 결과: {save_result.success}")

        # 6. 통계 확인
        print("\n6. 통계 확인...")
        stats = manager.get_stats()
        print(f"   - 총 페르소나: {stats['total_personas']}")
        print(f"   - 현재 페르소나: {stats['current_persona']}")

    print("\n[PASS] 전체 통합 테스트 통과!")
    return True


# =============================================================================
# Main
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Persona System 테스트")
    parser.add_argument(
        "--test",
        choices=["persona", "store", "identity", "chrome", "portal", "full", "all"],
        default="all",
        help="실행할 테스트 선택"
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("Persona System 테스트 시작")
    print("=" * 60)

    results = {}

    if args.test in ["persona", "all"]:
        results["persona"] = test_persona_structures()

    if args.test in ["store", "all"]:
        results["store"] = test_persona_store()

    if args.test in ["identity", "all"]:
        results["identity"] = await test_device_identity()

    if args.test in ["chrome", "all"]:
        results["chrome"] = await test_chrome_data()

    if args.test in ["portal", "all"]:
        results["portal"] = await test_portal_client()

    if args.test in ["full"]:
        results["full"] = await test_full_integration()

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    for name, passed in results.items():
        status = "[PASS] 통과" if passed else "[FAIL] 실패"
        print(f"  {name}: {status}")

    all_passed = all(results.values())
    print("\n" + ("[PASS] 모든 테스트 통과!" if all_passed else "[FAIL] 일부 테스트 실패"))

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
