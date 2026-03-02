# 재방문 시뮬레이션 검증 지시서

> **작성일**: 2025-12-15
> **목표**: 같은 페르소나로 재방문 시 NNB 쿠키가 유지되어 "재방문자"로 인식되는지 검증

---

## 1. 검증 목표

**핵심 질문**:
> "Persona_01로 다시 방문하면 네이버가 '재방문자'로 인식하는가?"

### 성공 기준
- [ ] Chrome 데이터 복원 성공
- [ ] NNB 쿠키가 이전 세션과 동일
- [ ] 네이버가 같은 사용자로 인식

---

## 2. 현재 상태

```
Persona_01:
  - ANDROID_ID: 4823c1ee801f87ea
  - 마지막 방문: "맛집" 검색 (13:44)
  - Chrome 백업: /sdcard/personas/{id}/chrome_data (3.3MB)
  - 상태: COOLING_DOWN (30분 쿨다운 중)

Persona_02:
  - ANDROID_ID: 376f30cad884bf4b
  - 마지막 방문: "여행" 검색 (14:04)
  - Chrome 백업: 있음
  - 상태: COOLING_DOWN
```

---

## 3. 테스트 단계

### 3.1 준비: 쿨다운 무시하고 페르소나 상태 확인

```bash
cd naver-ai-evolution

# 페르소나 목록 확인
python scripts/run_pipeline.py --list-personas
```

### 3.2 테스트 A: Persona_01 재방문

```python
# Python 스크립트로 직접 실행
import asyncio
import sys
sys.path.insert(0, 'src/shared')

from persona_manager import PersonaManager, PersonaStatus
from portal_client import PortalClient

async def test_revisit():
    manager = PersonaManager()

    # 1. Persona_01 찾기
    personas = manager.get_all_personas()
    persona_01 = next((p for p in personas if "Persona_01" in p.name), None)

    if not persona_01:
        print("Persona_01 not found!")
        return

    print(f"Found: {persona_01.name}")
    print(f"  - ANDROID_ID: {persona_01.android_id}")
    print(f"  - 총 세션: {persona_01.total_sessions}")
    print(f"  - 상태: {persona_01.status}")
    print(f"  - Chrome 백업: {persona_01.chrome_data_path}")

    # 2. 쿨다운 강제 해제 (테스트용)
    if persona_01.status == PersonaStatus.COOLING_DOWN:
        print("\n쿨다운 강제 해제...")
        persona_01.finish_cooldown()
        manager.update_persona(persona_01)

    # 3. 전환 전 현재 ANDROID_ID 기록
    print("\n현재 디바이스 ANDROID_ID 확인...")
    status = await manager.check_device_status()
    print(f"  - 현재 ID: {status['android_id']}")

    # 4. Persona_01로 전환
    print("\nPersona_01로 전환...")
    result = await manager.switch_to_persona(persona_01)
    print(f"  - 전환 성공: {result.success}")
    print(f"  - ID 변경: {result.identity_changed}")
    print(f"  - Chrome 복원: {result.chrome_data_restored}")

    # 5. 변경된 ANDROID_ID 확인
    new_status = await manager.check_device_status()
    print(f"  - 새 ID: {new_status['android_id']}")
    print(f"  - 페르소나 매칭: {new_status['persona_match']}")

    # 6. Chrome 시작하여 네이버 접속
    print("\nChrome으로 네이버 접속...")
    from persona_manager import ChromeDataManager
    chrome = ChromeDataManager()
    await chrome.start_chrome("https://www.naver.com")

    print("\n=== 수동 확인 필요 ===")
    print("1. Chrome 개발자 도구 열기 (PC에서)")
    print("2. chrome://inspect → Remote Target → 태블릿 Chrome")
    print("3. Application → Cookies → .naver.com")
    print("4. NNB 쿠키 값 확인")
    print("5. 이전 값과 비교")
    print("========================")

    return persona_01

asyncio.run(test_revisit())
```

### 3.3 NNB 쿠키 확인 방법

**방법 A: ADB로 직접 확인 (루팅)**
```bash
# Chrome 쿠키 DB에서 NNB 조회
adb shell "su -c 'sqlite3 /data/data/com.android.chrome/app_chrome/Default/Cookies \"SELECT name, value FROM cookies WHERE name=\\\"NNB\\\"\"'"
```

**방법 B: Chrome DevTools (PC 연결 시)**
1. PC Chrome에서 `chrome://inspect` 열기
2. 태블릿 Chrome 페이지 선택
3. DevTools → Application → Cookies
4. NNB 값 확인

### 3.4 비교 데이터 수집

| 항목 | 첫 방문 (예상) | 재방문 |
|------|---------------|--------|
| ANDROID_ID | 4823c1ee801f87ea | |
| NNB 쿠키 | (이전 값) | (새 값) |
| 동일 여부 | - | ✅/❌ |

---

## 4. 기대 결과

### 성공 시나리오
```
1. Chrome 데이터 복원 → NNB 쿠키 그대로 복원
2. 네이버 접속 → 기존 NNB 쿠키 사용
3. 네이버 서버: "이 사용자 전에 왔었네!" (재방문자)
```

### 실패 시나리오
```
1. Chrome 데이터 복원 실패 → NNB 없음
2. 네이버 접속 → 새 NNB 쿠키 발급
3. 네이버 서버: "새로운 사용자네" (첫 방문자)
```

---

## 5. 피드백 양식

```markdown
# 재방문 시뮬레이션 검증 결과

## 테스트 환경
- **테스트 일시**: YYYY-MM-DD HH:MM
- **페르소나**: Persona_01

---

## 결과

### Chrome 데이터 복원
- 복원 성공: [True/False]
- 복원된 경로: [경로]

### ANDROID_ID
- 기대값: 4823c1ee801f87ea
- 실제값: [값]
- 일치: [True/False]

### NNB 쿠키 비교
- 첫 방문 NNB: [값 또는 "기록 없음"]
- 재방문 NNB: [값]
- 동일 여부: [True/False/확인불가]

### 네이버 인식
- 재방문자로 인식: [True/False/불명확]
- 근거: [설명]

---

## 결론
[재방문 시뮬레이션 성공/실패/부분성공]

## 문제점 (있다면)
[설명]

## 제안
[다음 단계]
```

---

## 6. 추가 검증 (선택)

### NNB 쿠키 변화 추적

```python
async def track_nnb():
    """NNB 쿠키 변화 추적"""
    from persona_manager import ChromeDataManager

    chrome = ChromeDataManager()

    # 현재 NNB 확인
    cookies = await chrome.get_naver_cookies()
    nnb = next((c for c in cookies if c.name == "NNB"), None)

    if nnb:
        print(f"NNB Cookie: {nnb.value}")
        print(f"  - Host: {nnb.host_key}")
        print(f"  - Encrypted: {nnb.encrypted}")
    else:
        print("NNB Cookie not found!")

    return nnb
```

---

*작성: Claude Code (원격)*
*다음 단계: 재방문 검증 결과에 따라 장시간 운영 테스트 또는 문제 해결*
