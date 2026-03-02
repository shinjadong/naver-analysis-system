# 확장 가이드 (Extending Guide)

> 새 기능을 추가할 때 어디를 수정해야 하는지 안내합니다.

---

## 목차

1. [새 CLI 명령어 추가](#1-새-cli-명령어-추가)
2. [새 액션 타입 추가](#2-새-액션-타입-추가-탭스크롤-등)
3. [새 검색 타입 추가](#3-새-검색-타입-추가-blognewscafe-등)
4. [새 페르소나 전략 추가](#4-새-페르소나-전략-추가)
5. [휴먼라이크 동작 튜닝](#5-휴먼라이크-동작-튜닝)
6. [새 테스트 추가](#6-새-테스트-추가)

---

## 1. 새 CLI 명령어 추가

### 1.1 기존 그룹에 명령어 추가

**예: `naver run manual` 명령어 추가**

```python
# src/shared/cli/__init__.py

@run_app.command("manual")
def run_manual(
    action: str = typer.Argument(..., help="실행할 액션 (tap/scroll/type)"),
    x: int = typer.Option(None, "--x", help="X 좌표"),
    y: int = typer.Option(None, "--y", help="Y 좌표"),
):
    """수동 액션 실행"""
    from .commands.run import execute_manual
    execute_manual(action=action, x=x, y=y)
```

```python
# src/shared/cli/commands/run.py

def execute_manual(action: str, x: int = None, y: int = None):
    """수동 액션 실행 구현"""
    console.print(f"액션: {action}, 좌표: ({x}, {y})")
    # 구현...
```

### 1.2 새 명령어 그룹 추가

**예: `naver campaign` 그룹 추가**

```python
# src/shared/cli/__init__.py

# 1. 그룹 생성
campaign_app = typer.Typer(help="캠페인 관리")
app.add_typer(campaign_app, name="campaign")

# 2. 명령어 추가
@campaign_app.command("list")
def campaign_list():
    """캠페인 목록"""
    from .commands.campaign import list_campaigns
    list_campaigns()

@campaign_app.command("create")
def campaign_create(name: str):
    """캠페인 생성"""
    from .commands.campaign import create_campaign
    create_campaign(name=name)
```

```python
# src/shared/cli/commands/campaign.py (새 파일)

from rich.console import Console
console = Console()

def list_campaigns():
    console.print("캠페인 목록...")

def create_campaign(name: str):
    console.print(f"캠페인 생성: {name}")
```

---

## 2. 새 액션 타입 추가 (탭/스크롤 등)

### 수정할 파일

| 파일 | 역할 |
|------|------|
| `src/shared/device_tools/behavior_injector.py` | 휴먼라이크 동작 생성 |
| `src/shared/device_tools/adb_enhanced.py` | ADB 명령 실행 |
| `src/shared/smart_executor/executor.py` | 액션 디스패치 |

### 예: `long_press` 액션 추가

**Step 1: BehaviorInjector에 메서드 추가**

```python
# src/shared/device_tools/behavior_injector.py

@dataclass
class LongPressResult:
    x: int
    y: int
    duration_ms: int
    offset_x: int
    offset_y: int

class BehaviorInjector:
    def generate_human_long_press(
        self,
        x: int,
        y: int,
        duration_ms: int = 800
    ) -> LongPressResult:
        """롱프레스용 휴먼라이크 파라미터 생성"""
        offset_x = random.randint(-5, 5)
        offset_y = random.randint(-5, 5)
        duration_variance = random.randint(-100, 100)

        return LongPressResult(
            x=x + offset_x,
            y=y + offset_y,
            duration_ms=duration_ms + duration_variance,
            offset_x=offset_x,
            offset_y=offset_y,
        )
```

**Step 2: EnhancedAdbTools에 메서드 추가**

```python
# src/shared/device_tools/adb_enhanced.py

async def long_press(self, x: int, y: int, duration_ms: int = 800) -> ActionResult:
    """롱프레스 실행 (휴먼라이크)"""
    result = self.behavior.generate_human_long_press(x, y, duration_ms)

    cmd = f"input swipe {result.x} {result.y} {result.x} {result.y} {result.duration_ms}"
    await self._shell(cmd)

    return ActionResult(
        success=True,
        action_type="long_press",
        details={
            "x": result.x,
            "y": result.y,
            "duration_ms": result.duration_ms,
        }
    )
```

**Step 3: SmartExecutor에 디스패치 추가**

```python
# src/shared/smart_executor/executor.py

async def long_press_by_text(self, text: str, duration_ms: int = 800) -> ActionResult:
    """텍스트로 요소 찾아서 롱프레스"""
    await self.refresh_ui()
    elements = self._last_ui.find_all(text_contains=text)

    if not elements:
        return ActionResult(success=False, message=f"요소 없음: {text}")

    element = elements[0]
    x, y = element.center
    return await self.adb_tools.long_press(x, y, duration_ms)
```

---

## 3. 새 검색 타입 추가 (blog/news/cafe 등)

### 수정할 파일

| 파일 | 역할 |
|------|------|
| `src/shared/naver_chrome_use/url_builder.py` | URL 생성 |
| `src/shared/pipeline/__init__.py` | 검색 타입 처리 |

### 예: `shopping` 검색 타입 추가

```python
# src/shared/naver_chrome_use/url_builder.py

class NaverUrlBuilder:
    SEARCH_TYPES = {
        "blog": "blog",
        "news": "news",
        "cafe": "cafearticle",
        "shopping": "shop",  # 추가
    }

    def build_search_url(self, keyword: str, search_type: str = "blog") -> str:
        tab = self.SEARCH_TYPES.get(search_type, "blog")
        encoded = quote(keyword)
        return f"https://m.search.naver.com/search.naver?where={tab}&query={encoded}"
```

```python
# src/shared/pipeline/__init__.py

# run_session 메서드에서 search_type 파라미터 처리
async def run_session(
    self,
    keywords: List[str] = None,
    search_type: str = "blog",  # "shopping" 추가 가능
    ...
):
```

---

## 4. 새 페르소나 전략 추가

### 수정할 파일

| 파일 | 역할 |
|------|------|
| `src/shared/persona_manager/manager.py` | 전략 구현 |

### 예: `random_weighted` 전략 추가

```python
# src/shared/persona_manager/manager.py

class PersonaManager:
    STRATEGIES = {
        "least_recent": "_select_least_recent",
        "round_robin": "_select_round_robin",
        "random_weighted": "_select_random_weighted",  # 추가
    }

    def _select_random_weighted(self) -> Persona:
        """세션 수가 적은 페르소나에 가중치를 두고 랜덤 선택"""
        personas = self.get_all_personas()
        if not personas:
            return None

        # 세션 수의 역수를 가중치로
        weights = [1 / (p.total_sessions + 1) for p in personas]
        total = sum(weights)
        weights = [w / total for w in weights]

        import random
        return random.choices(personas, weights=weights, k=1)[0]
```

---

## 5. 휴먼라이크 동작 튜닝

### 설정 파일

```python
# src/shared/device_tools/behavior_injector.py

@dataclass
class BehaviorConfig:
    # 탭 오프셋
    tap_offset_min: int = -10
    tap_offset_max: int = 10
    tap_duration_min: int = 50
    tap_duration_max: int = 150

    # 스크롤
    scroll_segment_count_min: int = 3
    scroll_segment_count_max: int = 6
    scroll_pause_probability: float = 0.3

    # 타이핑
    typing_delay_min: int = 50
    typing_delay_max: int = 200
    typo_probability: float = 0.05
```

### 튜닝 방법

```python
from device_tools.behavior_injector import BehaviorInjector, BehaviorConfig

# 커스텀 설정
config = BehaviorConfig(
    tap_offset_min=-5,
    tap_offset_max=5,
    scroll_pause_probability=0.5,  # 멈춤 확률 증가
)

injector = BehaviorInjector(config)
```

---

## 6. 새 테스트 추가

### 테스트 구조

```
tests/
├── unit/           # 단위 테스트 (모킹, 빠름)
├── integration/    # 통합 테스트 (모듈 간 연동)
├── e2e/            # E2E 테스트 (실제 디바이스)
└── smoke/          # 스모크 테스트 (빠른 검증)
```

### 예: 새 단위 테스트 추가

```python
# tests/unit/test_url_builder.py

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "shared"))

from naver_chrome_use.url_builder import NaverUrlBuilder


class TestNaverUrlBuilder:
    def test_blog_search_url(self):
        builder = NaverUrlBuilder()
        url = builder.build_search_url("맛집", "blog")
        assert "where=blog" in url
        assert "query=" in url

    def test_shopping_search_url(self):
        builder = NaverUrlBuilder()
        url = builder.build_search_url("노트북", "shopping")
        assert "where=shop" in url
```

### 테스트 실행

```bash
# 단위 테스트만
naver test unit

# 특정 모듈만
naver test unit --module url_builder

# 스모크 테스트 (변경 후 빠른 검증)
naver test smoke

# E2E (디바이스 연결 필요)
naver test e2e
```

---

## 체크리스트

새 기능 추가 시 확인사항:

- [ ] 관련 모듈에 구현 추가
- [ ] CLI 명령어 추가 (필요시)
- [ ] 단위 테스트 작성
- [ ] 스모크 테스트에 import 확인 추가
- [ ] EXECUTION_FLOW.md 업데이트 (흐름 변경시)
- [ ] 커밋 메시지에 변경 내용 명시

---

## 관련 문서

- [QUICKSTART.md](QUICKSTART.md) - 빠른 시작
- [EXECUTION_FLOW.md](EXECUTION_FLOW.md) - 실행 흐름
- [ARCHITECTURE.md](ARCHITECTURE.md) - 시스템 아키텍처
- [API_REFERENCE.md](API_REFERENCE.md) - API 레퍼런스

---

*최종 업데이트: 2026-01-08*
