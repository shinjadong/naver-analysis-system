# 네이버 분석 시스템 (Naver Analysis System)

> 네이버 추적/식별 시스템 종합 분석 및 대응 자동화 프레임워크

## 이 리포지토리는

네이버의 사용자 추적 및 식별 시스템을 **역분석**하고, 그 결과를 바탕으로 구축된 **자동화 대응 시스템**의 전체 기록입니다.

모든 AI 에이전트가 이 리포지토리와 동기화하여 네이버 시스템에 대한 완전한 이해를 공유할 수 있도록 설계되었습니다.

---

## 핵심 발견 요약

### 네이버 4-Layer 식별 체계

```
Layer 1 (영구)  : NNB 쿠키 (디바이스ID, 2050만료) + NID (계정) + iv (서버UUID)
Layer 2 (세션)  : SRT5 (5분) + SRT30 (30분) + _naver_usersession_
Layer 3 (페이지) : page_uid (페이지별 고유ID) + PM_CK_loc (위치)
Layer 4 (실험)  : BUC + __Secure-BUCKET (A/B 테스트)
```

### 동일인 판별 원리

| 판별 수단 | 우선순위 | 설명 |
|-----------|---------|------|
| **NID (로그인)** | 1순위 | 확정적 식별, 크로스디바이스 |
| **NNB (쿠키)** | 2순위 | 디바이스 수준, 비로그인 시 PRIMARY |
| **iv (서버)** | 3순위 | 서버측 세션 연결 |
| **Fingerprint** | 4순위 | 보조 수단 (단독 불충분) |

### 블로그 조회수 증가 조건

```
조회수 +1 = unique NNB + new page_uid + 최소 체류시간
```

### 규모

- **74**개 추적 도메인
- **218**종 URL 파라미터
- **40**종 쿠키
- **50**종 이벤트 타입
- **5**개 추적 시스템 (NLOG, TIVAN SC2, TIVAN Perf, GFA, VETA)

---

## 디렉토리 구조

```
naver-analysis-system/
│
├── README.md                    ← 현재 문서
├── INDEX.md                     ← 전체 문서 색인
│
├── docs/                        ← 분석 문서 (카테고리별)
│   ├── 01-tracking-system/      # 네이버 추적 시스템 분석
│   │   ├── NAVER_TRACKING_ANALYSIS.md   ★ 핵심: 전체 추적 시스템 분석
│   │   └── TRAFFIC_BOOSTING_STRATEGY.md # 트래픽 부스팅 전략
│   │
│   ├── 02-identification/       # 사용자 식별 체계
│   │   ├── NID_IDENTIFICATION.md        ★ 핵심: 동일인 식별 원리 종합
│   │   ├── PERSONA_SYSTEM_DESIGN.md     # 페르소나 시스템 설계
│   │   └── FINGERPRINT_EXPERIMENT_PROTOCOL.md  # 핑거프린트 실험
│   │
│   ├── 03-architecture/         # 시스템 아키텍처
│   │   ├── ARCHITECTURE.md              # 시스템 아키텍처 v0.4.0
│   │   ├── AGENT_ARCHITECTURE.md        # 4-Layer 에이전트 계층
│   │   ├── EXECUTION_FLOW.md            # 실행 흐름
│   │   ├── DROIDRUN_INTEGRATION.md      # DroidRun 통합
│   │   ├── AI_WORKFLOW_IMPLEMENTATION.md # AI 워크플로우
│   │   └── CLAUDE_ON_DEVICE_ARCHITECTURE.md  # 온디바이스 아키텍처
│   │
│   ├── 04-implementation/       # 구현 상세
│   │   ├── NAVER_CHROME_USE.md          # Chrome 자동화 스펙
│   │   ├── SESSION_MANAGER_IMPLEMENTATION.md  # 세션 매니저
│   │   ├── API_REFERENCE.md             # API 레퍼런스
│   │   ├── DEVELOPMENT.md               # 개발 가이드
│   │   ├── EXTENDING.md                 # 확장 가이드
│   │   ├── USAGE_GUIDE.md               # 사용 가이드
│   │   └── QUICKSTART.md                # 빠른 시작
│   │
│   ├── 05-experiments/          # 실험 결과
│   │   ├── FINGERPRINT_FINDINGS.md      ★ 핵심: IP+쿠키삭제=신규사용자 확인
│   │   ├── REVISIT_TEST_RESULT.md       ★ NNB 복원=재방문자 확인
│   │   ├── REVISIT_TEST_INSTRUCTIONS.md # 재방문 테스트 방법
│   │   ├── ROOTING_TEST_RESULTS.md      # ANDROID_ID 변경 성공
│   │   ├── TEST_RESULTS.md              # 전체 테스트 32/32 통과
│   │   └── PIPELINE_TEST_REPORT.md      # 파이프라인 테스트
│   │
│   ├── 06-setup/                # 환경 설정
│   │   ├── DEVICE_SETUP.md              # 디바이스 설정
│   │   └── PROJECT_SETUP.md             # 프로젝트 설정
│   │
│   ├── 07-roadmap/              # 로드맵
│   │   ├── IMPROVEMENT_ROADMAP.md       # 개선 로드맵
│   │   └── PROJECT_EVOLUTION_STORY.md   # 프로젝트 진화 스토리
│   │
│   ├── 08-reference/            # 기타 참조
│   │   ├── compass_artifact_*.md        # Compass 아티팩트
│   │   └── claude-code(local-samsung-laptop).md  # 개발 로그
│   │
│   └── 09-blog-direct-api/     # [신규] 네이버 블로그 Direct API 발행
│       ├── NAVER_BLOG_API_ANALYSIS.md   ★ SE ONE 에디터 API 역분석
│       ├── DIRECT_PUBLISHER_IMPLEMENTATION.md # DirectPublisher 구현
│       ├── COOKIE_AUTO_REFRESH.md       # 쿠키 자동 갱신 메커니즘
│       └── POC_TEST_RESULTS.md          # POC 테스트 결과
│
├── experiments/                 ← 실험 원본 데이터
│   ├── fingerprint_capture/     # 핑거프린트 캡처 데이터
│   │   └── FINDINGS.md
│   ├── network_capture/         # 네트워크 캡처 데이터
│   │   ├── capture_result.json  # 캡처 결과
│   │   └── naver_capture.pcap   # 패킷 캡처
│   ├── referrer_test/           # 리퍼러 테스트
│   │   └── test_referrer.py     # CDP 리퍼러 테스트 스크립트
│   └── rooting_tests/           # 루팅 테스트
│       └── ROOTING_TEST_RESULTS.md
│
├── src/                         ← 소스 코드 (Python)
│   ├── api/                     # FastAPI 서버
│   ├── campaign/                # 캠페인 관리
│   ├── shared/                  # 공유 모듈
│   │   ├── device_tools/        #   - ADB 도구 (BehaviorInjector)
│   │   ├── naver_chrome_use/    #   - Chrome 자동화 (CDP)
│   │   ├── persona_manager/     #   - 페르소나 관리
│   │   ├── persona_generator/   #   - 페르소나 생성
│   │   ├── session_manager/     #   - 세션 관리 (IP회전/쿠키)
│   │   ├── portal_client/       #   - UI 자동화 (DroidRun)
│   │   ├── smart_executor/      #   - 스마트 실행기
│   │   └── storyline_generator/ #   - 스토리라인 생성 (DeepSeek)
│   ├── scheduler/               # 캠페인 스케줄러
│   └── clients/                 # 외부 클라이언트
│
├── tests/                       ← 테스트 코드
├── scripts/                     ← 실행 스크립트
├── config/                      ← 설정 파일
│   ├── deepseek_config.yaml
│   ├── naver_profiles.yaml
│   └── sample_missions.csv
│
├── data/                        ← 데이터
│   └── keyword/                 # 키워드 CSV 파일
│
└── pyproject.toml               ← Python 프로젝트 설정
```

---

## 필수 읽기 순서 (AI 에이전트용)

새 세션에서 이 리포를 이해하기 위한 최적 순서:

### 1단계: 추적 시스템 이해
1. **[NID_IDENTIFICATION.md](docs/02-identification/NID_IDENTIFICATION.md)** — 동일인 식별 원리 종합
2. **[NAVER_TRACKING_ANALYSIS.md](docs/01-tracking-system/NAVER_TRACKING_ANALYSIS.md)** — 추적 시스템 전체 분석

### 2단계: 실험 결과 확인
3. **[FINGERPRINT_FINDINGS.md](docs/05-experiments/FINGERPRINT_FINDINGS.md)** — IP+쿠키삭제=신규사용자
4. **[REVISIT_TEST_RESULT.md](docs/05-experiments/REVISIT_TEST_RESULT.md)** — NNB 복원=재방문자
5. **[ROOTING_TEST_RESULTS.md](docs/05-experiments/ROOTING_TEST_RESULTS.md)** — ANDROID_ID 변경 성공

### 3단계: 대응 시스템 설계
6. **[PERSONA_SYSTEM_DESIGN.md](docs/02-identification/PERSONA_SYSTEM_DESIGN.md)** — 페르소나 시스템
7. **[ARCHITECTURE.md](docs/03-architecture/ARCHITECTURE.md)** — 시스템 아키텍처
8. **[TRAFFIC_BOOSTING_STRATEGY.md](docs/01-tracking-system/TRAFFIC_BOOSTING_STRATEGY.md)** — 트래픽 전략

### 4단계: 구현 상세 (필요시)
9. **[EXECUTION_FLOW.md](docs/03-architecture/EXECUTION_FLOW.md)** — 실행 흐름
10. **[NAVER_CHROME_USE.md](docs/04-implementation/NAVER_CHROME_USE.md)** — Chrome 자동화

### 5단계: 블로그 Direct API (발행 자동화)
11. **[NAVER_BLOG_API_ANALYSIS.md](docs/09-blog-direct-api/NAVER_BLOG_API_ANALYSIS.md)** — SE ONE 에디터 API 역분석
12. **[DIRECT_PUBLISHER_IMPLEMENTATION.md](docs/09-blog-direct-api/DIRECT_PUBLISHER_IMPLEMENTATION.md)** — DirectPublisher 구현

---

## 실험 이력

| 날짜 | 실험 | 핵심 결과 |
|------|------|-----------|
| 2025-12-13 | 핑거프린트 캡처 | NNB 비교 (N42LJ→I46ZM), 98K→166K 이벤트 |
| 2026-01-28 | 루팅 테스트 | ANDROID_ID 변경 성공 (Galaxy Tab S9+) |
| 2026-02-05 | 재방문 시뮬레이션 | NNB 100% 동일, 쿠키 10개 보존 확인 |
| 2026-02-06 | 리퍼러 테스트 | CDP Page.navigate referrer 작동 확인 |
| 2026-03-05 | 블로그 Direct API | SE ONE 에디터 API 역분석, httpx만으로 발행 성공 |

---

## 기술 스택

| 기술 | 용도 |
|------|------|
| Python 3.10+ | 코어 언어 |
| FastAPI | API 서버 |
| ADB | Android 디바이스 제어 |
| DroidRun Portal | Accessibility 기반 UI 탐지 |
| CDP (Chrome DevTools Protocol) | 브라우저 제어, 리퍼러 조작 |
| Supabase | 캠페인 데이터 저장 |
| DeepSeek API | AI 스토리라인 생성 |

---

## 프로젝트 기원

이 시스템은 **CareOn** (KT CCTV 파트너사)의 블로그 마케팅 자동화 프로젝트에서 출발했습니다:

```
블로그 콘텐츠 생성 → 검색 트래픽 유입 시뮬레이션 → 랜딩페이지 전환
```

네이버의 추적/식별 시스템을 이해하지 않으면 자동화가 불가능하기에, 체계적 분석이 선행되었습니다.

---

## 관련 리포지토리

| 리포 | 역할 |
|------|------|
| [ai-project](https://github.com/shinjadong/ai-project) | 원본 트래픽 엔진 프로젝트 |
| [kt-cctv-landing](https://github.com/shinjadong/kt-cctv-landing) | KT CCTV 랜딩페이지 |
| blog-writer (로컬) | 블로그 원고 생성 + Direct API 발행 |

---

*마지막 업데이트: 2026-03-05*
