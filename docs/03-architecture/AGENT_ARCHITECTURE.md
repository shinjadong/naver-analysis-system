# 에이전트 아키텍처 설계서

> **작성일**: 2025-12-13
> **기반**: DroidRun 에이전트 시스템
> **목적**: Naver AI Evolution 에이전트 계층 구조 및 동작 정의

---

## 1. 개요

### 1.1 에이전트 시스템 목표

1. **자율적 작업 수행**: 사용자 목표를 이해하고 단계별로 실행
2. **탐지 회피**: 네이버 추적 시스템 대응 행동 패턴 적용
3. **자가 진화**: 피트니스 평가 기반 전략 최적화
4. **에러 복구**: AI 기반 장애 감지 및 자동 복구

### 1.2 아키텍처 원칙

```
┌─────────────────────────────────────────────────────────────────┐
│                        설계 원칙                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 계층 분리 (Layered)                                         │
│     └── Orchestrator → Strategy → Behavior → Device            │
│                                                                 │
│  2. 상태 공유 (Shared State)                                    │
│     └── NaverAgentState를 통한 에이전트 간 상태 공유             │
│                                                                 │
│  3. 이벤트 기반 (Event-Driven)                                  │
│     └── 비동기 이벤트로 에이전트 간 통신                          │
│                                                                 │
│  4. 진화 연계 (Evolution-Aware)                                 │
│     └── 모든 행동이 피트니스 평가에 반영                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 에이전트 계층 구조

### 2.1 전체 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                    NaverEvolutionAgent                           │
│                    (메인 오케스트레이터)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Layer 1: Strategy                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │ StrategyAgent│  │ PlanAgent  │  │RecoveryAgent│     │   │
│  │  │ (계획 수립) │  │ (계획 분해) │  │ (복구 계획) │     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Layer 2: Behavior                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │BehaviorAgent│  │ DirectAgent │  │ StealthAgent│     │   │
│  │  │ (행동 실행) │  │ (직접 실행) │  │ (회피 모드) │     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Layer 3: Device                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │EnhancedAdb │  │NaverChrome │  │ CookieMgr  │     │   │
│  │  │ Tools      │  │UseProvider │  │            │     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Layer 4: Evolution                    │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │EvolutionEngine│  │FitnessEval│  │StrategyPool│     │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 에이전트 역할 정의

| 에이전트 | 계층 | 역할 | DroidRun 기반 |
|---------|------|------|-------------|
| **NaverEvolutionAgent** | Orchestrator | 전체 워크플로우 조정 | DroidAgent |
| **StrategyAgent** | Strategy | 목표 분석 및 계획 수립 | ManagerAgent |
| **PlanAgent** | Strategy | 계획을 실행 가능한 단계로 분해 | - |
| **RecoveryAgent** | Strategy | 에러 복구 계획 수립 | - |
| **BehaviorAgent** | Behavior | 행동 실행 (탐지 회피 적용) | ExecutorAgent |
| **DirectAgent** | Behavior | 단순 작업 직접 실행 | CodeActAgent |
| **StealthAgent** | Behavior | 고 회피 모드 행동 | - |

---

## 3. 공유 상태 (NaverAgentState)

### 3.1 상태 구조

```python
@dataclass
class NaverAgentState:
    """
    에이전트 간 공유 상태

    DroidAgentState 기반 + 네이버 특화 확장
    """

    # ========================================
    # 기본 상태 (DroidAgentState 호환)
    # ========================================

    instruction: str = ""           # 사용자 목표
    step_number: int = 0            # 현재 스텝
    max_steps: int = 50             # 최대 스텝

    # 계획 상태
    plan: str = ""                  # 전체 계획
    current_subgoal: str = ""       # 현재 서브골
    progress_status: str = ""       # 진행 상태

    # 액션 히스토리
    action_history: List[str] = field(default_factory=list)
    action_outcomes: List[bool] = field(default_factory=list)
    error_descriptions: List[str] = field(default_factory=list)
    summary_history: List[str] = field(default_factory=list)

    # 마지막 액션 정보
    last_action: str = ""
    last_summary: str = ""
    last_action_thought: str = ""
    action_pool: List[Dict] = field(default_factory=list)

    # 에러 플래그
    error_flag_plan: bool = False
    err_to_manager_thresh: int = 2

    # ========================================
    # 네이버 특화 상태
    # ========================================

    # 쿠키/세션 상태
    cookie_state: Dict[str, str] = field(default_factory=dict)
    session_id: str = ""
    last_srt5_update: float = 0.0
    last_srt30_update: float = 0.0

    # 추적 대응 상태
    tracking_threat_level: float = 0.0  # 0~1
    detected_tracking_events: List[str] = field(default_factory=list)
    stealth_mode_active: bool = False

    # 진화 엔진 연계
    current_strategy_id: str = ""
    strategy_parameters: Dict = field(default_factory=dict)
    fitness_metrics: Dict[str, float] = field(default_factory=dict)

    # NaverChromeUse 상태
    current_browser: str = ""           # com.android.chrome 등
    current_browser_card: str = ""      # 브라우저 카드 내용
    visited_urls: Set[str] = field(default_factory=set)
    visited_domains: Set[str] = field(default_factory=set)

    # UI 상태
    focused_text: str = ""
    clickable_elements: List[Dict] = field(default_factory=list)
    last_screenshot: bytes = None

    # ========================================
    # 메서드
    # ========================================

    def update_srt_if_needed(self) -> bool:
        """SRT 쿠키 갱신 필요 여부 확인 및 갱신"""
        now = time.time()

        # SRT5 (5분)
        if now - self.last_srt5_update > 300:
            self.last_srt5_update = now
            return True

        # SRT30 (30분)
        if now - self.last_srt30_update > 1800:
            self.last_srt30_update = now
            return True

        return False

    def record_action(self, action: str, success: bool, summary: str = ""):
        """액션 기록"""
        self.action_history.append(action)
        self.action_outcomes.append(success)
        self.summary_history.append(summary)
        self.last_action = action
        self.last_summary = summary

    def update_threat_level(self, events: List[str]):
        """추적 위협 수준 업데이트"""
        self.detected_tracking_events.extend(events)

        # 이벤트 수에 따른 위협 수준 계산
        recent_events = self.detected_tracking_events[-10:]
        self.tracking_threat_level = min(1.0, len(recent_events) * 0.1)

        # 자동 스텔스 모드 활성화
        if self.tracking_threat_level > 0.7:
            self.stealth_mode_active = True

    def get_fitness_snapshot(self) -> Dict[str, float]:
        """현재 피트니스 지표 스냅샷"""
        success_rate = (
            sum(self.action_outcomes) / len(self.action_outcomes)
            if self.action_outcomes else 0.0
        )

        return {
            "task_success_rate": success_rate,
            "detection_avoidance": 1.0 - self.tracking_threat_level,
            "step_efficiency": max(0, 1 - (self.step_number / self.max_steps)),
            **self.fitness_metrics
        }
```

### 3.2 상태 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                      상태 흐름 다이어그램                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  시작                                                           │
│    │                                                            │
│    ▼                                                            │
│  ┌─────────────┐                                               │
│  │ 상태 초기화 │                                               │
│  │ instruction │                                               │
│  │ strategy    │                                               │
│  │ cookie      │                                               │
│  └──────┬──────┘                                               │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    루프 시작                              │   │
│  │                                                          │   │
│  │   ┌───────────────┐                                     │   │
│  │   │ StrategyAgent │ ───────────────┐                    │   │
│  │   │ plan 업데이트  │               │                    │   │
│  │   │ subgoal 설정  │               │                    │   │
│  │   └───────┬───────┘               │                    │   │
│  │           │                        │                    │   │
│  │           ▼                        │ 에러 시            │   │
│  │   ┌───────────────┐               │                    │   │
│  │   │ BehaviorAgent │               │                    │   │
│  │   │ action 실행   │ ──────────────┤                    │   │
│  │   │ outcome 기록  │               │                    │   │
│  │   └───────┬───────┘               │                    │   │
│  │           │                        │                    │   │
│  │           ▼                        ▼                    │   │
│  │   ┌───────────────┐   ┌───────────────┐               │   │
│  │   │ 피트니스 평가 │   │ RecoveryAgent │               │   │
│  │   │ fitness 업데이트│   │ 복구 계획    │               │   │
│  │   └───────┬───────┘   └───────┬───────┘               │   │
│  │           │                    │                        │   │
│  │           └──────────┬─────────┘                        │   │
│  │                      │                                  │   │
│  │                      ▼                                  │   │
│  │              ┌───────────────┐                          │   │
│  │              │ step++ 확인  │                          │   │
│  │              │ 완료 여부    │                          │   │
│  │              └───────┬───────┘                          │   │
│  │                      │                                  │   │
│  │            ┌─────────┴─────────┐                        │   │
│  │            │                   │                        │   │
│  │       미완료             완료                           │   │
│  │            │                   │                        │   │
│  │            ▼                   ▼                        │   │
│  │       루프 계속           결과 반환                      │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 에이전트 상세 설계

### 4.1 NaverEvolutionAgent (오케스트레이터)

```python
class NaverEvolutionAgent:
    """
    메인 오케스트레이터 에이전트

    역할:
    - 전체 워크플로우 조정
    - 하위 에이전트 관리
    - 진화 엔진 연계
    """

    def __init__(
        self,
        goal: str,
        mode: AgentMode = AgentMode.REASONING,
        config: NaverAgentConfig = None,
        evolution_engine: EvolutionEngine = None,
        **kwargs
    ):
        # 설정
        self.mode = mode
        self.config = config or NaverAgentConfig()
        self.evolution = evolution_engine

        # 상태 초기화
        self.state = NaverAgentState(
            instruction=goal,
            max_steps=self.config.max_steps
        )

        # 하위 에이전트
        self.strategy_agent = StrategyAgent(
            llm=self.config.strategy_llm,
            shared_state=self.state
        )
        self.behavior_agent = BehaviorAgent(
            tools=EnhancedAdbTools(stealth_mode=True),
            shared_state=self.state
        )
        self.direct_agent = DirectAgent(
            llm=self.config.direct_llm,
            tools=EnhancedAdbTools(stealth_mode=False),
            shared_state=self.state
        )

        # 도구
        self.cookie_manager = CookieManager()
        self.chrome_use_provider = NaverChromeUseProvider()

    async def run(self) -> AgentResult:
        """메인 실행 루프"""

        # 1. 초기화
        await self._initialize()

        # 2. 진화 전략 로드
        if self.evolution:
            strategy = await self.evolution.get_best_strategy()
            self.state.current_strategy_id = strategy.id
            self.state.strategy_parameters = strategy.parameters

        # 3. 실행 모드에 따른 분기
        if self.mode == AgentMode.DIRECT:
            result = await self._run_direct()
        elif self.mode == AgentMode.STEALTH:
            result = await self._run_stealth()
        else:
            result = await self._run_reasoning()

        # 4. 피트니스 평가 및 진화 업데이트
        if self.evolution:
            fitness = self.state.get_fitness_snapshot()
            await self.evolution.update_fitness(
                self.state.current_strategy_id,
                fitness
            )

        return result

    async def _initialize(self):
        """초기화"""
        # 쿠키 프로파일 로드/생성
        cookie_profile = await self.cookie_manager.get_or_create_profile()
        self.state.cookie_state = cookie_profile

        # 세션 시작
        self.state.session_id = self._generate_session_id()
        self.state.last_srt5_update = time.time()
        self.state.last_srt30_update = time.time()

    async def _run_reasoning(self) -> AgentResult:
        """Manager + Executor 워크플로우"""

        while self.state.step_number < self.state.max_steps:
            # 1. SRT 쿠키 갱신 확인
            if self.state.update_srt_if_needed():
                await self.cookie_manager.refresh_srt()

            # 2. 전략 수립
            strategy_result = await self.strategy_agent.run()

            if strategy_result.get("complete"):
                return AgentResult(
                    success=True,
                    reason=strategy_result.get("answer", "")
                )

            # 3. 행동 실행
            behavior_result = await self.behavior_agent.run(
                subgoal=self.state.current_subgoal
            )

            # 4. 결과 기록
            self.state.record_action(
                action=behavior_result.get("action", ""),
                success=behavior_result.get("success", False),
                summary=behavior_result.get("summary", "")
            )

            # 5. 에러 처리
            if not behavior_result.get("success"):
                await self._handle_error(behavior_result)

            self.state.step_number += 1

        return AgentResult(
            success=False,
            reason=f"Max steps ({self.state.max_steps}) reached"
        )

    async def _run_direct(self) -> AgentResult:
        """직접 실행 모드"""
        return await self.direct_agent.run(
            instruction=self.state.instruction
        )

    async def _run_stealth(self) -> AgentResult:
        """고 회피 모드"""
        self.state.stealth_mode_active = True
        # 추가 지연 및 패턴 적용
        return await self._run_reasoning()

    async def _handle_error(self, error_result: Dict):
        """에러 처리"""
        error_count = sum(1 for o in self.state.action_outcomes[-3:] if not o)

        if error_count >= self.state.err_to_manager_thresh:
            self.state.error_flag_plan = True
            # RecoveryAgent 호출 가능
```

### 4.2 StrategyAgent (전략 계층)

```python
class StrategyAgent:
    """
    전략 수립 에이전트

    역할:
    - 목표 분석
    - 계획 수립
    - 서브골 생성
    - 추적 회피 전략 포함
    """

    SYSTEM_PROMPT = """
    당신은 네이버 서비스 자동화를 위한 전략 수립 에이전트입니다.

    역할:
    1. 사용자 목표를 분석하고 실행 가능한 계획을 수립합니다.
    2. 각 단계에서 네이버 추적 시스템을 고려한 회피 전략을 포함합니다.
    3. 에러 상황에서 복구 계획을 제시합니다.

    추적 회피 고려사항:
    - 검색은 URL 직접 열기 방식 사용
    - 스크롤은 가변 속도와 중간 멈춤 포함
    - 탭은 베지어 커브 궤적 사용
    - 세션 중간에 자연스러운 휴식 포함

    출력 형식:
    - plan: 전체 계획 (단계별)
    - current_subgoal: 다음 실행할 서브골
    - thought: 현재 상황 분석
    """

    def __init__(
        self,
        llm,
        shared_state: NaverAgentState,
        chrome_use_provider: NaverChromeUseProvider = None
    ):
        self.llm = llm
        self.state = shared_state
        self.chrome_use = chrome_use_provider

    async def run(self) -> Dict:
        """전략 수립 실행"""

        # 1. 컨텍스트 구성
        context = await self._build_context()

        # 2. LLM 호출
        response = await self.llm.complete(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=self._format_prompt(context)
        )

        # 3. 응답 파싱
        result = self._parse_response(response)

        # 4. 상태 업데이트
        self.state.plan = result.get("plan", "")
        self.state.current_subgoal = result.get("current_subgoal", "")

        return result

    async def _build_context(self) -> Dict:
        """컨텍스트 구성"""
        context = {
            "instruction": self.state.instruction,
            "current_step": self.state.step_number,
            "max_steps": self.state.max_steps,
            "action_history": self.state.action_history[-5:],
            "last_summary": self.state.last_summary,
            "error_flag": self.state.error_flag_plan,
            "threat_level": self.state.tracking_threat_level
        }

        # NaverChromeUse 카드 추가
        if self.chrome_use and self.state.current_package:
            browser_card = await self.chrome_use.load_browser_card(
                self.state.current_package
            )
            context["browser_card"] = browser_card

        return context
```

### 4.3 BehaviorAgent (행동 계층)

```python
class BehaviorAgent:
    """
    행동 실행 에이전트

    역할:
    - 서브골을 구체적인 액션으로 변환
    - 탐지 회피 행동 적용
    - 실행 결과 반환
    """

    def __init__(
        self,
        tools: EnhancedAdbTools,
        shared_state: NaverAgentState,
        llm = None
    ):
        self.tools = tools
        self.state = shared_state
        self.llm = llm
        self.behavior_injector = BehaviorInjector()

    async def run(self, subgoal: str) -> Dict:
        """행동 실행"""

        # 1. 현재 UI 상태 획득
        ui_state = await self.tools.get_state()
        self.state.clickable_elements = ui_state.get("elements", [])
        self.state.focused_text = ui_state.get("focused_text", "")

        # 2. 액션 결정 (LLM 또는 규칙 기반)
        if self.llm:
            action = await self._decide_action_llm(subgoal, ui_state)
        else:
            action = await self._decide_action_rule(subgoal, ui_state)

        # 3. 스텔스 모드 확인
        if self.state.stealth_mode_active:
            action = self._apply_stealth_modifiers(action)

        # 4. 액션 실행
        result = await self._execute_action(action)

        # 5. 추적 이벤트 확인
        tracking_events = self._detect_tracking_events(result)
        if tracking_events:
            self.state.update_threat_level(tracking_events)

        return result

    async def _execute_action(self, action: Dict) -> Dict:
        """액션 실행 (탐지 회피 적용)"""

        action_type = action.get("type")
        success = False
        summary = ""

        try:
            if action_type == "tap":
                # 베지어 커브 탭
                if action.get("index"):
                    result = await self.tools.tap_by_index(action["index"])
                else:
                    result = await self.tools.tap(action["x"], action["y"])
                success = True
                summary = result

            elif action_type == "swipe":
                # 가변 속도 스크롤
                result = await self.tools.swipe(
                    action["start_x"], action["start_y"],
                    action["end_x"], action["end_y"],
                    action.get("duration", 500)
                )
                success = result
                summary = f"Swiped from ({action['start_x']}, {action['start_y']})"

            elif action_type == "input":
                # 인간적인 타이핑
                result = await self.tools.input_text(
                    action["text"],
                    clear=action.get("clear", False)
                )
                success = True
                summary = result

            elif action_type == "back":
                result = await self.tools.back()
                success = True
                summary = result

            elif action_type == "wait":
                # 자연스러운 대기
                duration = action.get("duration", 1.0)
                jitter = random.uniform(-0.2, 0.3) * duration
                await asyncio.sleep(duration + jitter)
                success = True
                summary = f"Waited {duration + jitter:.1f}s"

            elif action_type == "shell":
                # ADB 쉘 명령
                result = await self.tools.shell(action["command"])
                success = True
                summary = result

        except Exception as e:
            success = False
            summary = str(e)

        return {
            "action": action_type,
            "success": success,
            "summary": summary
        }

    def _apply_stealth_modifiers(self, action: Dict) -> Dict:
        """스텔스 모드 수정자 적용"""

        # 추가 지연
        if "wait_after" not in action:
            action["wait_after"] = random.uniform(0.5, 1.5)
        else:
            action["wait_after"] *= 1.5

        # 스크롤 속도 감소
        if action.get("type") == "swipe":
            action["duration"] = action.get("duration", 500) * 1.3

        return action
```

---

## 5. 이벤트 시스템

### 5.1 이벤트 정의

```python
from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum

class EventType(Enum):
    """이벤트 유형"""
    # 전략 이벤트
    STRATEGY_START = "strategy_start"
    STRATEGY_PLAN = "strategy_plan"
    STRATEGY_COMPLETE = "strategy_complete"

    # 행동 이벤트
    ACTION_START = "action_start"
    ACTION_TAP = "action_tap"
    ACTION_SWIPE = "action_swipe"
    ACTION_INPUT = "action_input"
    ACTION_COMPLETE = "action_complete"
    ACTION_ERROR = "action_error"

    # 상태 이벤트
    UI_STATE_UPDATE = "ui_state_update"
    SCREENSHOT = "screenshot"
    COOKIE_UPDATE = "cookie_update"

    # 진화 이벤트
    FITNESS_UPDATE = "fitness_update"
    STRATEGY_SWITCH = "strategy_switch"

    # 추적 이벤트
    TRACKING_DETECTED = "tracking_detected"
    THREAT_LEVEL_CHANGE = "threat_level_change"
    STEALTH_MODE_TOGGLE = "stealth_mode_toggle"


@dataclass
class AgentEvent:
    """에이전트 이벤트"""
    event_type: EventType
    timestamp: float
    data: Any = None
    source: str = ""
    description: str = ""


@dataclass
class ActionEvent(AgentEvent):
    """액션 이벤트"""
    action_type: str = ""
    x: int = 0
    y: int = 0
    element_index: Optional[int] = None
    element_text: str = ""
    success: bool = False


@dataclass
class TrackingEvent(AgentEvent):
    """추적 감지 이벤트"""
    tracking_type: str = ""
    endpoint: str = ""
    threat_level: float = 0.0
```

### 5.2 이벤트 핸들러

```python
class EventBus:
    """이벤트 버스"""

    def __init__(self):
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._event_log: List[AgentEvent] = []

    def subscribe(self, event_type: EventType, handler: Callable):
        """이벤트 구독"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    async def publish(self, event: AgentEvent):
        """이벤트 발행"""
        self._event_log.append(event)

        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)

    def get_recent_events(self, count: int = 10) -> List[AgentEvent]:
        """최근 이벤트 조회"""
        return self._event_log[-count:]
```

---

## 6. 진화 엔진 연계

### 6.1 피트니스 평가 연계

```python
class EvolutionIntegration:
    """진화 엔진 연계 모듈"""

    def __init__(self, evolution_engine: EvolutionEngine):
        self.engine = evolution_engine

    async def evaluate_agent_run(
        self,
        state: NaverAgentState,
        result: AgentResult
    ) -> FitnessMetrics:
        """에이전트 실행 결과 평가"""

        # 기본 지표
        task_success = 1.0 if result.success else 0.0

        success_rate = (
            sum(state.action_outcomes) / len(state.action_outcomes)
            if state.action_outcomes else 0.0
        )

        # 탐지 회피 지표
        detection_avoidance = 1.0 - state.tracking_threat_level

        # 효율성 지표
        step_efficiency = max(0, 1 - (state.step_number / state.max_steps))

        # 행동 자연스러움 (에러율 기반)
        error_rate = 1 - success_rate
        behavior_naturalness = 1 - (error_rate * 0.5)

        # 세션 지표
        session_complexity = self._calculate_session_complexity(state)
        cookie_consistency = self._calculate_cookie_consistency(state)
        srt_pattern = self._calculate_srt_pattern(state)

        return FitnessMetrics(
            detection_avoidance=detection_avoidance * 0.15,
            task_success_rate=success_rate * 0.15,
            resource_efficiency=step_efficiency * 0.05,
            error_recovery_speed=0.8 * 0.10,  # 복구 속도 (별도 계산 필요)
            behavior_naturalness=behavior_naturalness * 0.10,
            session_complexity=session_complexity * 0.08,
            interaction_density=0.7 * 0.08,  # 상호작용 밀도 (별도 계산)
            scroll_depth_quality=0.8 * 0.07,  # 스크롤 품질 (별도 계산)
            cross_domain_flow=0.6 * 0.05,  # 크로스 도메인 (별도 계산)
            dwell_time_pattern=0.7 * 0.07,  # 체류 시간 (별도 계산)
            cookie_consistency=cookie_consistency * 0.05,
            srt_update_pattern=srt_pattern * 0.05
        )

    def _calculate_session_complexity(self, state: NaverAgentState) -> float:
        """세션 복잡도 계산"""
        # 다양한 액션 유형 사용
        action_types = set(a.split()[0] for a in state.action_history if a)
        return min(1.0, len(action_types) / 5)

    def _calculate_cookie_consistency(self, state: NaverAgentState) -> float:
        """쿠키 일관성 계산"""
        required_cookies = ['NNB', 'SRT5', 'SRT30']
        present = sum(1 for c in required_cookies if c in state.cookie_state)
        return present / len(required_cookies)

    def _calculate_srt_pattern(self, state: NaverAgentState) -> float:
        """SRT 갱신 패턴 점수"""
        now = time.time()

        # SRT5는 5분마다 갱신되어야 함
        srt5_age = now - state.last_srt5_update
        srt5_score = 1.0 if srt5_age < 300 else max(0, 1 - (srt5_age - 300) / 300)

        # SRT30은 30분마다
        srt30_age = now - state.last_srt30_update
        srt30_score = 1.0 if srt30_age < 1800 else max(0, 1 - (srt30_age - 1800) / 1800)

        return (srt5_score + srt30_score) / 2
```

---

## 7. 설정 및 구성

### 7.1 에이전트 설정

```yaml
# config/agent_config.yaml

agent:
  # 기본 설정
  max_steps: 50
  timeout_seconds: 300
  default_mode: "reasoning"  # reasoning | direct | stealth

  # LLM 설정
  llm_profiles:
    strategy:
      model: "deepseek-chat"
      temperature: 0.7
      max_tokens: 2000
    behavior:
      model: "deepseek-chat"
      temperature: 0.3
      max_tokens: 1000
    direct:
      model: "deepseek-chat"
      temperature: 0.5
      max_tokens: 1500

  # 스텔스 설정
  stealth:
    auto_activate_threat_level: 0.7
    extra_delay_multiplier: 1.5
    scroll_speed_reduction: 0.7

  # 에러 처리
  error_handling:
    max_consecutive_errors: 3
    auto_recovery: true
    recovery_strategies:
      - "retry"
      - "alternative_action"
      - "rollback"

  # 이벤트 로깅
  logging:
    save_events: true
    save_screenshots: true
    trajectory_path: "logs/trajectories"
```

### 7.2 파일 구조

```
naver-ai-evolution/src/shared/agent_core/
├── __init__.py
├── agents/
│   ├── __init__.py
│   ├── naver_evolution_agent.py    # 메인 오케스트레이터
│   ├── strategy_agent.py            # 전략 에이전트
│   ├── behavior_agent.py            # 행동 에이전트
│   ├── direct_agent.py              # 직접 실행 에이전트
│   └── recovery_agent.py            # 복구 에이전트
├── state/
│   ├── __init__.py
│   ├── agent_state.py               # NaverAgentState
│   └── state_manager.py             # 상태 관리자
├── events/
│   ├── __init__.py
│   ├── event_types.py               # 이벤트 정의
│   ├── event_bus.py                 # 이벤트 버스
│   └── handlers.py                  # 이벤트 핸들러
├── evolution/
│   ├── __init__.py
│   └── integration.py               # 진화 엔진 연계
└── config/
    ├── __init__.py
    └── agent_config.py              # 설정 로더
```

---

## 8. 참고 문서

- [DroidRun 통합 가이드](DROIDRUN_INTEGRATION.md)
- [NaverChromeUse 명세서](NAVER_CHROME_USE.md) - Chrome 기반 네이버 자동화
- [네이버 추적 시스템 분석](../analysis/naver_complete_analysis.md)
- [시스템 아키텍처](ARCHITECTURE.md)

---

*마지막 업데이트: 2025-12-14*
*핵심 원칙: Chrome 브라우저 기반 네이버 접속 (네이티브 앱 미사용)*
