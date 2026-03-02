# Claude Code 온디바이스 아키텍처

> **문서 목적**: 상위 프로젝트(CareOn) 기획자에게 새로운 아키텍처 방향 공유
> **작성일**: 2026-01-10
> **상태**: 설계 완료, 구현 대기

---

## 1. 배경: 기존 방식의 한계

### 현재 구조
```
[Ubuntu 서버] ──ADB over USB/TCP──> [Android 디바이스]
     │
     ├── DeepSeek API (AI 판단)
     ├── droidrun Portal (UI 탐지)
     └── ADB 명령 (터치/스와이프)
```

### 문제점
1. **서버 의존성**: Ubuntu 서버가 꺼지면 전체 시스템 중단
2. **네트워크 레이턴시**: ADB 명령마다 USB/TCP 오버헤드
3. **확장성 제한**: 디바이스 추가 시 서버 부하 증가
4. **규칙 기반 한계**: DeepSeek 미사용, 순수 텍스트 매칭으로 동적 UI 대응 불가

---

## 2. 새로운 아키텍처: "온디바이스 자율 주행"

### 핵심 아이디어
**디바이스 내부에서 Claude Code가 직접 세션을 관리**

```
┌─────────────────────────────────────────────────────────────────┐
│  Android Device (Termux + proot-distro Ubuntu)                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Session Manager                                         │   │
│  │  ┌───────────────┐  ┌───────────────┐                   │   │
│  │  │ Traffic Bot   │  │ Claude Code   │                   │   │
│  │  │ (DeepSeek)    │  │ (셀프 치유)   │                   │   │
│  │  │ - 평소 작업   │  │ - 실패 시만   │                   │   │
│  │  │ - 빠른 실행   │  │   소환        │                   │   │
│  │  └───────┬───────┘  └───────┬───────┘                   │   │
│  │          │ 실패 시           │ 코드 수정                │   │
│  │          └──────────────────>│                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                       │ 로컬 ADB (127.0.0.1:5555)              │
│                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Android System                                          │   │
│  │  - 네이버 앱                                             │   │
│  │  - /sdcard/personas/ (1,000명 영혼 창고)                │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐            ┌─────────────────┐
│  Supabase       │            │  Claude API     │
│  - campaigns    │            │  (Max+ 무제한)  │
│  - profiles     │            │                 │
└─────────────────┘            └─────────────────┘
```

---

## 3. 핵심 기능

### 3.1 셀프 치유 시스템

```bash
# supervisor.sh
while true; do
    python3 traffic_bot.py
    if [ $? -ne 0 ]; then
        # 실패 시 Claude Code 소환
        echo "에러 분석 후 코드 수정해줘" | claude
    fi
done
```

**장점**:
- 네이버 UI 변경 시 자동 대응
- 24시간 무인 운영 가능
- Max+ 플랜으로 비용 무제한

### 3.2 페르소나 스와핑 (1,000명 관리)

**기존 방식**: 로그아웃 → 로그인 → 캡차 발생 (실패)

**새로운 방식**: 앱 데이터(tar.gz) 통째로 스왑

```python
# 페르소나 교체 (로그인 상태 유지)
def swap_persona(uuid):
    adb_shell("pm clear com.nhn.android.search")  # 앱 초기화
    adb_shell(f"tar -xzf /sdcard/personas/{uuid}/backup.tar.gz -C /data/data/...")
    adb_shell("chown -R u0_a123:u0_a123 /data/data/...")  # 권한 복구
    # 앱 실행 → 이미 로그인된 상태!
```

### 3.3 하드웨어 위장

```python
# 매 세션마다 다른 기기로 인식
settings put secure android_id {랜덤값}
# GPS 텔레포트
am broadcast -a com.fakegps.SET_LOCATION --ef lat 35.15 --ef lng 129.16
```

---

## 4. Supabase 스키마

### profiles 테이블
| 컬럼 | 타입 | 설명 |
|------|------|------|
| uuid | TEXT | 페르소나 ID |
| device_config | JSONB | android_id, imei, mac, model |
| location | JSONB | lat, lng, label |
| trust_score | INT | 신뢰도 (활동 시 +1) |
| status | TEXT | idle / active / banned |
| last_active | TIMESTAMP | 쿨타임 계산용 |

### 작업 지시서 JSON
```json
{
  "session_id": "job_20250110_001",
  "persona": {
    "uuid": "user_8829",
    "device_config": { "android_id": "af82...", "model": "Galaxy S24" },
    "location": { "lat": 35.15, "lng": 129.16 }
  },
  "mission": {
    "target_keyword": "해운대 맛집",
    "target_url": "blog.naver.com/...",
    "action_plan": "search_and_click"
  }
}
```

---

## 5. 구현 로드맵

| Phase | 작업 | 예상 기간 |
|-------|------|-----------|
| **1** | 환경 구축 (proot-distro + 로컬 ADB) | - |
| **2** | 페르소나 매니저 (앱 데이터 스왑 검증) | - |
| **3** | 셀프 치유 시스템 (supervisor.sh) | - |
| **4** | 세션 매니저 통합 | - |
| **5** | 1,000명 페르소나 생성/숙성 | - |

---

## 6. 비용 분석

| 항목 | 현재 | 새로운 방식 |
|------|------|-------------|
| 서버 | VPS $30-50/월 | $0 (디바이스 내장) |
| DeepSeek | $0 (미사용) | ~$10/월 (판단용) |
| Claude | $0 | Max+ 구독 (무제한) |
| **총합** | **$30-50/월** | **Max+ 구독만** |

---

## 7. 연관 프로젝트 영향

### kt-cctv-landing (세일즈 엔진)
- **변경 없음**: 트래픽 엔진 API 인터페이스 유지
- 내부 구현만 변경 (서버 → 온디바이스)

### blog-archetype (콘텐츠 전략)
- **변경 없음**: 캠페인/키워드 제공 방식 동일

---

## 8. 다음 단계

1. **환경 결정**: Linux Deploy vs proot-distro
2. **PoC 구현**: 페르소나 1명으로 전체 플로우 테스트
3. **스케일업**: 1,000명 페르소나 생성 및 관리

---

*이 문서는 상위 프로젝트 기획자와의 맥락 공유를 위해 작성되었습니다.*
