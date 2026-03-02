#!/usr/bin/env python3
"""
재방문 시뮬레이션 검증 테스트

목표: 같은 페르소나로 재방문 시 NNB 쿠키가 유지되는지 검증
"""

import asyncio
import sys
import os

# 프로젝트 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'shared'))

from persona_manager import PersonaManager, PersonaStatus
from persona_manager.chrome_data import ChromeDataManager


async def get_nnb_cookie():
    """현재 NNB 쿠키 조회"""
    chrome = ChromeDataManager()
    cookies = await chrome.get_naver_cookies()

    nnb = None
    for cookie in cookies:
        if cookie.name == "NNB":
            nnb = cookie
            break

    return nnb, cookies


async def test_revisit():
    """재방문 시뮬레이션 테스트"""
    print("=" * 60)
    print("재방문 시뮬레이션 검증 테스트")
    print("=" * 60)

    manager = PersonaManager()

    # 1. 페르소나 목록 확인
    print("\n[1] 페르소나 목록 확인")
    personas = manager.get_all_personas()

    for p in personas:
        print(f"  - {p.name}")
        print(f"    ANDROID_ID: {p.android_id}")
        print(f"    총 세션: {p.total_sessions}")
        print(f"    상태: {p.status.value if hasattr(p.status, 'value') else p.status}")
        print(f"    Chrome 백업: {p.chrome_data_path or 'None'}")
        print()

    # 2. Persona_01 찾기
    print("\n[2] Persona_01 찾기")
    persona_01 = None
    for p in personas:
        if "Persona_01" in p.name:
            persona_01 = p
            break

    if not persona_01:
        print("  [ERROR] Persona_01을 찾을 수 없습니다!")
        return False

    print(f"  Found: {persona_01.name}")
    print(f"  ANDROID_ID: {persona_01.android_id}")

    # 3. 현재 ANDROID_ID 확인
    print("\n[3] 현재 디바이스 상태")
    status = await manager.check_device_status()
    original_android_id = status['android_id']
    print(f"  현재 ANDROID_ID: {original_android_id}")
    print(f"  루팅 상태: {status['is_rooted']}")

    # 4. 쿨다운 체크 및 강제 해제
    print("\n[4] 쿨다운 상태 확인")
    if hasattr(persona_01, 'status'):
        current_status = persona_01.status.value if hasattr(persona_01.status, 'value') else str(persona_01.status)
        print(f"  현재 상태: {current_status}")

        if 'cooling' in current_status.lower() or 'COOLING' in str(persona_01.status):
            print("  쿨다운 중 - 강제 해제...")
            if hasattr(persona_01, 'finish_cooldown'):
                persona_01.finish_cooldown()
                manager.update_persona(persona_01)
                print("  쿨다운 해제 완료")

    # 5. 재방문 전 NNB 쿠키 확인 시도
    print("\n[5] 재방문 전 NNB 쿠키 확인")
    try:
        nnb_before, cookies_before = await get_nnb_cookie()
        if nnb_before:
            print(f"  NNB 발견: {nnb_before.value[:20] if nnb_before.value else '(encrypted)'}...")
            print(f"  암호화: {nnb_before.encrypted}")
        else:
            print(f"  NNB 없음 (총 {len(cookies_before)}개 네이버 쿠키)")
    except Exception as e:
        print(f"  쿠키 조회 실패: {e}")
        nnb_before = None

    # 6. Persona_01로 전환
    print("\n[6] Persona_01로 전환")
    print(f"  예상 ANDROID_ID: {persona_01.android_id}")

    result = await manager.switch_to_persona(persona_01)
    print(f"  전환 성공: {result.success}")
    print(f"  ID 변경: {result.identity_changed}")
    print(f"  Chrome 복원: {getattr(result, 'chrome_data_restored', 'N/A')}")
    print(f"  소요 시간: {result.duration_sec:.1f}초")

    if not result.success:
        print(f"  [ERROR] 전환 실패: {result.error_message}")
        return False

    # 7. 전환 후 ANDROID_ID 확인
    print("\n[7] 전환 후 확인")
    new_status = await manager.check_device_status()
    print(f"  새 ANDROID_ID: {new_status['android_id']}")
    print(f"  예상값 일치: {new_status['android_id'] == persona_01.android_id}")

    # 8. Chrome 시작 및 네이버 접속
    print("\n[8] Chrome으로 네이버 접속")
    chrome = ChromeDataManager()
    await chrome.start_chrome("https://www.naver.com")

    print("  Chrome 시작됨, 5초 대기...")
    await asyncio.sleep(5)

    # 9. NNB 쿠키 확인
    print("\n[9] 재방문 후 NNB 쿠키 확인")
    try:
        nnb_after, cookies_after = await get_nnb_cookie()
        if nnb_after:
            print(f"  NNB 발견: {nnb_after.value[:20] if nnb_after.value else '(encrypted)'}...")
            print(f"  암호화: {nnb_after.encrypted}")
        else:
            print(f"  NNB 없음 (총 {len(cookies_after)}개 네이버 쿠키)")

        # 네이버 쿠키 목록 출력
        print("\n  네이버 쿠키 목록:")
        for c in cookies_after[:10]:
            val = c.value[:15] + "..." if c.value and len(c.value) > 15 else (c.value or "(encrypted)")
            print(f"    - {c.name}: {val}")

    except Exception as e:
        print(f"  쿠키 조회 실패: {e}")
        nnb_after = None

    # 10. 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    print(f"  페르소나: {persona_01.name}")
    print(f"  ANDROID_ID 변경: {original_android_id} -> {new_status['android_id']}")
    print(f"  예상 ID 일치: {new_status['android_id'] == persona_01.android_id}")
    print(f"  Chrome 복원: {getattr(result, 'chrome_data_restored', 'N/A')}")

    if nnb_before and nnb_after:
        same_nnb = nnb_before.value == nnb_after.value if (nnb_before.value and nnb_after.value) else "비교 불가 (암호화)"
        print(f"  NNB 유지: {same_nnb}")
    else:
        print(f"  NNB 유지: 확인 필요")

    # 11. 원래 ANDROID_ID로 복원
    print("\n[11] 원래 ANDROID_ID로 복원")
    from persona_manager.device_identity import DeviceIdentityManager
    identity_manager = DeviceIdentityManager()
    restore_result = await identity_manager.set_android_id(original_android_id)
    print(f"  복원 성공: {restore_result.success}")
    print(f"  현재 ID: {restore_result.new_value}")

    print("\n" + "=" * 60)
    print("[PASS] 재방문 시뮬레이션 테스트 완료!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = asyncio.run(test_revisit())
    sys.exit(0 if success else 1)
