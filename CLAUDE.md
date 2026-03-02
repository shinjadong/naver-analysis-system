# 네이버 분석 시스템 — Claude Code 컨텍스트

> AI 에이전트가 이 리포를 열었을 때 가장 먼저 읽는 문서

---

## 프로젝트 개요

네이버의 사용자 추적/식별 시스템을 역분석하고, 그 결과를 바탕으로 구축된 자동화 대응 시스템.

| 항목 | 내용 |
|------|------|
| 목적 | 네이버 추적 시스템 분석 + 트래픽 자동화 |
| 언어 | Python 3.10+ |
| 프레임워크 | FastAPI, ADB, DroidRun, CDP |
| 환경 | Termux (Android) / Ubuntu / Windows-WSL2 |
| 소유자 | shinjadong |

---

## 세션 시작 시 필수 읽기

**순서대로** 읽을 것. 이 순서가 최적의 컨텍스트 구축 경로임.

### 1단계: 핵심 분석 (반드시)

1. `docs/02-identification/NID_IDENTIFICATION.md` — 네이버 동일인 식별 원리 (4-Layer)
2. `docs/01-tracking-system/NAVER_TRACKING_ANALYSIS.md` — 5개 추적 시스템 전체 분석

### 2단계: 실험 근거 (권장)

3. `docs/05-experiments/FINGERPRINT_FINDINGS.md` — IP+쿠키삭제=신규사용자 확인
4. `docs/05-experiments/REVISIT_TEST_RESULT.md` — NNB 복원=재방문자 확인

### 3단계: 시스템 설계 (작업 시)

5. `docs/02-identification/PERSONA_SYSTEM_DESIGN.md` — 페르소나 시스템
6. `docs/03-architecture/ARCHITECTURE.md` — 시스템 아키텍처 v0.4.0
7. `docs/03-architecture/EXECUTION_FLOW.md` — 실행 흐름

### 전체 색인

모든 문서 목록: `INDEX.md`

---

## 핵심 지식 (즉시 참조용)

### 네이버 동일인 판별 우선순위

```
1. NID (로그인)  → 확정적 식별, 크로스디바이스
2. NNB (쿠키)   → 디바이스 식별, 비로그인 시 PRIMARY
3. iv (서버)    → 서버측 UUID, 세션 연결
4. Fingerprint  → 보조 수단 (단독 불충분)
```

### NNB 쿠키 (가장 중요한 식별자)

- 12자리 영숫자 (예: `N42LJ2QRSQ7GS`)
- 도메인: `.naver.com`, 만료: 2050년
- 쿠키 삭제 시 새 값 발급 → 신규 사용자
- 쿠키 유지(Chrome 데이터 복원) → 재방문자

### 블로그 조회수 +1 조건

```
unique NNB + new page_uid + 최소 체류시간
```

### 5개 추적 시스템

| 시스템 | 엔드포인트 | 역할 |
|--------|-----------|------|
| NLOG | `nlog.naver.com/n` | 세션 로깅 (Image pixel) |
| TIVAN SC2 | `tivan.naver.com/sc2/` | 행동 추적 (Beacon API) |
| TIVAN Perf | `tivan.naver.com/g/` | 성능 추적 (Web Vitals) |
| GFA | `g.tivan.naver.com/gfa/` | 광고 행동 (암호화 POST) |
| VETA | `siape.veta.naver.com` | 광고 입찰 (OpenRTB) |

### 분석 규모

74 추적 도메인 / 218 URL 파라미터 / 40 쿠키 / 50 이벤트 타입

---

## 디렉토리 구조

```
docs/
├── 01-tracking-system/    # 추적 시스템 분석 (NLOG, TIVAN, GFA, VETA)
├── 02-identification/     # 식별 체계 (NNB, NID, iv, fingerprint, 페르소나)
├── 03-architecture/       # 아키텍처 (Agent, DroidRun, AI workflow)
├── 04-implementation/     # 구현 상세 (Chrome, Session, API)
├── 05-experiments/        # 실험 결과 (핑거프린트, 재방문, 루팅)
├── 06-setup/             # 환경 설정 (디바이스, 프로젝트)
├── 07-roadmap/           # 로드맵 & 진화 스토리
└── 08-reference/         # 참조 자료 (개발 로그 등)

experiments/               # 실험 원본 데이터 (pcap, json, py)
src/                      # Python 소스 코드 (110파일)
  ├── api/                #   FastAPI 서버
  ├── campaign/           #   캠페인 관리 + 모듈화 프레임워크
  └── shared/             #   공유 모듈
      ├── device_tools/   #     BehaviorInjector, EnhancedAdbTools
      ├── naver_chrome_use/ #   Chrome 자동화 (CDP)
      ├── persona_manager/ #    페르소나 관리
      ├── session_manager/ #    세션 관리 (IP 회전)
      ├── portal_client/  #     DroidRun Portal UI 탐지
      └── smart_executor/ #     OBSERVE→ACT→VERIFY
tests/                    # 테스트 코드
scripts/                  # 실행/테스트 스크립트
config/                   # YAML 설정 파일
data/keyword/             # 키워드 CSV 데이터
```

---

## 주요 소스 모듈

| 모듈 | 경로 | 역할 |
|------|------|------|
| BehaviorInjector | `src/shared/device_tools/behavior_injector.py` | 베지어 커브 탭, 가변속도 스크롤, 자연 타이핑 |
| EnhancedAdbTools | `src/shared/device_tools/adb_enhanced.py` | 탐지회피 ADB 래퍼 |
| PersonaManager | `src/shared/persona_manager/manager.py` | ANDROID_ID 변경, Chrome 데이터 관리 |
| CdpClient | `src/shared/naver_chrome_use/cdp_client.py` | CDP referrer 네비게이션 |
| DeviceSessionManager | `src/shared/session_manager/device_session_manager.py` | IP 회전, 쿠키 삭제 |
| PortalClient | `src/shared/portal_client/client.py` | DroidRun accessibility tree |
| PipelineEngine | `src/campaign/refactor/core/pipeline_engine.py` | YAML 기반 모듈화 파이프라인 |
| FastAPI | `src/api/main.py` | API 서버 (인증, CORS, 라우터) |

---

## 검증된 실험 결과

| 실험 | 날짜 | 결과 |
|------|------|------|
| 핑거프린트 캡처 | 2025-12-13 | IP+쿠키삭제 → 새 NNB → 신규사용자 |
| 루팅 테스트 | 2026-01-28 | ANDROID_ID 변경 성공 (Galaxy Tab S9+) |
| 재방문 시뮬레이션 | 2026-02-05 | NNB 100% 동일, 쿠키 10개 보존, 재방문 인식 |
| 리퍼러 테스트 | 2026-02-06 | CDP Page.navigate referrer 작동 확인 |

---

## 기술 스택

| 기술 | 용도 |
|------|------|
| Python 3.10+ | 코어 |
| FastAPI | API 서버 |
| ADB | Android 디바이스 제어 |
| DroidRun Portal | Accessibility 기반 UI 탐지 |
| CDP | Chrome DevTools Protocol (리퍼러, 쿠키) |
| Supabase | 캠페인 데이터 저장 |
| DeepSeek API | AI 스토리라인 생성 |

---

## 관련 리포지토리

| 리포 | 역할 |
|------|------|
| [ai-project](https://github.com/shinjadong/ai-project) | 원본 트래픽 엔진 |
| [kt-cctv-landing](https://github.com/shinjadong/kt-cctv-landing) | KT CCTV 랜딩페이지 |

---

## 코딩 컨벤션

- PEP 8 준수, type hints 사용
- `pathlib` > `os.path`
- `dataclass` 선호
- Early return 패턴
- 파일 300줄 이하 유지
- 시크릿은 `.env` (git-ignored)

---

## 주의사항

- `.env` 파일은 포함하지 않음 — Supabase/DeepSeek 키는 별도 관리
- `data/personas.db`는 `.gitignore` — 실제 페르소나 데이터 보호
- 소스 코드는 **참조용** — 실 실행은 원본 `ai-project` 리포에서

---

*마지막 업데이트: 2026-03-02*
