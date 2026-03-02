# 사용 가이드 (Usage Guide)

## ADB 제어 (EnhancedAdbTools)

이 프로젝트는 `input tap`이나 `input swipe` 같은 Raw ADB 명령 대신, **EnhancedAdbTools**를 통해 모든 디바이스 상호작용을 수행합니다. 이를 통해 베지어 커브, 가변 속도 스크롤, 인간적인 타이핑 등 "휴먼라이크" 동작이 자동으로 적용됩니다.

> **Note**: `stealth_mode` 옵션은 삭제되었습니다. 모든 동작은 기본적으로 휴먼라이크로 수행됩니다.

### 기본 사용법

```python
from src.shared.device_tools import EnhancedAdbTools, AdbConfig, create_tools

# 1. 팩토리 함수 사용 (권장)
# 연결된 디바이스의 시리얼 넘버로 도구 생성
tools = create_tools(serial="R3CW60BHSAT")

# 2. 직접 생성
# 화면 해상도를 명시하여 생성
config = AdbConfig(serial="R3CW60BHSAT", screen_width=1080, screen_height=2340)
tools = EnhancedAdbTools(config)
```

### 주요 동작

#### 탭 (Tap)
베지어 곡선 알고리즘을 사용하여 목표 지점 주변으로 자연스럽게 터치합니다.

```python
# 좌표 (540, 1200) 터치
await tools.tap(540, 1200)
```

#### 스크롤 (Scroll)
가속-유지-감속의 물리적인 움직임을 시뮬레이션하며, 중간에 잠깐 멈춰서 읽는 듯한 동작을 섞습니다.

```python
# 아래로 600픽셀 스크롤
await tools.scroll_down(distance=600)

# 위로 스크롤
await tools.scroll_up(distance=600)
```

#### 텍스트 입력 (Text Input)
타이핑 속도를 불규칙하게 조절하고, 가끔 오타를 냈다가 지우고 다시 쓰는 시뮬레이션을 포함합니다.

```python
# 검색어 입력
await tools.input_text("맛집 추천")
```

### 파라미터 튜닝 (BehaviorConfig)

기본 동작 특성을 변경하려면 `BehaviorConfig`를 수정합니다.

```python
from src.shared.device_tools import BehaviorConfig

# 설정 변경
tools.behavior_profile = BehaviorConfig(
    typing_speed_mean=0.1,  # 타이핑 평균 속도 (초)
    mistake_rate=0.05,      # 오타 발생 확률 (5%)
    scroll_smoothness=0.8   # 스크롤 부드러움 정도
)
```
