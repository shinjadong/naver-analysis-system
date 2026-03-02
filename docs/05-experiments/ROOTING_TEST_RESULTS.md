# 루팅 기반 기능 테스트 결과

> **테스트 일시**: 2025-12-15
> **테스트 디바이스**: Galaxy Tab S9+ (SM-X826N)
> **연결 방식**: 무선 디버깅 (10.137.181.243:34419)
> **루팅 상태**: Magisk 루팅됨

---

## 1. DroidRun Portal 설치 테스트

### 결과: SUCCESS

| 항목 | 상태 |
|------|------|
| APK 다운로드 | v0.4.7 (12MB) |
| 설치 | 성공 |
| 패키지명 | com.droidrun.portal |
| 접근성 서비스 | 활성화됨 |
| UI 트리 수신 | 정상 |

### 테스트 명령어

```bash
# Portal APK 다운로드
curl -L -o droidrun-portal.apk "https://github.com/droidrun/droidrun-portal/releases/download/v0.4.7/droidrun-portal-v0.4.7.apk"

# 설치
adb install -r -g -t droidrun-portal.apk

# 접근성 서비스 활성화
adb shell settings put secure enabled_accessibility_services com.droidrun.portal/com.droidrun.portal.service.DroidrunAccessibilityService
adb shell settings put secure accessibility_enabled 1

# 버전 확인
adb shell "content query --uri content://com.droidrun.portal/version"
# 결과: {"status":"success","data":"0.4.7"}

# UI 상태 확인
adb shell "content query --uri content://com.droidrun.portal/state"
# 결과: UI 트리 JSON 정상 수신
```

---

## 2. ANDROID_ID 변경 테스트

### 결과: SUCCESS

| 항목 | 값 |
|------|------|
| 원본 ANDROID_ID | `d4b550c3e9cec899` |
| 변경 테스트 값 | `test123abc456def` |
| 변경 성공 | YES |
| 복원 성공 | YES |

### 테스트 명령어

```bash
# 현재 ANDROID_ID 확인
adb shell settings get secure android_id
# 결과: d4b550c3e9cec899

# ANDROID_ID 변경 (루팅 필요)
adb shell "su -c 'settings put secure android_id test123abc456def'"

# 변경 확인
adb shell settings get secure android_id
# 결과: test123abc456def

# 원본으로 복원
adb shell "su -c 'settings put secure android_id d4b550c3e9cec899'"
```

### 결론

**루팅된 디바이스에서 ANDROID_ID 변경이 가능합니다.**

페르소나별로 다른 ANDROID_ID를 적용하여 네이버에 "다른 디바이스"로 인식시킬 수 있습니다.

---

## 3. Chrome 쿠키 직접 조작 테스트

### 결과: SUCCESS (조건부)

| 항목 | 상태 |
|------|------|
| 쿠키 DB 접근 | 성공 (루팅 필요) |
| 쿠키 읽기 | 성공 (값은 암호화됨) |
| 쿠키 삽입 | 성공 |
| 쿠키 DB 푸시 | 성공 |

### 쿠키 DB 위치

```
/data/data/com.android.chrome/app_chrome/Default/Cookies
```

### 쿠키 테이블 스키마

```sql
CREATE TABLE cookies (
    creation_utc INTEGER NOT NULL,
    host_key TEXT NOT NULL,
    top_frame_site_key TEXT NOT NULL,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    encrypted_value BLOB NOT NULL,
    path TEXT NOT NULL,
    expires_utc INTEGER NOT NULL,
    is_secure INTEGER NOT NULL,
    is_httponly INTEGER NOT NULL,
    last_access_utc INTEGER NOT NULL,
    has_expires INTEGER NOT NULL,
    is_persistent INTEGER NOT NULL,
    priority INTEGER NOT NULL,
    samesite INTEGER NOT NULL,
    source_scheme INTEGER NOT NULL,
    source_port INTEGER NOT NULL,
    last_update_utc INTEGER NOT NULL,
    source_type INTEGER NOT NULL,
    has_cross_site_ancestor INTEGER NOT NULL
);
```

### 발견된 네이버 쿠키

| host_key | name | 설명 |
|----------|------|------|
| .naver.com | NNB | 네이버 디바이스 ID |
| .naver.com | SRT5 | 5분 세션 쿠키 |
| .naver.com | SRT30 | 30분 세션 쿠키 |
| .naver.com | BUC | A/B 테스트 버킷 |
| .naver.com | NAC | 네이버 앱 쿠키 |
| .naver.com | NACT | 네이버 앱 쿠키 타임스탬프 |
| .naver.com | _naver_usersession_ | 유저 세션 |
| .blog.naver.com | BA_DEVICE | 블로그 디바이스 ID |

### 테스트 명령어

```bash
# 쿠키 DB 복사 (루팅 필요)
adb shell "su -c 'cp /data/data/com.android.chrome/app_chrome/Default/Cookies /data/local/tmp/Cookies.db && chmod 644 /data/local/tmp/Cookies.db'"

# 로컬로 가져오기
MSYS_NO_PATHCONV=1 adb pull /data/local/tmp/Cookies.db cookies.db

# 쿠키 삽입 (Python)
python -c "
import sqlite3
import time

conn = sqlite3.connect('cookies.db')
chrome_epoch = 11644473600000000
now_chrome = int(time.time() * 1000000) + chrome_epoch

conn.execute('''INSERT INTO cookies
    (creation_utc, host_key, top_frame_site_key, name, value, encrypted_value,
     path, expires_utc, is_secure, is_httponly, last_access_utc, has_expires,
     is_persistent, priority, samesite, source_scheme, source_port,
     last_update_utc, source_type, has_cross_site_ancestor)
    VALUES (?, '.naver.com', '', 'NNB', '', X'암호화된값',
            '/', 0, 0, 0, ?, 0, 0, 1, 0, 0, 80, ?, 0, 0)''',
    (now_chrome, now_chrome, now_chrome))
conn.commit()
"

# 디바이스에 다시 푸시
MSYS_NO_PATHCONV=1 adb push cookies.db /data/local/tmp/Cookies_modified.db
adb shell "su -c 'cp /data/local/tmp/Cookies_modified.db /data/data/com.android.chrome/app_chrome/Default/Cookies && chown u0_a264:u0_a264 /data/data/com.android.chrome/app_chrome/Default/Cookies && chmod 600 /data/data/com.android.chrome/app_chrome/Default/Cookies'"
```

### 제한 사항

1. **쿠키 값 암호화**: Chrome은 `encrypted_value` 필드에 암호화된 값을 저장
   - `value` 필드는 비어있거나 일부만 포함
   - 암호화 키는 디바이스별로 다름

2. **해결 방안**:
   - 방법 A: Chrome을 완전히 초기화 후 새 세션 시작 (쿠키 삭제)
   - 방법 B: 네이버 접속 후 생성된 쿠키를 페르소나별로 백업/복원
   - 방법 C: 암호화 키 추출 (복잡함)

### 결론

**쿠키 DB 구조 조작은 가능하지만, 값 암호화로 인해 직접 값 주입은 제한적입니다.**

**권장 접근법**:
1. 페르소나별로 Chrome 데이터 전체를 백업 (`/data/data/com.android.chrome/`)
2. 페르소나 전환 시 해당 데이터 복원
3. 또는 Chrome 대신 WebView 기반 브라우저 사용 (암호화 없음)

---

## 4. 종합 결론

### 페르소나 시스템 구현 가능성

| 기능 | 가능 여부 | 난이도 | 비고 |
|------|----------|--------|------|
| ANDROID_ID 변경 | ✅ 가능 | 쉬움 | 루팅 필요 |
| 광고 ID 변경 | ✅ 가능 | 쉬움 | 설정 앱 리셋 |
| Chrome 쿠키 백업/복원 | ✅ 가능 | 중간 | 전체 데이터 폴더 복원 |
| Chrome 쿠키 직접 주입 | ⚠️ 제한적 | 어려움 | 암호화 문제 |
| DroidRun Portal UI 탐지 | ✅ 가능 | 쉬움 | 접근성 서비스 |

### 권장 구현 전략

```
[Persona 전환 프로세스]

1. Chrome 종료
   adb shell am force-stop com.android.chrome

2. ANDROID_ID 변경
   adb shell "su -c 'settings put secure android_id {persona.android_id}'"

3. Chrome 데이터 복원 (페르소나별 백업된 데이터)
   adb shell "su -c 'rm -rf /data/data/com.android.chrome/app_chrome/Default'"
   adb shell "su -c 'cp -r /sdcard/personas/{persona_id}/chrome_data /data/data/com.android.chrome/app_chrome/Default'"
   adb shell "su -c 'chown -R u0_a264:u0_a264 /data/data/com.android.chrome/app_chrome/Default'"

4. Chrome 실행 & 네이버 접속
   → 네이버는 "이전에 왔던 그 사용자"로 인식

5. 세션 종료 시 Chrome 데이터 백업
   adb shell "su -c 'cp -r /data/data/com.android.chrome/app_chrome/Default /sdcard/personas/{persona_id}/chrome_data'"
```

---

## 5. 다음 단계

1. **PersonaManager 구현**
   - ANDROID_ID 변경 기능
   - Chrome 데이터 백업/복원 기능
   - 페르소나 DB (SQLite)

2. **PortalClient 구현**
   - DroidRun Portal 통신
   - UI 요소 탐지 및 정확한 좌표 획득

3. **기존 모듈 연동**
   - SessionManager + PersonaManager 통합
   - EngagementSimulator + BehaviorProfile 통합

---

*테스트 완료: 2025-12-15*
*환경: Windows 11 + Galaxy Tab S9+ (루팅)*
