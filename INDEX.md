# 전체 문서 색인 (Document Index)

> 모든 문서의 위치, 분류, 핵심 내용을 한눈에 파악

---

## 01 — 추적 시스템 (Tracking System)

| 문서 | 파일 | 핵심 내용 |
|------|------|-----------|
| **네이버 추적 분석** | [docs/01-tracking-system/NAVER_TRACKING_ANALYSIS.md](docs/01-tracking-system/NAVER_TRACKING_ANALYSIS.md) | 5개 추적 시스템 전체 분석, 74 도메인, 218 파라미터, 40 쿠키, 50 이벤트, C-Rank/DIA 알고리즘 |
| **트래픽 부스팅 전략** | [docs/01-tracking-system/TRAFFIC_BOOSTING_STRATEGY.md](docs/01-tracking-system/TRAFFIC_BOOSTING_STRATEGY.md) | 검색 클릭 시그널, 세션 카운팅, CDP 리퍼러 조작, 단계별 실행 전략 |

## 02 — 사용자 식별 (Identification)

| 문서 | 파일 | 핵심 내용 |
|------|------|-----------|
| **NID 식별 체계 종합** | [docs/02-identification/NID_IDENTIFICATION.md](docs/02-identification/NID_IDENTIFICATION.md) | 4-Layer 식별 체계, NNB/NID/iv/핑거프린트, 동일인 판별 로직, 블로그 조회수 조건 |
| **페르소나 시스템 설계** | [docs/02-identification/PERSONA_SYSTEM_DESIGN.md](docs/02-identification/PERSONA_SYSTEM_DESIGN.md) | 가상 사용자 관리, ANDROID_ID/NNB/Chrome 데이터 관리, 세션 플로우 |
| **핑거프린트 실험 프로토콜** | [docs/02-identification/FINGERPRINT_EXPERIMENT_PROTOCOL.md](docs/02-identification/FINGERPRINT_EXPERIMENT_PROTOCOL.md) | 3개 시나리오 실험 설계 (기준선/IP+쿠키삭제/쿠키만삭제) |

## 03 — 시스템 아키텍처 (Architecture)

| 문서 | 파일 | 핵심 내용 |
|------|------|-----------|
| **시스템 아키텍처** | [docs/03-architecture/ARCHITECTURE.md](docs/03-architecture/ARCHITECTURE.md) | v0.4.0, Windows-WSL2 하이브리드, 4-Layer 쿠키 관리, 12개 적합도 지표 |
| **에이전트 아키텍처** | [docs/03-architecture/AGENT_ARCHITECTURE.md](docs/03-architecture/AGENT_ARCHITECTURE.md) | 4-Layer 에이전트 (Strategy→Behavior→Device→Evolution), EventBus |
| **실행 흐름** | [docs/03-architecture/EXECUTION_FLOW.md](docs/03-architecture/EXECUTION_FLOW.md) | CLI→ADB 전체 실행 흐름, Pipeline/SmartExecutor/BehaviorInjector |
| **DroidRun 통합** | [docs/03-architecture/DROIDRUN_INTEGRATION.md](docs/03-architecture/DROIDRUN_INTEGRATION.md) | DroidRun Portal 통합, BehaviorInjector(베지어), EnhancedAdbTools |
| **AI 워크플로우** | [docs/03-architecture/AI_WORKFLOW_IMPLEMENTATION.md](docs/03-architecture/AI_WORKFLOW_IMPLEMENTATION.md) | AI-driven UI 탐지, bounds 파싱, wait_for_elements |
| **온디바이스 아키텍처** | [docs/03-architecture/CLAUDE_ON_DEVICE_ARCHITECTURE.md](docs/03-architecture/CLAUDE_ON_DEVICE_ARCHITECTURE.md) | Termux에서의 Claude Code 운영 아키텍처 |

## 04 — 구현 상세 (Implementation)

| 문서 | 파일 | 핵심 내용 |
|------|------|-----------|
| **Chrome 자동화** | [docs/04-implementation/NAVER_CHROME_USE.md](docs/04-implementation/NAVER_CHROME_USE.md) | ADB Intent, UI 좌표(1080x2400), BehaviorInjector 설정, 워크플로우 |
| **세션 매니저** | [docs/04-implementation/SESSION_MANAGER_IMPLEMENTATION.md](docs/04-implementation/SESSION_MANAGER_IMPLEMENTATION.md) | DeviceSessionManager, EngagementSimulator, Galaxy Z Fold5 테스트 |
| **API 레퍼런스** | [docs/04-implementation/API_REFERENCE.md](docs/04-implementation/API_REFERENCE.md) | FastAPI 엔드포인트 목록 및 스펙 |
| **개발 가이드** | [docs/04-implementation/DEVELOPMENT.md](docs/04-implementation/DEVELOPMENT.md) | 개발 환경 설정, 코드 구조, 디버깅 |
| **확장 가이드** | [docs/04-implementation/EXTENDING.md](docs/04-implementation/EXTENDING.md) | 새 모듈/액션 추가 방법 |
| **사용 가이드** | [docs/04-implementation/USAGE_GUIDE.md](docs/04-implementation/USAGE_GUIDE.md) | CLI 사용법, API 호출 방법 |
| **빠른 시작** | [docs/04-implementation/QUICKSTART.md](docs/04-implementation/QUICKSTART.md) | 5분 안에 시작하기 |

## 05 — 실험 결과 (Experiments)

| 문서 | 파일 | 핵심 결과 |
|------|------|-----------|
| **핑거프린트 실험 결과** | [docs/05-experiments/FINGERPRINT_FINDINGS.md](docs/05-experiments/FINGERPRINT_FINDINGS.md) | IP+쿠키삭제 → 새 NNB → 신규사용자. 98K→166K 이벤트 |
| **재방문 테스트 결과** | [docs/05-experiments/REVISIT_TEST_RESULT.md](docs/05-experiments/REVISIT_TEST_RESULT.md) | NNB 100% 동일, 쿠키 10개 보존, 재방문자 인식 확인 |
| **재방문 테스트 방법** | [docs/05-experiments/REVISIT_TEST_INSTRUCTIONS.md](docs/05-experiments/REVISIT_TEST_INSTRUCTIONS.md) | Python 스크립트, ADB 쿠키 쿼리 방법 |
| **루팅 테스트 결과** | [docs/05-experiments/ROOTING_TEST_RESULTS.md](docs/05-experiments/ROOTING_TEST_RESULTS.md) | ANDROID_ID 변경 성공, Chrome DB 스키마 분석 |
| **전체 테스트 결과** | [docs/05-experiments/TEST_RESULTS.md](docs/05-experiments/TEST_RESULTS.md) | 32/32 통과 (BehaviorInjector, ChromeUse, AdbTools, 실기기) |
| **파이프라인 테스트** | [docs/05-experiments/PIPELINE_TEST_REPORT.md](docs/05-experiments/PIPELINE_TEST_REPORT.md) | NaverSessionPipeline 통합 테스트 보고서 |

## 06 — 환경 설정 (Setup)

| 문서 | 파일 | 핵심 내용 |
|------|------|-----------|
| **디바이스 설정** | [docs/06-setup/DEVICE_SETUP.md](docs/06-setup/DEVICE_SETUP.md) | Android 디바이스 설정, ADB 연결, 루팅 |
| **프로젝트 설정** | [docs/06-setup/PROJECT_SETUP.md](docs/06-setup/PROJECT_SETUP.md) | Python 환경, 의존성, .env 설정 |

## 07 — 로드맵 (Roadmap)

| 문서 | 파일 | 핵심 내용 |
|------|------|-----------|
| **개선 로드맵** | [docs/07-roadmap/IMPROVEMENT_ROADMAP.md](docs/07-roadmap/IMPROVEMENT_ROADMAP.md) | 갭 분석, 3-Phase 로드맵, 탐지위험 40%→95% 감소 |
| **프로젝트 진화 스토리** | [docs/07-roadmap/PROJECT_EVOLUTION_STORY.md](docs/07-roadmap/PROJECT_EVOLUTION_STORY.md) | 고정좌표→AI→DroidRun 진화 과정 |

## 08 — 참조 (Reference)

| 문서 | 파일 | 핵심 내용 |
|------|------|-----------|
| **Compass 아티팩트** | [docs/08-reference/compass_artifact_*.md](docs/08-reference/) | 네이버 트래픽 엔진 Compass 설계 |
| **개발 세션 로그** | [docs/08-reference/claude-code(local-samsung-laptop).md](docs/08-reference/) | Samsung 노트북 개발 세션 전체 기록 |

---

## 실험 원본 데이터

| 파일 | 경로 | 설명 |
|------|------|------|
| 캡처 결과 | [experiments/network_capture/capture_result.json](experiments/network_capture/capture_result.json) | 네트워크 캡처 결과 JSON |
| 패킷 캡처 | [experiments/network_capture/naver_capture.pcap](experiments/network_capture/naver_capture.pcap) | 원본 패킷 캡처 |
| 리퍼러 테스트 | [experiments/referrer_test/test_referrer.py](experiments/referrer_test/test_referrer.py) | CDP 리퍼러 테스트 Python 스크립트 |
| 핑거프린트 분석 | [experiments/fingerprint_capture/FINDINGS.md](experiments/fingerprint_capture/FINDINGS.md) | DeepSeek V3.2 분석 결과 |
| 루팅 테스트 | [experiments/rooting_tests/ROOTING_TEST_RESULTS.md](experiments/rooting_tests/ROOTING_TEST_RESULTS.md) | ANDROID_ID 변경 실험 |

---

## 소스 코드 주요 모듈

| 모듈 | 경로 | 역할 |
|------|------|------|
| BehaviorInjector | `src/shared/device_tools/behavior_injector.py` | 휴먼라이크 행동 (베지어 커브, 가변속도 스크롤) |
| EnhancedAdbTools | `src/shared/device_tools/adb_enhanced.py` | 탐지회피 ADB 래퍼 |
| NaverChromeUseProvider | `src/shared/naver_chrome_use/provider.py` | Chrome 자동화 (URL/Intent/CDP) |
| CdpClient | `src/shared/naver_chrome_use/cdp_client.py` | CDP 리퍼러 네비게이션 |
| NaverUrlBuilder | `src/shared/naver_chrome_use/url_builder.py` | 네이버 URL 빌더 |
| PersonaManager | `src/shared/persona_manager/manager.py` | 페르소나 관리 (ANDROID_ID 변경, Chrome 데이터) |
| PersonaStore | `src/shared/persona_manager/persona_store.py` | SQLite 페르소나 저장소 |
| DeviceIdentityManager | `src/shared/persona_manager/device_identity.py` | 디바이스 ID 관리 (루팅) |
| ChromeDataManager | `src/shared/persona_manager/chrome_data.py` | Chrome 데이터 백업/복원 |
| DeviceSessionManager | `src/shared/session_manager/device_session_manager.py` | IP 회전, 쿠키 삭제 |
| EngagementSimulator | `src/shared/session_manager/engagement_simulator.py` | 체류시간/스크롤 시뮬레이션 |
| PortalClient | `src/shared/portal_client/client.py` | DroidRun Portal UI 탐지 |
| SmartExecutor | `src/shared/smart_executor/executor.py` | OBSERVE→ACT→VERIFY 실행기 |
| StorylineGenerator | `src/shared/storyline_generator/storyline_generator.py` | DeepSeek AI 스토리라인 |
| AISessionController | `src/shared/ai_session_controller.py` | AI 세션 제어 (Portal+CDP) |
| AICampaignWorkflow | `src/shared/ai_campaign_workflow.py` | AI 캠페인 워크플로우 |
| PipelineEngine | `src/campaign/refactor/core/pipeline_engine.py` | 모듈화 파이프라인 |
| CampaignRunner | `src/campaign/refactor/campaigns/campaign_runner.py` | YAML 캠페인 실행 |
| FastAPI Main | `src/api/main.py` | API 서버 엔트리포인트 |
| TrafficExecutor | `src/api/services/traffic_executor.py` | 트래픽 실행 서비스 |

---

*총 문서: 30개 | 소스 파일: 110개 | 실험 데이터: 5개*
