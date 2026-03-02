# DroidRun 레퍼런스 프로젝트 통합 가이드

> **작성일**: 2025-12-13
> **레퍼런스 소스**: `reference-projects/droidrun/` (automation-shinjadong-androidrun)
> **목적**: Naver AI Evolution 시스템에 DroidRun 컴포넌트 적용

---

## 1. 개요

DroidRun은 LLM 기반 Android AI 에이전트 프레임워크입니다. Naver AI Evolution 시스템에 다음 요소들을 통합하여 탐지 회피 및 자동화 품질을 향상시킵니다.

### 1.1 통합 대상 컴포넌트

| 컴포넌트 | 소스 경로 | 적용 대상 | 우선순위 |
|---------|----------|----------|---------|
| **에이전트 시스템** | `droidrun/agent/` | 진화 에이전트 | 🔴 높음 |
| **앱 카드 시스템** | `droidrun/app_cards/` | 네이버 앱 카드 | 🔴 높음 |
| **ADB 도구** | `droidrun/tools/adb.py` | DeviceManager | 🔴 높음 |
| **매크로 시스템** | `droidrun/macro/` | 워크플로우 녹화 | 🟡 중간 |
| **텔레메트리** | `droidrun/telemetry/` | 모니터링 | 🟢 낮음 |

### 1.2 통합 원칙

1. **복사가 아닌 적응**: 원본 코드를 그대로 복사하지 않고, Naver 특화 요구사항에 맞게 수정
2. **탐지 회피 강화**: 모든 UI 인터랙션에 베지어 커브, 가변 타이밍 적용
3. **네이버 쿠키 시스템 연동**: 앱 카드와 쿠키 매니저 통합
4. **진화 엔진 연계**: 에이전트 행동을 피트니스 평가에 반영

---

## 2. 에이전트 시스템 통합

### 2.1 DroidRun 에이전트 아키텍처 분석

```
droidrun/agent/
├── droid/
│   ├── droid_agent.py      # 메인 래퍼 (Manager + Executor 조정)
│   ├── state.py            # DroidAgentState (공유 상태)
│   └── events.py           # 이벤트 정의
├── manager/
│   ├── manager_agent.py    # 계획 수립 에이전트
│   └── prompts.py          # 프롬프트 템플릿
├── executor/
│   ├── executor_agent.py   # 액션 실행 에이전트
│   └── prompts.py          # 프롬프트 템플릿
├── codeact/
│   └── codeact_agent.py    # 직접 실행 모드 (reasoning=False)
├── scripter/
│   └── scripter_agent.py   # 오프-디바이스 작업 에이전트
└── oneflows/
    ├── app_starter_workflow.py  # 앱 실행 워크플로우
    └── text_manipulator.py      # 텍스트 조작 워크플로우
```

### 2.2 Naver AI Evolution 에이전트 매핑

| DroidRun 에이전트 | Naver 에이전트 | 역할 | 수정 사항 |
|-----------------|---------------|------|----------|
| `DroidAgent` | `NaverEvolutionAgent` | 전체 오케스트레이션 | 진화 엔진 연동 추가 |
| `ManagerAgent` | `StrategyAgent` | 전략 수립 | 네이버 추적 회피 전략 포함 |
| `ExecutorAgent` | `BehaviorAgent` | 행동 실행 | 베지어 커브/가변 타이밍 적용 |
| `CodeActAgent` | `DirectAgent` | 단순 작업 | 그대로 활용 |
| `ScripterAgent` | `AIQueryAgent` | AI 쿼리 처리 | DeepSeek API 연동 |

### 2.3 NaverEvolutionAgent 설계

```python
# src/shared/agent_core/naver_evolution_agent.py

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class AgentMode(Enum):
    """에이전트 실행 모드"""
    REASONING = "reasoning"      # Manager + Executor 워크플로우
    DIRECT = "direct"            # 직접 실행 (CodeAct)
    STEALTH = "stealth"          # 고 회피 모드 (추가 지연/패턴)

@dataclass
class NaverAgentState:
    """네이버 에이전트 공유 상태"""

    # 기본 상태 (DroidAgentState 기반)
    instruction: str                          # 사용자 목표
    step_number: int = 0                      # 현재 스텝
    max_steps: int = 50                       # 최대 스텝

    # 계획 상태
    plan: str = ""                            # 현재 계획
    current_subgoal: str = ""                 # 현재 서브골

    # 액션 히스토리
    action_history: List[str] = None         # 액션 기록
    action_outcomes: List[bool] = None       # 성공/실패
    error_descriptions: List[str] = None     # 에러 설명

    # 네이버 특화 상태
    cookie_state: Dict = None                 # 현재 쿠키 상태
    session_id: str = ""                      # 세션 ID
    tracking_threat_level: float = 0.0        # 추적 위협 수준 (0~1)
    last_srt_update: float = 0.0              # 마지막 SRT 갱신 시간

    # 진화 엔진 연계
    current_strategy_id: str = ""             # 현재 전략 ID
    fitness_metrics: Dict = None              # 실시간 피트니스 지표

    def __post_init__(self):
        if self.action_history is None:
            self.action_history = []
        if self.action_outcomes is None:
            self.action_outcomes = []
        if self.error_descriptions is None:
            self.error_descriptions = []
        if self.cookie_state is None:
            self.cookie_state = {}
        if self.fitness_metrics is None:
            self.fitness_metrics = {}


class NaverEvolutionAgent:
    """
    Naver AI Evolution 메인 에이전트

    DroidAgent를 기반으로 다음 기능 추가:
    - 네이버 추적 시스템 대응
    - 진화 엔진 연계
    - 쿠키/세션 관리
    """

    def __init__(
        self,
        goal: str,
        mode: AgentMode = AgentMode.REASONING,
        strategy_id: str = None,
        cookie_profile: Dict = None,
        evolution_engine = None,
        **kwargs
    ):
        self.goal = goal
        self.mode = mode
        self.strategy_id = strategy_id
        self.evolution_engine = evolution_engine

        # 상태 초기화
        self.state = NaverAgentState(
            instruction=goal,
            current_strategy_id=strategy_id or "",
            cookie_state=cookie_profile or {}
        )

        # 하위 에이전트 초기화
        self.strategy_agent = None    # ManagerAgent 기반
        self.behavior_agent = None    # ExecutorAgent 기반
        self.direct_agent = None      # CodeActAgent 기반

    async def run(self) -> Dict:
        """메인 실행 루프"""

        # 1. 쿠키 상태 검증 및 갱신
        await self._ensure_cookie_consistency()

        # 2. 모드에 따른 실행
        if self.mode == AgentMode.DIRECT:
            result = await self._run_direct()
        else:
            result = await self._run_reasoning()

        # 3. 피트니스 평가 및 진화 엔진 업데이트
        if self.evolution_engine:
            await self._update_fitness(result)

        return result

    async def _ensure_cookie_consistency(self):
        """쿠키 일관성 확인 및 갱신"""
        # SRT 갱신 확인
        # NNB 일치 확인
        # 세션 유효성 확인
        pass

    async def _run_reasoning(self) -> Dict:
        """Manager + Executor 워크플로우"""
        pass

    async def _run_direct(self) -> Dict:
        """직접 실행 모드"""
        pass

    async def _update_fitness(self, result: Dict):
        """피트니스 지표 업데이트"""
        pass
```

### 2.4 에이전트 워크플로우

```
┌─────────────────────────────────────────────────────────────────────┐
│                    NaverEvolutionAgent 워크플로우                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. 초기화                                                          │
│  ┌─────────────┐                                                   │
│  │ 쿠키 로드   │ ← CookieManager.load_profile()                    │
│  │ 전략 로드   │ ← EvolutionEngine.get_strategy()                  │
│  │ 세션 시작   │ ← SessionSimulator.start_session()                │
│  └──────┬──────┘                                                   │
│         │                                                          │
│  2. 계획 수립 (reasoning=True)                                     │
│  ┌──────▼──────┐                                                   │
│  │ StrategyAgent│                                                  │
│  │ (Manager)   │ → 서브골 목록 생성                                │
│  │             │ → 추적 회피 전략 포함                              │
│  └──────┬──────┘                                                   │
│         │                                                          │
│  3. 액션 실행                                                       │
│  ┌──────▼──────┐                                                   │
│  │ BehaviorAgent│                                                  │
│  │ (Executor)  │ → 베지어 커브 터치                                │
│  │             │ → 가변 속도 스크롤                                │
│  │             │ → 자연스러운 타이핑                                │
│  └──────┬──────┘                                                   │
│         │                                                          │
│  4. 결과 평가                                                       │
│  ┌──────▼──────┐                                                   │
│  │ 피트니스    │ → 12개 지표 평가                                  │
│  │ 평가       │ → 진화 엔진 업데이트                               │
│  └──────┬──────┘                                                   │
│         │                                                          │
│  5. 반복 (step_number < max_steps && !complete)                   │
│         │                                                          │
└─────────┴───────────────────────────────────────────────────────────┘
```

---

## 3. 앱 카드 시스템 통합

### 3.1 DroidRun 앱 카드 구조 분석

```
droidrun/app_cards/
├── __init__.py
├── app_card_provider.py     # 추상 기본 클래스
└── providers/
    ├── local_provider.py    # 로컬 파일 기반
    ├── server_provider.py   # 원격 서버 기반
    └── composite_provider.py # 복합 (로컬 우선, 서버 폴백)

droidrun/config/app_cards/
├── app_cards.json           # 패키지 → 카드 매핑
├── chrome.md                # Chrome 앱 카드
├── samsung_internet.md      # 삼성 인터넷 앱 카드
└── gmail.md                 # Gmail 앱 카드
```

### 3.2 앱 카드 인터페이스

```python
# 기존 DroidRun 인터페이스
class AppCardProvider(ABC):
    @abstractmethod
    async def load_app_card(self, package_name: str, instruction: str = "") -> str:
        """패키지별 앱 카드 로드"""
        pass
```

### 3.3 NaverChromeUse 카드 목록

**핵심 원칙**: 네이티브 네이버 앱을 사용하지 않고, Chrome 브라우저를 통해 네이버에 접속

| 카드 파일 | 패키지 | 용도 | 상태 |
|----------|--------|------|------|
| `chrome_naver.md` | `com.android.chrome` | Chrome에서 네이버 (기본) | 완료 |
| `samsung_naver.md` | `com.sec.android.app.sbrowser` | 삼성 인터넷에서 네이버 | 완료 |
| `edge_naver.md` | `com.microsoft.emmx` | Edge에서 네이버 (대안) | 계획 |

> **참고**: 네이티브 네이버 앱(com.nhn.android.search 등)은 탐지가 더 엄격하므로 사용하지 않음.
> 자세한 내용은 [NaverChromeUse 명세서](NAVER_CHROME_USE.md) 참조

### 3.4 앱 카드 템플릿

```markdown
# [앱명] 앱 카드

## Package Info
- **Package Name**: `[패키지명]`
- **Main Activity**: `[액티비티명]`

## 실행 명령어 (ADB Intent)

### 기본 실행
\`\`\`bash
am start -n [패키지명]/[액티비티명]
\`\`\`

### URL 직접 열기
\`\`\`bash
am start -a android.intent.action.VIEW -d '[URL]' [패키지명]
\`\`\`

### 검색 URL
\`\`\`bash
am start -a android.intent.action.VIEW -d 'https://search.naver.com/search.naver?query=[검색어]' [패키지명]
\`\`\`

## UI 상호작용

### 스크롤
- 아래로: `swipe(450, 1500, 450, 800, 500)`
- 위로: `swipe(450, 800, 450, 1500, 500)`

### 주요 요소 좌표 (해상도별)
| 요소 | 1080x2400 | 1440x3200 |
|------|-----------|-----------|
| 검색창 | (540, 180) | (720, 240) |
| 첫 번째 결과 | (540, 700) | (720, 933) |

## 네이버 특화 설정

### 쿠키 요구사항
- `NNB`: 필수 (디바이스 식별)
- `NID`: 로그인 시 필수
- `SRT5`: 세션 유지

### 추적 회피 설정
- 검색창 입력 대신 URL 직접 열기 권장
- 스크롤 시 가변 속도 적용
- 탭 시 베지어 커브 적용

## 워크플로우 예시

### 블로그 검색 → 글 읽기 → URL 복사
\`\`\`python
# 1. 블로그 검색 결과 바로 열기
start_app("[패키지명]", "android.intent.action.VIEW -d 'https://search.naver.com/search.naver?where=blog&query=[검색어]'")

# 2. 첫 번째 결과 클릭
tap(index=5)  # 또는 좌표

# 3. 천천히 스크롤
for i in range(5):
    swipe(450, 1500, 450, 1000, 600)
    wait(1.5)

# 4. 공유 → URL 복사
tap(공유버튼_index)
tap(URL복사_index)
\`\`\`
```

---

## 4. ADB 도구 통합

### 4.1 DroidRun AdbTools 분석

**핵심 메서드** (`droidrun/tools/adb.py`):

| 메서드 | 기능 | 탐지 회피 수준 |
|--------|------|--------------|
| `tap_by_index(index)` | 인덱스 기반 탭 | 🔴 낮음 (정확한 좌표) |
| `swipe(start, end, duration)` | 스와이프 | 🟡 중간 (고정 속도) |
| `input_text(text, clear)` | 텍스트 입력 | 🔴 낮음 (일괄 입력) |
| `get_state()` | UI 트리 파싱 | N/A |
| `take_screenshot()` | 스크린샷 | N/A |
| `back()` | 뒤로가기 | 🟢 높음 |
| `press_key(keycode)` | 키 입력 | 🟢 높음 |

### 4.2 탐지 회피 강화 버전

```python
# src/shared/device_tools/adb_enhanced.py

import asyncio
import random
import math
from typing import List, Tuple
from dataclasses import dataclass

@dataclass
class TouchPoint:
    """터치 포인트"""
    x: float
    y: float
    pressure: float = 1.0
    timestamp: float = 0.0

class BehaviorInjector:
    """인간 행동 시뮬레이션 주입기"""

    # 타이핑 파라미터
    TYPING_DELAY_MIN = 50      # ms
    TYPING_DELAY_MAX = 500     # ms
    TYPING_ERROR_RATE = 0.08   # 8% 오타율

    # 터치 파라미터
    TAP_OFFSET_MAX = 15        # px
    TAP_DURATION_MIN = 50      # ms
    TAP_DURATION_MAX = 150     # ms

    # 스크롤 파라미터
    SCROLL_ACCELERATION = 0.3  # 가속 비율
    SCROLL_DECELERATION = 0.2  # 감속 비율
    SCROLL_PAUSE_PROB = 0.15   # 중간 멈춤 확률

    def generate_bezier_curve(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        control_points: int = 2
    ) -> List[TouchPoint]:
        """
        베지어 커브 기반 터치 궤적 생성

        Args:
            start: 시작점 (x, y)
            end: 끝점 (x, y)
            control_points: 제어점 개수

        Returns:
            터치 포인트 리스트
        """
        points = []

        # 제어점 생성 (시작-끝 사이의 랜덤 위치)
        controls = []
        for i in range(control_points):
            t = (i + 1) / (control_points + 1)
            base_x = start[0] + (end[0] - start[0]) * t
            base_y = start[1] + (end[1] - start[1]) * t

            # 랜덤 오프셋 추가
            offset_x = random.gauss(0, 20)
            offset_y = random.gauss(0, 20)

            controls.append((base_x + offset_x, base_y + offset_y))

        # 베지어 곡선 샘플링
        all_points = [start] + controls + [end]
        n = len(all_points) - 1

        num_samples = random.randint(10, 20)
        for i in range(num_samples + 1):
            t = i / num_samples

            # De Casteljau 알고리즘
            temp_points = all_points.copy()
            for r in range(1, n + 1):
                for j in range(n - r + 1):
                    temp_points[j] = (
                        (1 - t) * temp_points[j][0] + t * temp_points[j + 1][0],
                        (1 - t) * temp_points[j][1] + t * temp_points[j + 1][1]
                    )

            # 압력 시뮬레이션 (시작/끝에서 약함)
            pressure = 0.5 + 0.5 * math.sin(math.pi * t)

            points.append(TouchPoint(
                x=temp_points[0][0],
                y=temp_points[0][1],
                pressure=pressure,
                timestamp=t
            ))

        return points

    def generate_human_tap(
        self,
        x: int,
        y: int
    ) -> Tuple[int, int, int]:
        """
        인간적인 탭 생성 (오프셋 + 지속시간)

        Returns:
            (x, y, duration_ms)
        """
        # 위치 오프셋 (가우시안 분포)
        offset_x = int(random.gauss(0, self.TAP_OFFSET_MAX / 2))
        offset_y = int(random.gauss(0, self.TAP_OFFSET_MAX / 2))

        # 지속시간
        duration = random.randint(self.TAP_DURATION_MIN, self.TAP_DURATION_MAX)

        return (x + offset_x, y + offset_y, duration)

    def generate_variable_scroll(
        self,
        start_y: int,
        end_y: int,
        screen_width: int = 1080
    ) -> List[Tuple[int, int, int, int, int]]:
        """
        가변 속도 스크롤 생성

        Returns:
            [(start_x, start_y, end_x, end_y, duration_ms), ...]
        """
        segments = []
        distance = abs(end_y - start_y)
        direction = 1 if end_y > start_y else -1

        # 세그먼트 분할
        num_segments = random.randint(2, 4)
        current_y = start_y

        for i in range(num_segments):
            # 세그먼트 거리
            if i == 0:
                # 가속 구간
                seg_distance = int(distance * self.SCROLL_ACCELERATION)
                duration = random.randint(100, 200)
            elif i == num_segments - 1:
                # 감속 구간
                seg_distance = abs(end_y - current_y)
                duration = random.randint(200, 400)
            else:
                # 중간 구간
                remaining = abs(end_y - current_y)
                seg_distance = random.randint(int(remaining * 0.3), int(remaining * 0.6))
                duration = random.randint(150, 300)

            next_y = current_y + (seg_distance * direction)

            # X 좌표 약간의 변화
            start_x = screen_width // 2 + random.randint(-30, 30)
            end_x = screen_width // 2 + random.randint(-30, 30)

            segments.append((start_x, current_y, end_x, next_y, duration))
            current_y = next_y

            # 중간 멈춤
            if i < num_segments - 1 and random.random() < self.SCROLL_PAUSE_PROB:
                segments.append(None)  # None = 멈춤 신호

        return segments

    def generate_human_typing(self, text: str) -> List[Tuple[str, int]]:
        """
        인간적인 타이핑 시퀀스 생성

        Returns:
            [(char, delay_ms), ...]
        """
        sequence = []

        for i, char in enumerate(text):
            # 기본 지연
            delay = random.randint(self.TYPING_DELAY_MIN, self.TYPING_DELAY_MAX)

            # 단어 시작시 약간 더 긴 지연
            if i > 0 and text[i-1] == ' ':
                delay += random.randint(50, 150)

            # 오타 시뮬레이션
            if random.random() < self.TYPING_ERROR_RATE:
                # 잘못된 문자 입력
                wrong_char = chr(ord(char) + random.choice([-1, 1]))
                if wrong_char.isalnum():
                    sequence.append((wrong_char, delay))
                    # 잠시 후 백스페이스
                    sequence.append(('\b', random.randint(100, 300)))
                    # 올바른 문자
                    sequence.append((char, random.randint(50, 150)))
                else:
                    sequence.append((char, delay))
            else:
                sequence.append((char, delay))

        return sequence


class EnhancedAdbTools:
    """
    탐지 회피 강화된 ADB 도구

    DroidRun AdbTools 기반 + BehaviorInjector 통합
    """

    def __init__(self, serial: str = None, stealth_mode: bool = True):
        self.serial = serial
        self.stealth_mode = stealth_mode
        self.behavior = BehaviorInjector() if stealth_mode else None
        self.device = None

    async def tap(self, x: int, y: int) -> str:
        """탐지 회피 탭"""
        if self.stealth_mode:
            # 인간적인 탭 생성
            adj_x, adj_y, duration = self.behavior.generate_human_tap(x, y)

            # 베지어 커브로 이동 (현재 위치 → 탭 위치)
            # 실제 구현에서는 이전 터치 위치 사용

            # 탭 실행 (지속시간 포함)
            await self._execute_tap(adj_x, adj_y, duration)

            return f"Tapped at ({adj_x}, {adj_y}) with {duration}ms duration"
        else:
            await self._execute_tap(x, y, 100)
            return f"Tapped at ({x}, {y})"

    async def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int = 400
    ) -> bool:
        """탐지 회피 스와이프"""
        if self.stealth_mode:
            # 가변 속도 스크롤 생성
            segments = self.behavior.generate_variable_scroll(start_y, end_y, start_x)

            for seg in segments:
                if seg is None:
                    # 중간 멈춤
                    await asyncio.sleep(random.uniform(0.3, 0.8))
                else:
                    sx, sy, ex, ey, dur = seg
                    await self._execute_swipe(sx, sy, ex, ey, dur)
                    await asyncio.sleep(dur / 1000 * 0.5)

            return True
        else:
            await self._execute_swipe(start_x, start_y, end_x, end_y, duration_ms)
            return True

    async def input_text(self, text: str, clear: bool = False) -> str:
        """탐지 회피 텍스트 입력"""
        if self.stealth_mode:
            # 인간적인 타이핑 시퀀스 생성
            sequence = self.behavior.generate_human_typing(text)

            for char, delay in sequence:
                if char == '\b':
                    await self._execute_key('KEYCODE_DEL')
                else:
                    await self._execute_char(char)
                await asyncio.sleep(delay / 1000)

            return f"Typed '{text}' with human-like delays"
        else:
            await self._execute_text(text)
            return f"Typed '{text}'"

    # 저수준 ADB 명령 실행 (구현 필요)
    async def _execute_tap(self, x: int, y: int, duration: int):
        pass

    async def _execute_swipe(self, sx: int, sy: int, ex: int, ey: int, duration: int):
        pass

    async def _execute_key(self, keycode: str):
        pass

    async def _execute_char(self, char: str):
        pass

    async def _execute_text(self, text: str):
        pass
```

### 4.3 통합 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    Device Tools 통합 아키텍처                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   EnhancedAdbTools                       │   │
│  │  (droidrun/tools/adb.py + BehaviorInjector)             │   │
│  └───────────────────────┬─────────────────────────────────┘   │
│                          │                                      │
│            ┌─────────────┼─────────────┐                       │
│            │             │             │                        │
│  ┌─────────▼───┐ ┌───────▼─────┐ ┌─────▼─────────┐            │
│  │ BehaviorInjector│ │ AdbTools  │ │ PortalClient │            │
│  │             │ │   (원본)   │ │  (UI 트리)   │            │
│  │ • 베지어커브 │ │ • 기본 탭  │ │ • get_state  │            │
│  │ • 가변스크롤 │ │ • 기본스와이프│ │ • 스크린샷  │            │
│  │ • 인간타이핑 │ │ • 기본입력  │ │              │            │
│  └─────────────┘ └─────────────┘ └──────────────┘            │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    DeviceManager                         │   │
│  │  (기존 src/shared/device_manager + EnhancedAdbTools)    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. 네이버 워크플로우 예제 활용

### 5.1 기존 DroidRun 워크플로우

**파일**: `reference-projects/droidrun/examples/workflows/naver_blog_search_workflow.py`

| 단계 | 설명 | 현재 구현 | 개선 필요 |
|-----|------|----------|----------|
| 1 | 브라우저 실행 | `am start` | 그대로 |
| 2 | 네이버 이동 | Intent URL | 그대로 |
| 3 | 검색 | 검색창 탭 + 입력 | URL 직접 열기로 변경 |
| 4 | 블로그 탭 | 탭 탭 | 스와이프 + 탭 |
| 5 | 블로거 찾기 | 고정 스크롤 | 가변 스크롤 |
| 6 | 천천히 스크롤 | 고정 속도 | 가변 속도 + 멈춤 |
| 7 | 공유/URL 복사 | 좌표 탭 | 인덱스 탭 |
| 8 | 종료 | `am force-stop` | 그대로 |

### 5.2 개선된 네이버 워크플로우 템플릿

```python
# src/shared/workflows/naver_blog_workflow.py

class NaverBlogWorkflow:
    """
    개선된 네이버 블로그 검색 워크플로우

    탐지 회피 적용:
    - URL 직접 열기 (검색창 입력 대신)
    - 가변 속도 스크롤
    - 베지어 커브 탭
    - 자연스러운 타이밍
    """

    def __init__(
        self,
        search_keyword: str,
        target_blogger: str = None,
        stealth_mode: bool = True
    ):
        self.keyword = search_keyword
        self.target = target_blogger
        self.stealth = stealth_mode
        self.tools = EnhancedAdbTools(stealth_mode=stealth_mode)

    async def run(self) -> Dict:
        """워크플로우 실행"""

        # 1. 브라우저 실행 + 네이버 블로그 검색 바로 열기
        search_url = f"https://search.naver.com/search.naver?where=blog&query={self.keyword}"
        await self._open_url(search_url)
        await self._random_wait(2, 4)

        # 2. 블로그 글 선택
        target_index = await self._find_blog_post(self.target)
        await self.tools.tap_by_index(target_index)
        await self._random_wait(2, 3)

        # 3. 콘텐츠 읽기 (가변 스크롤)
        await self._read_content()

        # 4. URL 복사
        copied_url = await self._share_and_copy()

        return {
            "success": True,
            "url": copied_url,
            "keyword": self.keyword
        }

    async def _open_url(self, url: str):
        """URL 직접 열기"""
        cmd = f"am start -a android.intent.action.VIEW -d '{url}' com.android.chrome"
        await self.tools.shell(cmd)

    async def _random_wait(self, min_sec: float, max_sec: float):
        """랜덤 대기"""
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    async def _find_blog_post(self, target: str = None) -> int:
        """블로그 글 찾기"""
        state = await self.tools.get_state()
        # UI 트리에서 블로그 글 찾기 로직
        # target이 있으면 해당 블로거 찾기
        # 없으면 첫 번째 결과
        return 5  # 예시 인덱스

    async def _read_content(self):
        """콘텐츠 읽기 (가변 스크롤)"""
        scroll_count = random.randint(4, 7)

        for i in range(scroll_count):
            # 가변 속도 스크롤
            distance = random.randint(300, 600)
            await self.tools.swipe(450, 1500, 450, 1500 - distance)

            # 읽는 시간 (체류)
            await self._random_wait(1.0, 3.0)

            # 가끔 위로 살짝 스크롤 (다시 보기)
            if random.random() < 0.2:
                await self.tools.swipe(450, 1000, 450, 1200)
                await self._random_wait(0.5, 1.5)

    async def _share_and_copy(self) -> str:
        """공유 및 URL 복사"""
        # 공유 버튼 찾기
        state = await self.tools.get_state()
        share_index = self._find_share_button(state)

        await self.tools.tap_by_index(share_index)
        await self._random_wait(0.5, 1.0)

        # URL 복사 버튼
        state = await self.tools.get_state()
        copy_index = self._find_copy_button(state)

        await self.tools.tap_by_index(copy_index)

        return "URL copied"  # 실제로는 클립보드에서 가져오기
```

---

## 6. 파일 구조 계획

### 6.1 신규 파일

```
naver-ai-evolution/src/shared/
├── agent_core/                          # 에이전트 시스템
│   ├── __init__.py
│   ├── naver_evolution_agent.py         # 메인 에이전트
│   ├── strategy_agent.py                # 전략 에이전트 (Manager)
│   ├── behavior_agent.py                # 행동 에이전트 (Executor)
│   ├── direct_agent.py                  # 직접 실행 에이전트 (CodeAct)
│   ├── state.py                         # 공유 상태
│   └── events.py                        # 이벤트 정의
│
├── naver_chrome_use/                    # NaverChromeUse 시스템
│   ├── __init__.py
│   ├── provider.py                      # NaverChromeUseProvider
│   ├── url_builder.py                   # NaverUrlBuilder
│   └── cards/                           # 브라우저 카드 파일
│       ├── browser_cards.json           # 브라우저 매핑
│       ├── chrome_naver.md              # Chrome + 네이버
│       └── samsung_naver.md             # Samsung Internet + 네이버
│
├── device_tools/                        # 디바이스 도구
│   ├── __init__.py
│   ├── adb_enhanced.py                  # 강화된 ADB 도구
│   ├── behavior_injector.py             # 행동 주입기
│   └── portal_client.py                 # UI 트리 클라이언트
│
└── workflows/                           # 워크플로우
    ├── __init__.py
    ├── naver_blog_workflow.py           # 블로그 워크플로우
    ├── naver_search_workflow.py         # 검색 워크플로우
    └── naver_shopping_workflow.py       # 쇼핑 워크플로우
```

### 6.2 수정 파일

| 파일 | 변경 내용 |
|-----|----------|
| `src/shared/device_manager/__init__.py` | EnhancedAdbTools 통합 |
| `src/shared/evolution_engine/__init__.py` | 에이전트 피트니스 연계 |
| `config/naver_profiles.yaml` | 앱 카드 경로, 에이전트 설정 추가 |
| `docs/ARCHITECTURE.md` | 에이전트 아키텍처 추가 |

---

## 7. 구현 우선순위

### Phase 1: 핵심 - device_tools 모듈 (완료)

1. **BehaviorInjector** - 베지어 커브, 가변 타이밍, 인간적인 타이핑 ✅
2. **EnhancedAdbTools** - 탐지 회피 탭/스크롤/입력 + BehaviorInjector 연동 ✅
3. **단위 테스트** - 28개 테스트 통과 ✅

### Phase 2: NaverChromeUse 시스템 (진행중)

4. **NaverChromeUseProvider** - 브라우저 선택 및 카드 제공
5. **NaverUrlBuilder** - 네이버 URL 생성 헬퍼
6. **chrome_naver.md 카드** - Chrome + 네이버 명세
7. **samsung_naver.md 카드** - Samsung Internet + 네이버 명세

### Phase 3: 에이전트 시스템

8. **NaverEvolutionAgent** - 메인 오케스트레이터
9. **StrategyAgent** - 전략 수립 (ManagerAgent 기반)
10. **BehaviorAgent** - 행동 실행 (ExecutorAgent 기반)
11. **NaverAgentState** - 공유 상태

### Phase 4: 워크플로우 및 진화 엔진 연계

12. **NaverBlogWorkflow** - 블로그 검색/읽기 워크플로우
13. **NaverShoppingWorkflow** - 쇼핑 검색/탐색 워크플로우
14. **진화 엔진 연계** - 피트니스 평가 연동

---

## 8. 참고 자료

### 8.1 DroidRun 레퍼런스 파일

| 파일 | 경로 | 용도 |
|-----|------|------|
| DroidAgent | `reference-projects/droidrun/droidrun/agent/droid/droid_agent.py` | 에이전트 구조 참고 |
| AdbTools | `reference-projects/droidrun/droidrun/tools/adb.py` | ADB 도구 참고 |
| AppCardProvider | `reference-projects/droidrun/droidrun/app_cards/app_card_provider.py` | 앱 카드 인터페이스 |
| chrome.md | `reference-projects/droidrun/droidrun/config/app_cards/chrome.md` | 네이버 앱 카드 템플릿 |
| NaverWorkflow | `reference-projects/droidrun/examples/workflows/naver_blog_search_workflow.py` | 워크플로우 예제 |

### 8.2 관련 문서

- [NaverChromeUse 명세서](NAVER_CHROME_USE.md) - Chrome 기반 네이버 자동화
- [에이전트 아키텍처](AGENT_ARCHITECTURE.md) - 4계층 에이전트 설계
- [네이버 추적 시스템 분석](../analysis/naver_complete_analysis.md)
- [시스템 아키텍처](ARCHITECTURE.md)

---

*마지막 업데이트: 2025-12-14*
*명명 규칙: NaverChromeUse (네이티브 네이버 앱 미사용)*
