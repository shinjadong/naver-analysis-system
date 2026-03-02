# API Reference

## EnhancedAdbTools

`src.shared.device_tools.adb_enhanced.EnhancedAdbTools`

모든 ADB/디바이스 상호작용을 담당하는 핵심 클래스입니다. 내부적으로 `BehaviorInjector`를 사용하여 모든 입력을 사람처럼 변환합니다.

### 초기화

```python
def __init__(self, config: AdbConfig): ...
```

- **config**: `AdbConfig` 객체 (serial, host, port, screen_size 등 포함)

### 메서드

#### `async tap(x: int, y: int)`
화면의 (x, y) 좌표를 탭합니다.
- 정확한 (x, y)를 찍지 않고, `BehaviorInjector`를 통해 약간의 오차와 베지어 접근 경로를 생성합니다.

#### `async scroll_down(distance: int = 500)`
지정된 거리만큼 아래로 스크롤합니다.
- 가속-감속 물리 모델이 적용됩니다.

#### `async scroll_up(distance: int = 500)`
지정된 거리만큼 위로 스크롤합니다.

#### `async input_text(text: str)`
텍스트를 입력합니다.
- `adb shell input text`를 바로 호출하지 않고, 글자 단위로 쪼개어 가변 딜레이를 줍니다.
- 오타 및 백스페이스 수정 동작이 무작위로 포함될 수 있습니다.

#### `async swipe(start_x, start_y, end_x, end_y, duration)`
두 지점 사이를 스와이프합니다. 직선이 아닌 곡선 경로를 사용합니다.

---

## Helper Functions

### `create_tools(serial: str) -> EnhancedAdbTools`
기본 설정으로 `EnhancedAdbTools` 인스턴스를 생성하는 팩토리 함수입니다.

### `create_fast_tools(serial: str) -> EnhancedAdbTools`
`create_tools`와 동일하지만, 인간적인 딜레이가 조금 더 짧게 설정된 프로필을 사용합니다. (여전히 휴먼라이크 동작은 유지됨)

> **Deprecated**: `create_stealth_tools()`는 제거되었습니다. 기본 `create_tools()`를 사용하세요.

---

## Configuration

### `AdbConfig`
ADB 연결 및 디바이스 정보를 담는 데이터 클래스.

- `serial`: 디바이스 시리얼 번호
- `screen_width`: 화면 너비
- `screen_height`: 화면 높이

### `BehaviorConfig`
휴먼라이크 동작의 파라미터를 정의합니다.

- `variation_range`: 터치 좌표 랜덤 오차 범위 (px)
- `typing_speed_mean`: 타이핑 평균 대기 시간 (초)
- `typing_speed_std`: 타이핑 속도 표준 편차
- `mistake_rate`: 오타 발생 확률 (0.0 ~ 1.0)
