# 빠른 시작 가이드

> 5분 안에 첫 실행까지

## 1. 설치

```bash
# 프로젝트 클론
git clone <repo-url>
cd naver-ai-evolution

# 패키지 설치 (editable mode)
pip install -e .

# 의존성만 설치 (개발용)
pip install -e ".[dev]"
```

## 2. 디바이스 연결 확인

```bash
# ADB 연결 확인
adb devices

# 출력 예시:
# List of devices attached
# R3CW60BHSAT    device
```

## 3. 시스템 상태 확인

```bash
naver status
```

출력 예시:
```
[ ADB 연결 ]
  ✓ 연결된 디바이스: 1개
    - R3CW60BHSAT

[ DroidRun Portal ]
  ✓ Portal APK 설치됨
  ✓ Accessibility Service 활성화

[ 페르소나 통계 ]
  총 페르소나: 10개
  총 세션: 45회
```

## 4. 첫 번째 세션 실행

### 방법 1: 키워드 검색

```bash
# 기본 실행 (3개 페이지뷰)
naver run session --keywords "맛집 추천"

# 여러 키워드
naver run session -k "맛집" -k "여행" -k "IT뉴스"

# 페이지뷰 수 지정
naver run session -k "맛집" --pageviews 5
```

### 방법 2: URL 직접 방문

```bash
naver run session --urls "https://blog.naver.com/example"
```

### 방법 3: Dry Run (테스트)

```bash
# 실제 실행 없이 설정만 확인
naver run session -k "맛집" --dry-run
```

## 5. 핵심 명령어 요약

| 하고 싶은 것 | 명령어 |
|-------------|--------|
| 상태 확인 | `naver status` |
| 단일 세션 | `naver run session -k "키워드"` |
| 다중 세션 | `naver run campaign -s 5 -k "키워드"` |
| 페르소나 목록 | `naver persona list` |
| 페르소나 생성 | `naver persona create 10` |
| 스모크 테스트 | `naver test smoke` |
| 도움말 | `naver --help` |

## 6. 다음 단계

- **캠페인 실행**: `naver run campaign --sessions 10`
- **페르소나 관리**: [PERSONA_SYSTEM_DESIGN.md](PERSONA_SYSTEM_DESIGN.md)
- **전체 아키텍처**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **실행 흐름 상세**: [EXECUTION_FLOW.md](EXECUTION_FLOW.md)

---

## 문제 해결

### Portal 미설치

```bash
# Portal 상태 확인
naver debug portal

# APK 설치 (수동)
adb install path/to/portal.apk
```

### 디바이스 미연결

```bash
# USB 디버깅 확인
adb devices

# 권한 문제 시
adb kill-server
adb start-server
```

### 페르소나 없음

```bash
# 10개 페르소나 생성
naver persona create 10

# 확인
naver persona list
```

---

*빠른 시작 완료! 더 자세한 내용은 [EXECUTION_FLOW.md](EXECUTION_FLOW.md)를 참고하세요.*
