# 시스템 개선 로드맵

> **작성일**: 2025-12-13
> **기반 분석**: 네이버 추적 시스템 분석 보고서

---

## 1. 현재 시스템 Gap 분석

### 1.1 DeviceManager 모듈

| 현재 구현 | 네이버 추적 시스템 | Gap |
|----------|------------------|-----|
| `tap(x, y)` 단순 좌표 | `me` 파라미터로 터치 궤적 전체 추적 | 베지어 커브 기반 자연스러운 터치 궤적 필요 |
| `swipe(duration=300ms)` 고정 | `navt` - 스크롤 패턴, 속도 변화, 일시정지 분석 | 가변 속도, 관성 스크롤, 중간 멈춤 필요 |
| `input_text()` 일괄 입력 | `slogs` - 키입력 간격(80~400ms), 오타율(10%) | 개별 키 지연, 의도적 오타+백스페이스 필요 |

**현재 코드 위치**: `src/shared/device_manager/__init__.py:144-159`

```python
# 현재 구현 (단순)
def tap(self, serial: str, x: int, y: int) -> bool:
    result = self.execute_command(serial, f"input tap {x} {y}")
    return True
```

**개선 필요 사항**:
- 탭 압력 시뮬레이션
- 탭 지속시간 변화
- 위치 오프셋 (인간 오차)
- 터치 궤적 (시작→유지→해제)

### 1.2 EvolutionEngine 모듈

**현재 적합도 지표** (`src/shared/evolution_engine/__init__.py:25-31`):

| 지표 | 가중치 | 설명 |
|------|--------|------|
| `detection_avoidance` | 25% | 탐지 회피율 |
| `task_success_rate` | 20% | 작업 성공률 |
| `resource_efficiency` | 15% | 자원 효율성 |
| `error_recovery_speed` | 20% | 에러 복구 속도 |
| `behavior_naturalness` | 20% | 행동 자연스러움 |

**누락된 지표** (네이버 추적 분석 기반):

| 신규 지표 | 설명 | 중요도 |
|----------|------|--------|
| `session_complexity` | SC2 로그 다양성 - 단순 조회 vs 탐색 행동 | 🔴 높음 |
| `interaction_density` | 단위 시간당 클릭/호버 이벤트 수 | 🔴 높음 |
| `scroll_depth_quality` | 스크롤 패턴의 자연스러움 | 🔴 높음 |
| `cross_domain_flow` | 블로그→쇼핑→검색 자연스러운 전환 | 🟡 중간 |
| `dwell_time_pattern` | 체류 시간 분포의 자연스러움 | 🟡 중간 |
| `widget_engagement` | 커머스 위젯 상호작용 | 🟢 낮음 |
| `cookie_consistency` | 쿠키 일관성 유지율 | 🔴 높음 |
| `srt_update_pattern` | SRT5/SRT30 갱신 패턴 자연스러움 | 🔴 높음 |

### 1.3 쿠키/세션 관리 (완전 누락)

**네이버 4계층 쿠키 시스템**:

```
┌─ 영구 계층: NNB (2050년 만료), NID
├─ 세션 계층: SRT5/SRT30, _naver_usersession_
├─ 페이지 계층: page_uid, PM_CK_loc
└─ 실험 계층: BUC, __Secure-BUCKET
```

**현재 상태**: 쿠키 관리 기능 **전무**

**필요한 신규 모듈**:
- `CookieManager`: 40개 쿠키 프로파일 관리
- `SessionSimulator`: SRT5/SRT30 갱신 시뮬레이션
- `FingerprintManager`: NNB 일관성 유지

### 1.4 ErrorHandler 모듈

**현재 에러 유형** (`src/shared/error_handler/__init__.py:13-22`):

```python
CAPTCHA, LOGIN_FAILED, RATE_LIMIT, SESSION_EXPIRED,
NETWORK, ELEMENT_NOT_FOUND, DEVICE_DISCONNECTED, APP_CRASH
```

**누락된 네이버 특화 탐지 패턴**:

| 신규 에러 유형 | 탐지 방법 | 설명 |
|--------------|----------|------|
| `BEHAVIOR_ANOMALY` | SC2 로그 이상 패턴 | 비정상적 클릭 빈도/위치 |
| `FINGERPRINT_MISMATCH` | NNB vs 실제 디바이스 불일치 | 쿠키 조작 탐지 |
| `TIMING_ANOMALY` | SRT5/SRT30 갱신 패턴 이상 | 자동화 의심 |
| `AB_TEST_DETECTION` | BUC 변화 후 행동 무반응 | 봇 특성 |
| `SCROLL_PATTERN_ANOMALY` | navt 이상 패턴 | 기계적 스크롤 탐지 |

### 1.5 naver_profiles.yaml 설정

**현재 설정**:

```yaml
stealth:
  random_delays: true
  human_like_curves: true
  session_variance: 0.3
  activity_breaks: true
```

**누락된 설정**:
- 추적 엔드포인트 정보
- 쿠키 관리 전략
- 세션 시뮬레이션 파라미터
- A/B 테스트 대응 설정

---

## 2. 개선 로드맵

### Phase 1: Critical (탐지 회피 핵심)

#### 1.1 행동 시뮬레이터 고도화

**대상 파일**: `src/shared/device_manager/__init__.py`

**신규 클래스/함수**:

```python
class HumanBehaviorSimulator:
    """인간 행동 시뮬레이터"""

    def generate_bezier_touch(self, start, end, duration) -> List[TouchPoint]:
        """베지어 커브 기반 터치 궤적 생성"""

    def generate_variable_scroll(self, distance, style='natural') -> ScrollSequence:
        """가변 속도 스크롤 + 관성 + 중간 멈춤"""

    def generate_typing_sequence(self, text) -> List[KeyEvent]:
        """개별 키 지연 + 오타 + 백스페이스"""
```

**파라미터 (naver_profiles.yaml 기반)**:

| 파라미터 | 현재 값 | 개선 값 |
|----------|--------|---------|
| 타이핑 지연 | 80-400ms | 50-500ms + 가우시안 분포 |
| 오타 확률 | 10% | 5-15% + 문맥 기반 |
| 스크롤 속도 | 고정 | 시작 가속 → 유지 → 감속 |
| 탭 오프셋 | ±10px | ±5-15px + 손가락 크기 모델 |

#### 1.2 쿠키/세션 매니저 신규 개발

**신규 파일**: `src/shared/cookie_manager/__init__.py`

```python
class CookieManager:
    """네이버 쿠키 프로파일 관리"""

    REQUIRED_COOKIES = [
        'NNB', 'NID', 'SRT5', 'SRT30', 'BUC',
        'page_uid', '_naver_usersession_', ...
    ]

    def generate_nnb(self) -> str:
        """NNB 쿠키 생성 (12자리 영숫자)"""

    def update_srt_cookies(self) -> Dict:
        """SRT5/SRT30 갱신 시뮬레이션"""

    def maintain_consistency(self, device_fingerprint: Dict) -> bool:
        """쿠키-디바이스 일관성 검증"""

class SessionSimulator:
    """세션 행동 시뮬레이터"""

    def simulate_session_lifecycle(self) -> SessionEvents:
        """세션 시작 → 활동 → 휴식 → 종료 패턴"""

    def generate_page_uid(self, context: Dict) -> str:
        """page_uid 생성 (컨텍스트 기반)"""
```

**쿠키 관리 전략**:

| 쿠키 | 갱신 주기 | 일관성 요구 |
|------|----------|------------|
| NNB | 30일 | 디바이스 핑거프린트와 일치 |
| NID | 로그인 시 | 계정과 일치 |
| SRT5 | 5분마다 | 활동 시간과 일치 |
| SRT30 | 30분마다 | 세션 지속과 일치 |
| BUC | 실험 노출 시 | 행동 변화와 연계 |

#### 1.3 추적 엔드포인트 설정

**naver_profiles.yaml 추가**:

```yaml
tracking_endpoints:
  # 회피해야 할 추적 시스템
  tivan:
    base_url: "tivan.naver.com"
    paths:
      - "/sc2/*"      # 상세 클릭 추적
      - "/g/*"        # 성능 메트릭
    response_strategy: "natural_timing"

  veta:
    base_url: "siape.veta.naver.com"
    paths:
      - "/fxview"     # 광고 노출
      - "/fxshow"     # 광고 표시
      - "/openrtb/*"  # RTB 추적
    response_strategy: "selective_engagement"

  nlog:
    base_url: "nlog.naver.com"
    paths:
      - "/n"          # 세션 로깅
    response_strategy: "consistent_session"

  gfa:
    base_url: "g.tivan.naver.com"
    paths:
      - "/gfa/*"      # 암호화 페이로드
    response_strategy: "realistic_payload"

cookie_strategy:
  nnb:
    rotation_days: 30
    format: "alphanumeric_12"
    device_binding: true

  nid:
    maintain_consistency: true
    profile_segments: ["527", "general"]

  srt:
    srt5_interval_seconds: 300
    srt30_interval_seconds: 1800
    jitter_percent: 10

  buc:
    track_experiments: true
    behavior_adaptation: true

session_simulation:
  lifecycle:
    min_duration_seconds: 25
    max_duration_seconds: 120
    break_probability: 0.15
    break_duration_range: [5, 30]

  page_transitions:
    min_dwell_seconds: 3
    max_dwell_seconds: 60
    scroll_before_leave_probability: 0.7
```

---

### Phase 2: Important (품질 최적화)

#### 2.1 피트니스 지표 확장

**대상 파일**: `src/shared/evolution_engine/__init__.py`

**확장된 FitnessMetrics**:

```python
@dataclass
class FitnessMetrics:
    """확장된 적합도 평가 지표"""

    # 기존 지표
    detection_avoidance: float      # 탐지 회피율
    task_success_rate: float        # 작업 성공률
    resource_efficiency: float      # 자원 효율성
    error_recovery_speed: float     # 에러 복구 속도
    behavior_naturalness: float     # 행동 자연스러움

    # 신규 지표 (네이버 추적 분석 기반)
    session_complexity: float       # 세션 복잡도 (SC2 다양성)
    interaction_density: float      # 상호작용 밀도
    scroll_depth_quality: float     # 스크롤 패턴 품질
    cross_domain_flow: float        # 크로스-도메인 흐름
    dwell_time_pattern: float       # 체류 시간 패턴
    cookie_consistency: float       # 쿠키 일관성
    srt_update_pattern: float       # SRT 갱신 패턴

    def total_score(self, weights: Dict[str, float] = None) -> float:
        """확장된 가중치 적용 총점"""
        default_weights = {
            # 기존 (총 55%)
            "detection_avoidance": 0.15,
            "task_success_rate": 0.15,
            "resource_efficiency": 0.05,
            "error_recovery_speed": 0.10,
            "behavior_naturalness": 0.10,

            # 신규 (총 45%)
            "session_complexity": 0.08,
            "interaction_density": 0.08,
            "scroll_depth_quality": 0.07,
            "cross_domain_flow": 0.05,
            "dwell_time_pattern": 0.07,
            "cookie_consistency": 0.05,
            "srt_update_pattern": 0.05
        }
        # ... 계산 로직
```

**가중치 조정 근거**:

| 지표 | 가중치 | 근거 |
|------|--------|------|
| `detection_avoidance` | 15%→ | 네이버 다층 추적 대응 |
| `session_complexity` | 8% | SC2 로그 다양성 중요 |
| `cookie_consistency` | 5% | 핑거프린트 일치 필수 |
| `srt_update_pattern` | 5% | 세션 진위 판별 핵심 |

#### 2.2 에러 핸들러 강화

**대상 파일**: `src/shared/error_handler/__init__.py`

**확장된 ErrorType**:

```python
class ErrorType(Enum):
    """확장된 에러 유형"""

    # 기존
    CAPTCHA = "captcha"
    LOGIN_FAILED = "login_failed"
    RATE_LIMIT = "rate_limit"
    SESSION_EXPIRED = "session_expired"
    NETWORK = "network"
    ELEMENT_NOT_FOUND = "element_not_found"
    DEVICE_DISCONNECTED = "device_disconnected"
    APP_CRASH = "app_crash"
    UNKNOWN = "unknown"

    # 신규 (네이버 특화)
    BEHAVIOR_ANOMALY = "behavior_anomaly"           # 행동 이상 탐지
    FINGERPRINT_MISMATCH = "fingerprint_mismatch"   # 핑거프린트 불일치
    TIMING_ANOMALY = "timing_anomaly"               # 타이밍 이상
    AB_TEST_DETECTION = "ab_test_detection"         # A/B 테스트 탐지
    SCROLL_PATTERN_ANOMALY = "scroll_pattern_anomaly"  # 스크롤 패턴 이상
    COOKIE_INVALIDATION = "cookie_invalidation"     # 쿠키 무효화
```

**신규 탐지 패턴**:

```python
ERROR_PATTERNS = {
    # 기존 패턴...

    # 신규 네이버 특화 패턴
    ErrorType.BEHAVIOR_ANOMALY: [
        "비정상적인 접근", "자동화 의심", "봇 감지",
        "unusual activity", "automated access"
    ],
    ErrorType.FINGERPRINT_MISMATCH: [
        "기기 정보 불일치", "세션 무효", "재인증 필요"
    ],
    ErrorType.TIMING_ANOMALY: [
        "너무 빠른 요청", "비정상 패턴", "접속 제한"
    ],
    ErrorType.SCROLL_PATTERN_ANOMALY: [
        "스크롤 확인", "사용자 확인"
    ],
    ErrorType.COOKIE_INVALIDATION: [
        "쿠키 만료", "세션 갱신 필요"
    ]
}
```

---

### Phase 3: Enhancement (고급 기능)

#### 3.1 크로스-서비스 흐름 시뮬레이션

**신규 파일**: `src/shared/cross_service_flow/__init__.py`

```python
class CrossServiceFlowSimulator:
    """크로스-서비스 흐름 시뮬레이터"""

    NATURAL_FLOWS = [
        # 검색 → 블로그 → 쇼핑
        ["search.naver.com", "blog.naver.com", "shopping.naver.com"],
        # 메인 → 뉴스 → 블로그
        ["www.naver.com", "news.naver.com", "blog.naver.com"],
        # 블로그 → 블로그 (내부 탐색)
        ["blog.naver.com", "blog.naver.com", "blog.naver.com"],
    ]

    def generate_flow(self, target_service: str) -> List[ServiceVisit]:
        """자연스러운 서비스 전환 경로 생성"""

    def maintain_session_across_services(self, flow: List[ServiceVisit]) -> SessionContext:
        """서비스 간 세션 연계 유지"""
```

#### 3.2 A/B 테스트 대응

**신규 파일**: `src/shared/ab_test_handler/__init__.py`

```python
class ABTestHandler:
    """A/B 테스트 대응 핸들러"""

    def detect_experiment(self, response_headers: Dict, cookies: Dict) -> Optional[Experiment]:
        """실험 배정 감지 (BUC 쿠키, abt 파라미터)"""

    def adapt_behavior(self, experiment: Experiment) -> BehaviorModification:
        """실험군에 맞는 행동 적응"""

    def simulate_natural_response(self, experiment: Experiment) -> ResponsePattern:
        """UI 변화에 대한 자연스러운 반응 생성"""
```

#### 3.3 실시간 탐지 회피 엔진

**신규 파일**: `src/shared/detection_evasion/__init__.py`

```python
class DetectionEvasionEngine:
    """실시간 탐지 회피 엔진"""

    def analyze_tracking_response(self, response: TrackingResponse) -> ThreatLevel:
        """추적 응답 분석 및 위협 수준 평가"""

    def adjust_behavior_realtime(self, threat_level: ThreatLevel) -> BehaviorAdjustment:
        """실시간 행동 조정"""

    def generate_counter_pattern(self, detected_pattern: str) -> CounterPattern:
        """탐지 패턴에 대한 대응 패턴 생성"""
```

---

## 3. 파일 변경 요약

### 신규 파일

| 파일 경로 | 용도 |
|----------|------|
| `src/shared/cookie_manager/__init__.py` | 쿠키/세션 관리 |
| `src/shared/behavior_simulator/__init__.py` | 인간 행동 시뮬레이션 |
| `src/shared/cross_service_flow/__init__.py` | 크로스-서비스 흐름 |
| `src/shared/ab_test_handler/__init__.py` | A/B 테스트 대응 |
| `src/shared/detection_evasion/__init__.py` | 탐지 회피 엔진 |
| `docs/NAVER_TRACKING_ANALYSIS.md` | 네이버 추적 분석 문서 |
| `docs/IMPROVEMENT_ROADMAP.md` | 개선 로드맵 (현재 문서) |

### 수정 파일

| 파일 경로 | 변경 내용 |
|----------|----------|
| `src/shared/device_manager/__init__.py` | HumanBehaviorSimulator 통합 |
| `src/shared/evolution_engine/__init__.py` | FitnessMetrics 확장 |
| `src/shared/error_handler/__init__.py` | ErrorType 확장 |
| `config/naver_profiles.yaml` | 추적 엔드포인트, 쿠키 전략 추가 |
| `docs/ARCHITECTURE.md` | 신규 모듈 반영 |
| `docs/WSL_CLAUDE_CONTEXT.md` | 개선 사항 반영 |
| `README.md` | 신규 문서 링크 추가 |

---

## 4. 예상 효과

### 탐지 위험도 변화

| 영역 | 현재 | Phase 1 후 | Phase 2 후 | Phase 3 후 |
|------|------|-----------|-----------|-----------|
| 터치 패턴 | 🔴 높음 | 🟡 중간 | 🟢 낮음 | 🟢 낮음 |
| 쿠키 일관성 | 🔴 높음 (미구현) | 🟡 중간 | 🟢 낮음 | 🟢 낮음 |
| 세션 패턴 | 🟡 중간 | 🟢 낮음 | 🟢 낮음 | 🟢 낮음 |
| 스크롤 행동 | 🟡 중간 | 🟢 낮음 | 🟢 낮음 | 🟢 낮음 |
| A/B 테스트 대응 | 🔴 높음 (미구현) | 🔴 높음 | 🟡 중간 | 🟢 낮음 |
| 크로스-서비스 | 🟡 중간 | 🟡 중간 | 🟢 낮음 | 🟢 낮음 |

### 종합 탐지 회피율 예상

| Phase | 예상 탐지 회피율 |
|-------|----------------|
| 현재 | ~40% |
| Phase 1 완료 | ~70% |
| Phase 2 완료 | ~85% |
| Phase 3 완료 | ~95% |

---

## 5. 구현 우선순위

### 즉시 (Phase 1)

1. **쿠키 매니저 구현** - 가장 큰 Gap
2. **HumanBehaviorSimulator 구현** - 탐지 핵심
3. **naver_profiles.yaml 업데이트** - 설정 기반

### 단기 (Phase 2)

4. **FitnessMetrics 확장** - 평가 고도화
5. **ErrorType 확장** - 탐지 대응
6. **세션 시뮬레이터 구현** - SRT 관리

### 중기 (Phase 3)

7. **CrossServiceFlowSimulator** - 고급 회피
8. **ABTestHandler** - 실험 대응
9. **DetectionEvasionEngine** - 실시간 대응

---

## 6. 참고 문서

- [네이버 추적 시스템 분석](NAVER_TRACKING_ANALYSIS.md)
- [시스템 아키텍처](ARCHITECTURE.md)
- [WSL Claude 컨텍스트](WSL_CLAUDE_CONTEXT.md)

---

*마지막 업데이트: 2025-12-13*
