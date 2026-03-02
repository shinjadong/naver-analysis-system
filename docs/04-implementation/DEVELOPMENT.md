# 개발 가이드 (Development Guide)

이 문서는 Naver AI Evolution 시스템의 개발자를 위한 가이드입니다.
특히 **EnhancedAdbTools**를 활용한 입력 제어와 새로운 아키텍처 원칙을 설명합니다.

## 핵심 개발 원칙 (2026 업데이트)

1. **모든 입력은 Human-like**: `stealth_mode` 옵션은 제거되었습니다. 모든 입력은 기본적으로 무작위성과 물리적 특성을 가집니다.
2. **단일 진입점**: 모든 디바이스 상호작용은 `EnhancedAdbTools`를 통해서만 이루어져야 합니다. `input tap`이나 `input swipe`를 직접 호출하지 마세요.
3. **BehaviorInjector 활용**: 내부적으로 `BehaviorInjector`가 베지어 커브와 가변 속도를 계산합니다.

---

## EnhancedAdbTools 사용법

### 1. 인스턴스 생성

가장 간단한 방법은 `create_tools` 팩토리 함수를 사용하는 것입니다.

```python
from src.shared.device_tools import create_tools

# 시리얼 번호로 생성 (화면 크기 자동 감지 시도)
tools = create_tools("emulator-5554")
```

### 2. 기본적인 상호작용

```python
# 탭 (베지어 오프셋 자동 적용)
await tools.tap(500, 1000)

# 텍스트 입력 (타이핑 시뮬레이션)
await tools.input_text("검색어 입력")

# 스크롤 (가변 속도)
await tools.scroll_down(distance=600)
```

### 3. 기존 코드 마이그레이션

기존에 직접 ADB를 호출하던 코드는 다음과 같이 변경해야 합니다.

**Before:**
```python
# 기존 (금지됨)
cmd = f"input tap {x} {y}"
await device.shell(cmd)
```

**After:**
```python
# 변경
await tools.tap(x, y)
```

---

## BehaviorConfig 튜닝

특정 페르소나나 상황에 맞춰 행동 패턴을 조정하고 싶다면 `behavior_profile`을 수정하세요.

```python
from src.shared.device_tools import BehaviorConfig

# 실수 많은 사용자 (오타율 10%)
tools.behavior_profile.mistake_rate = 0.1

# 느긋한 사용자 (타이핑 속도 느림)
tools.behavior_profile.typing_speed_mean = 0.25
```

---

## 디렉토리 구조

- `src/shared/device_tools/adb_enhanced.py`: `EnhancedAdbTools` 클래스 정의
- `src/shared/device_tools/behavior_injector.py`: 행동 패턴 생성 로직 (베지어, 스크롤 물리)
- `src/shared/device_tools/__init__.py`: 공개 API (`create_tools`, `AdbConfig` 등)

## 테스트

새로운 기능을 구현한 후에는 반드시 휴먼라이크 동작을 육안으로 확인하거나(개발 중), 로그를 통해 좌표 분산을 확인해야 합니다.

```bash
# 휴먼라이크 동작 테스트 스크립트 실행
python scripts/test_humanlike_flow.py
```
