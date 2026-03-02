# 03 — 시스템 아키텍처

추적 분석 결과를 바탕으로 설계된 자동화 시스템의 아키텍처.

## 문서 목록

| 문서 | 설명 |
|------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 시스템 아키텍처 v0.4.0 — Windows-WSL2 하이브리드, 4-Layer 쿠키 관리, 12개 적합도 지표 |
| [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) | 4-Layer 에이전트 계층 (Strategy→Behavior→Device→Evolution), EventBus |
| [EXECUTION_FLOW.md](EXECUTION_FLOW.md) | CLI→ADB 전체 실행 흐름, Pipeline/SmartExecutor/BehaviorInjector 상세 |
| [DROIDRUN_INTEGRATION.md](DROIDRUN_INTEGRATION.md) | DroidRun 프레임워크 통합, BehaviorInjector(베지어 커브), EnhancedAdbTools |
| [AI_WORKFLOW_IMPLEMENTATION.md](AI_WORKFLOW_IMPLEMENTATION.md) | AI-driven 동적 UI 탐지, Portal 기반 accessibility tree 분석 |
| [CLAUDE_ON_DEVICE_ARCHITECTURE.md](CLAUDE_ON_DEVICE_ARCHITECTURE.md) | Termux 환경 Claude Code 운영 아키텍처 |

## 아키텍처 레이어

```
Strategy Agent (전략 결정)
  └── Behavior Agent (행동 패턴)
       └── Device Agent (디바이스 제어)
            └── Evolution Agent (학습/적응)
```
