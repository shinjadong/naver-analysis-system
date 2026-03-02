# 네이버 사용자 식별 체계 종합 분석

> "이놈이 그놈이다" — 네이버가 동일 사용자를 식별하는 원리

## 개요

네이버는 **회원 로그인 없이도** 방문자를 식별할 수 있는 다층 추적 시스템을 운용합니다.
이 문서는 실험과 트래픽 분석을 통해 확인된 네이버의 사용자 식별 체계를 종합합니다.

---

## 핵심 원리: 4-Layer 식별 체계

```
┌──────────────────────────────────────────────────────────────────┐
│                    네이버 4-Layer 식별 체계                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 1: 영구 식별자 (Permanent)                                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │    NNB     │  │    NID     │  │     iv     │                │
│  │ 디바이스ID │  │  계정 ID   │  │ 서버 UUID  │                │
│  │ 만료:2050  │  │ 로그인시   │  │ 영구 저장  │                │
│  └────────────┘  └────────────┘  └────────────┘                │
│                                                                  │
│  Layer 2: 세션 식별자 (Session)                                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐        │
│  │   SRT5     │  │   SRT30    │  │ _naver_usersession │        │
│  │  5분 만료  │  │  30분 만료 │  │    세션 쿠키       │        │
│  └────────────┘  └────────────┘  └────────────────────┘        │
│                                                                  │
│  Layer 3: 페이지 식별자 (Page-level)                             │
│  ┌────────────┐  ┌────────────┐                                 │
│  │ page_uid   │  │ PM_CK_loc  │                                 │
│  │ 페이지별   │  │ 위치 추적  │                                 │
│  └────────────┘  └────────────┘                                 │
│                                                                  │
│  Layer 4: 실험/광고 식별자 (Experiment)                          │
│  ┌────────────┐  ┌──────────────────┐                           │
│  │    BUC     │  │ __Secure-BUCKET  │                           │
│  │ A/B 테스트 │  │ 보안 버킷        │                           │
│  └────────────┘  └──────────────────┘                           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: 영구 식별자 (가장 중요)

### 1.1 NNB 쿠키 — 디바이스(브라우저) 식별자

**네이버의 PRIMARY 식별자**. 로그인 없이도 "이 디바이스는 전에 온 적 있다"를 판별.

| 속성 | 값 |
|------|-----|
| 쿠키명 | `NNB` |
| 도메인 | `.naver.com` |
| 형식 | 12자리 영숫자 (예: `N42LJ2QRSQ7GS`) |
| 만료 | 2050년 (사실상 영구) |
| 생성 시점 | 최초 방문 시 서버가 부여 |
| 변경 조건 | 쿠키 삭제 시 새 값 발급 |

**실험으로 확인된 사실**:
- IP 변경 + 쿠키 삭제 = 완전히 새로운 NNB 발급 → **신규 사용자**로 인식
- 쿠키 삭제 없이 IP만 변경 = 동일 NNB 유지 → **동일 사용자**로 인식
- NNB 쿠키 유지(Chrome 데이터 복원) = **재방문자**로 인식 (실험 검증 완료)

```
실험 결과 비교:
  Session A (최초):  NNB = N42LJ2QRSQ7GS
  Session B (삭제후): NNB = I46ZMQWHKM7WS  ← 완전히 다른 값
  Session C (복원후): NNB = N42LJ2QRSQ7GS  ← 동일! 재방문자 인식
```

### 1.2 NID 쿠키 — 계정 식별자

네이버 **로그인 상태**에서 활성화되는 계정 기반 식별자.

| 속성 | 값 |
|------|-----|
| 쿠키명 | `NID_AUT`, `NID_SES`, `NID_JKL` |
| 도메인 | `.naver.com` |
| 특징 | 인코딩된 계정 정보 (527=...) |
| 역할 | 크로스 디바이스 식별 (PC ↔ 모바일 연결) |
| 변경 조건 | 로그아웃 시 무효화 |

**핵심**: NID는 로그인 시에만 작동. 비로그인 상태에서는 NNB가 유일한 영구 식별자.

### 1.3 iv (Identifier Vector) — 서버측 영구 식별자

서버 사이드에서 관리되는 **UUIDv4** 식별자.

| 속성 | 값 |
|------|-----|
| 형식 | UUIDv4 (예: `b09f2d3a-7c41-4e8b-9a15-2f6c8d1e3b74`) |
| 저장 위치 | 서버 사이드 (클라이언트에서 URL 파라미터로 전달) |
| 영속성 | 쿠키 삭제해도 서버에 남을 수 있음 |
| 용도 | 세션 추적, 행동 분석, 개인화 |
| 전달 방식 | URL 파라미터 `iv=` |

```
실험 관찰:
  Session A: iv = b09f2d3a-7c41-4e8b-9a15-2f6c8d1e3b74
  Session B: iv = e71a4c56-2d89-4f13-b623-8a9d0e5f7c41  ← 새 UUID
```

---

## Layer 2: 세션 식별자

### SRT 쿠키 시리즈

| 쿠키 | 만료 | 역할 |
|------|------|------|
| `SRT5` | 5분 | 단기 세션 추적 (클릭 후 이탈 감지) |
| `SRT30` | 30분 | 중기 세션 추적 (일반 브라우징) |
| `_naver_usersession_` | 세션 | 탭 닫을 때까지 유지 |

**의미**: 사용자가 "지금 활동 중인지" 판별. 5분 이내 재방문은 동일 세션으로 카운트.

---

## Layer 3: 페이지 식별자

### page_uid

모든 네이버 요청에 포함되는 **고유 페이지 ID**.

```
예: s_4f7e2a1b3c5d8e9f
```

- 매 페이지 로드마다 새로 생성
- NLOG/TIVAN 로깅의 핵심 키
- 이 값으로 페이지별 체류시간, 스크롤 깊이 등을 추적

### PM_CK_loc

사용자의 **설정 지역** 쿠키. 콘텐츠 개인화에 사용.

---

## Layer 4: 실험/광고 식별자

### BUC (Bucket)

A/B 테스트 실험군 할당 쿠키.

| 속성 | 값 |
|------|-----|
| 쿠키명 | `BUC`, `__Secure-BUCKET` |
| 역할 | 검색 결과, UI, 알고리즘 변형 테스트 |
| 영속성 | 영구 (실험 일관성 유지) |

---

## 추적 시스템 5종

네이버는 5개의 전문 추적 시스템을 운용합니다:

### 1. NLOG (세션 로깅)
```
엔드포인트: nlog.naver.com/n
전송 방식: Image pixel (1x1 GIF)
주요 파라미터: u (NNB), r (referrer), page (서비스), sid (세션ID)
역할: 기본 페이지뷰, 클릭 이벤트 기록
```

### 2. TIVAN SC2 (행동 추적)
```
엔드포인트: tivan.naver.com/sc2/{code}/
코드 체계:
  sc2/1  = 페이지 뷰 (초기 로드)
  sc2/11 = 체류시간 보고 (30초, 60초, 90초...)
  sc2/12 = 스크롤/인터랙션 이벤트
전송 방식: Beacon API (sendBeacon)
역할: 콘텐츠 소비 행동 측정
```

### 3. TIVAN Performance (성능 추적)
```
엔드포인트: tivan.naver.com/g/{codes}/
측정 항목: LCP, FID, CLS, page load time
역할: Core Web Vitals 모니터링
```

### 4. GFA (광고 행동)
```
엔드포인트: g.tivan.naver.com/gfa/
전송 방식: POST (암호화된 페이로드)
역할: 광고 노출/클릭/전환 추적
특징: 데이터가 암호화되어 내용 해독 불가
```

### 5. VETA (광고 입찰/추적)
```
엔드포인트: siape.veta.naver.com, nam.veta.naver.com
프로토콜: OpenRTB 기반
역할: 실시간 광고 입찰 및 추적
데이터: 디바이스 정보, 위치, 관심사 전달
```

---

## 브라우저 핑거프린팅

### gfp-display-sdk.js

네이버의 핑거프린팅 스크립트. 다음 정보를 수집:

| 기술 | 수집 데이터 |
|------|------------|
| Canvas Fingerprint | GPU/렌더링 엔진 고유 해시 |
| WebGL Fingerprint | 그래픽 드라이버 정보 |
| Audio Fingerprint | AudioContext 처리 특성 |
| 화면 해상도 | screen.width/height, devicePixelRatio |
| 폰트 목록 | 설치된 시스템 폰트 |
| 플러그인 | navigator.plugins |
| 시간대 | Intl.DateTimeFormat, timezoneOffset |
| 언어 | navigator.languages |
| 하드웨어 | navigator.hardwareConcurrency, deviceMemory |

**핵심**: 쿠키를 삭제해도 핑거프린트가 동일하면 "같은 디바이스"로 **추정** 가능.
하지만 실험에서 확인된 바, **NNB 쿠키가 없으면** 네이버는 핑거프린트만으로는 재방문자로 확정하지 않음.

---

## 동일인 판별 로직 (종합)

### 판별 시나리오

| 시나리오 | NNB | NID | IP | 핑거프린트 | 판정 |
|----------|-----|-----|-----|-----------|------|
| 첫 방문 | 없음→새 발급 | - | 신규 | 신규 | **신규 사용자** |
| 재방문 (쿠키 유지) | 동일 | - | 동일/다름 | 동일 | **재방문자** |
| 쿠키 삭제 후 | 새 발급 | - | 동일 | 동일 | **신규 사용자** (확인됨) |
| IP+쿠키 모두 변경 | 새 발급 | - | 다름 | 동일 | **신규 사용자** (확인됨) |
| 로그인 상태 | 동일 | 있음 | 무관 | 무관 | **계정 기반 식별** |
| 다른 기기 로그인 | 다름 | 동일 | 다름 | 다름 | **동일 계정** (크로스디바이스) |

### 핵심 결론

```
판별 우선순위:
  1. NID (로그인) → 확정적 식별 (크로스디바이스 가능)
  2. NNB (쿠키)  → 디바이스 수준 식별 (가장 일반적)
  3. iv (서버)   → 서버측 세션 연결
  4. Fingerprint → 보조 수단 (단독으로는 불충분)
```

---

## 블로그 조회수 카운트 조건

실험을 통해 확인된 블로그 조회수 증가 조건:

```
조회수 +1 조건 = unique NNB + new page_uid + 최소 체류시간
```

| 조건 | 설명 |
|------|------|
| unique NNB | 동일 NNB로 반복 방문 시 카운트 안됨 |
| new page_uid | 매 방문마다 새 page_uid 필요 |
| 체류시간 | 바운스(즉시 이탈) 시 카운트 안될 수 있음 |
| 쿨다운 | 동일 NNB의 재조회는 일정 시간 후 |

---

## 실용적 시사점: 페르소나 시스템

위 분석을 바탕으로 설계된 페르소나 관리 시스템:

### 페르소나 구성요소

```python
@dataclass
class Persona:
    persona_id: str
    android_id: str        # ANDROID_ID (루팅으로 변경)
    gsf_id: str           # Google Services Framework ID
    advertising_id: str    # 광고 ID
    nnb_cookie: str       # NNB 쿠키값 (Chrome 데이터 복원)
    behavior_profile: BehaviorProfile  # 행동 패턴
    chrome_data_path: str  # Chrome 데이터 백업 경로
```

### 페르소나 전환 플로우

```
1. PersonaStore에서 페르소나 선택 (라운드로빈/가중 랜덤)
2. DeviceIdentityManager로 ANDROID_ID 변경 (su 필요)
3. Chrome 데이터 복원 (쿠키 = NNB 복원)
4. 검색 → 블로그 방문 (BehaviorInjector로 자연스러운 행동)
5. Chrome 데이터 백업 (새 쿠키 상태 저장)
6. PersonaStore에 상태 저장
```

### Chrome 데이터 관리

```
경로: /data/data/com.android.chrome/app_chrome/Default/
필수 파일:
  - Cookies (SQLite, encrypted) → NNB, SRT, BUC 등
  - Web Data
  - Preferences
  - Local State

조작 방법: 직접 DB 수정이 아닌 폴더 통째로 백업/복원
  → Chrome의 cookie_encrypted_key 문제 회피
```

---

## 탐지 회피를 위한 핵심 지침

| 항목 | 방법 |
|------|------|
| NNB 쿠키 | 페르소나별 Chrome 데이터 백업/복원으로 관리 |
| IP 주소 | 비행기모드 토글로 LTE IP 회전 (또는 프록시) |
| ANDROID_ID | 루팅 후 Settings.Secure DB 직접 수정 |
| 행동 패턴 | BehaviorInjector (베지어 커브, 가변 속도 스크롤, 타이핑) |
| 체류시간 | 자연스러운 분포 (30~180초, 가우시안) |
| 스크롤 패턴 | 빠른→느린→빠른 비선형 패턴 |
| 검색 키워드 | 타겟 외 일반 키워드 혼합 (3:1 비율) |
| 시간 분포 | 출퇴근시간, 점심시간 등 자연스러운 분포 |

---

## 참조 데이터

### 규모 (분석 완료)

- 추적 도메인: **74개**
- URL 파라미터: **218종**
- 쿠키: **40종**
- 이벤트 타입: **50종**

### 실험 이력

| 실험 | 날짜 | 결과 |
|------|------|------|
| 핑거프린트 캡처 | 2025-12-13 | NNB 비교, 98K→166K 이벤트, IV 변경 확인 |
| 루팅 테스트 | 2026-01-28 | ANDROID_ID 변경 성공, Chrome DB 스키마 분석 |
| 재방문 시뮬레이션 | 2026-02-05 | NNB 100% 동일, 쿠키 10개 보존, 재방문자 인식 |
| 리퍼러 테스트 | 2026-02-06 | CDP referrer 작동 확인, strict-origin-when-cross-origin |

---

## 관련 문서

| 문서 | 내용 |
|------|------|
| [NAVER_TRACKING_ANALYSIS.md](../01-tracking-system/NAVER_TRACKING_ANALYSIS.md) | 추적 시스템 전체 분석 (74도메인, 218파라미터) |
| [PERSONA_SYSTEM_DESIGN.md](PERSONA_SYSTEM_DESIGN.md) | 페르소나 시스템 설계 |
| [FINGERPRINT_EXPERIMENT_PROTOCOL.md](FINGERPRINT_EXPERIMENT_PROTOCOL.md) | 핑거프린트 실험 프로토콜 |
| [FINGERPRINT_FINDINGS.md](../05-experiments/FINGERPRINT_FINDINGS.md) | 핑거프린트 실험 결과 |
| [REVISIT_TEST_RESULT.md](../05-experiments/REVISIT_TEST_RESULT.md) | 재방문 시뮬레이션 결과 |
| [ROOTING_TEST_RESULTS.md](../05-experiments/ROOTING_TEST_RESULTS.md) | 루팅 테스트 결과 |
| [TRAFFIC_BOOSTING_STRATEGY.md](../01-tracking-system/TRAFFIC_BOOSTING_STRATEGY.md) | 트래픽 부스팅 전략 |

---

*종합 분석 일자: 2026-03-02*
*분석 기반: DeepSeek V3.2 Reasoner 분석 + 실험 데이터 + 트래픽 캡처*
