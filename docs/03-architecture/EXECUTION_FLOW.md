# 실행 흐름 문서 (Execution Flow)

> **버전**: 0.9.1
> **최종 업데이트**: 2026-01-08

이 문서는 프로그램 실행 시 엔트리포인트부터 각 함수/모듈이 어떤 순서로 호출되는지 한눈에 파악할 수 있도록 작성되었습니다.

---

## 0. 빠른 시작 (CLI)

> **신규 v0.9.1**: 통합 CLI `naver`를 통해 모든 기능에 접근할 수 있습니다.

### 무엇을 하고 싶으신가요?

```
┌─────────────────────────────────────────────────────────────────────┐
│                     무엇을 하고 싶으신가요?                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ▶ 시스템 상태 확인        →  naver status                          │
│                                                                      │
│  ▶ 단일 세션 실행          →  naver run session -k "맛집"           │
│                                                                      │
│  ▶ 다중 세션 캠페인        →  naver run campaign -s 10 -k "맛집"    │
│                                                                      │
│  ▶ 페르소나 관리           →  naver persona list                    │
│                             →  naver persona create 10              │
│                                                                      │
│  ▶ 테스트/검증             →  naver test smoke                      │
│                                                                      │
│  ▶ 디버깅                  →  naver debug portal                    │
│                             →  naver debug device                   │
│                                                                      │
│  ▶ 도움말                  →  naver --help                          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### CLI 명령어 구조

```
naver
├── status              # 시스템 상태 확인
├── version             # 버전 정보
├── run
│   ├── session         # 단일 세션 실행
│   └── campaign        # 다중 세션 캠페인
├── persona
│   ├── list            # 목록 조회
│   ├── create          # 생성
│   └── delete          # 삭제
├── test
│   ├── smoke           # 스모크 테스트
│   ├── unit            # 단위 테스트
│   └── e2e             # E2E 테스트
└── debug
    ├── portal          # Portal 상태
    ├── device          # 디바이스 상태
    └── tap             # 탭 테스트
```

---

## 1. 전체 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      UNIFIED ENTRY POINT (CLI)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                    naver (src/shared/cli/)                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │ run session │ │ run campaign│ │ persona     │ │ test/debug  │       │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    LEGACY ENTRY POINTS (scripts/)                       │
├─────────────────────────────────────────────────────────────────────────┤
│  scripts/run_pipeline.py     │  scripts/test_smart_executor.py          │
│  scripts/test_naver_flow.py  │  scripts/test_portal_integration.py      │
└───────────────────────────────┴─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  pipeline/NaverSessionPipeline    │  smart_executor/SmartExecutor       │
│  campaign_orchestrator/           │                                      │
└───────────────────────────────────┴─────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌──────────────────────┐ ┌──────────────────┐ ┌──────────────────────────┐
│   PERSONA LAYER      │ │   UI LAYER       │ │   DEVICE LAYER           │
├──────────────────────┤ ├──────────────────┤ ├──────────────────────────┤
│ persona_manager/     │ │ portal_client/   │ │ device_tools/            │
│ - PersonaManager     │ │ - PortalClient   │ │ - EnhancedAdbTools       │
│ - PersonaStore       │ │ - ElementFinder  │ │ - BehaviorInjector       │
│ - DeviceIdentity     │ │ - UITree         │ │                          │
└──────────────────────┘ └──────────────────┘ └──────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │      ANDROID DEVICE           │
                    │  (ADB + DroidRun Portal APK)  │
                    └───────────────────────────────┘
```

---

## 2. 핵심 실행 흐름

### 2.1 메인 파이프라인 실행 (`run_pipeline.py`)

```
python scripts/run_pipeline.py --keywords "맛집" --pageviews 3
```

```
scripts/run_pipeline.py
│
├─► main()                                          # :256
│   ├─► argparse로 인자 파싱
│   └─► run_single_session(args)                    # :97
│
├─► run_single_session()                            # :97
│   ├─► from pipeline import NaverSessionPipeline   # :99
│   ├─► PipelineConfig() 생성                        # :105-109
│   ├─► NaverSessionPipeline(config) 생성            # :111
│   └─► pipeline.run_session()                      # :116 또는 :126
│
└─► NaverSessionPipeline.run_session()
    └─► (아래 2.2 참조)
```

### 2.2 세션 실행 흐름 (`NaverSessionPipeline`)

```
src/shared/pipeline/__init__.py
│
├─► NaverSessionPipeline.__init__()                 # :109
│   ├─► PersonaManager() 생성                        # :116-119
│   ├─► PortalClient() 생성                          # :120
│   ├─► ElementFinder() 생성                         # :121
│   ├─► AdbConfig() 생성                             # :124-128
│   └─► EnhancedAdbTools(adb_config) 생성            # :129
│
├─► run_session()                                   # :471
│   │
│   ├─► [1] 페르소나 선택 및 전환
│   │   └─► persona_manager.switch_to_next()        # :500-502
│   │       ├─► PersonaStore.get_least_recent()
│   │       ├─► DeviceIdentityManager.set_android_id()
│   │       └─► ChromeDataManager.restore()
│   │
│   ├─► [2] 키워드 검색 + 방문 (반복)
│   │   └─► search_and_visit()                      # :528
│   │       ├─► _open_url()                         # :410
│   │       │   └─► adb_tools.open_url()
│   │       │       └─► EnhancedAdbTools.open_url()  # adb_enhanced.py:270
│   │       │
│   │       ├─► _find_and_tap_search_result()       # :416
│   │       │   ├─► finder.find_search_results()    # Portal 사용시
│   │       │   │   └─► PortalClient.get_ui_tree()
│   │       │   │       └─► adb shell content query --uri content://com.droidrun.portal/state
│   │       │   │
│   │       │   └─► _tap(x, y)                      # :221 또는 :227
│   │       │       └─► adb_tools.tap()
│   │       │           └─► EnhancedAdbTools.tap()   # adb_enhanced.py:175
│   │       │               └─► BehaviorInjector.generate_human_tap()
│   │       │                   └─► 베지어 오프셋 계산
│   │       │
│   │       └─► _simulate_reading()                 # :433
│   │           └─► _scroll()                       # :291
│   │               └─► adb_tools.scroll_down()
│   │                   └─► EnhancedAdbTools.scroll_down()  # adb_enhanced.py:226
│   │                       └─► BehaviorInjector.generate_variable_scroll()
│   │                           └─► 가변 속도 세그먼트 생성
│   │
│   └─► [3] 세션 저장
│       └─► persona_manager.save_current_session()
│           └─► PersonaStore.update_session()
```

---

## 3. SmartExecutor 실행 흐름 (Portal 기반)

### 3.1 텍스트로 요소 찾아서 탭

```
SmartExecutor.tap_by_text("블로그")
```

```
src/shared/smart_executor/executor.py
│
├─► tap_by_text(text="블로그")                       # :311
│   │
│   ├─► [1] UI 트리 갱신
│   │   └─► refresh_ui()                            # :265
│   │       └─► portal.get_ui_tree()
│   │           └─► PortalClient.get_ui_tree()      # client.py:130
│   │               └─► _query_content_provider("state")
│   │                   └─► adb shell content query --uri content://com.droidrun.portal/state
│   │                       └─► JSON 파싱 → UITree 생성
│   │
│   ├─► [2] 텍스트로 요소 검색
│   │   └─► tree.find_all(text_contains=text)       # :345
│   │       └─► UITree.find_all()                   # element.py
│   │           └─► 재귀적으로 모든 노드 검색
│   │
│   └─► [3] 요소 탭 (휴먼라이크)
│       └─► _tap_element(element)                   # :359
│           └─► element.center → (x, y) 좌표
│           └─► _execute_tap(x, y)                  # :537
│               └─► adb_tools.tap(x, y)             # :248
│                   └─► EnhancedAdbTools.tap()
│                       └─► (아래 4.1 참조)
```

### 3.2 Lifecycle 실행 (OBSERVE → ACT → VERIFY)

```
SmartExecutor.execute("tap_text", text="블로그")
```

```
src/shared/smart_executor/executor.py
│
├─► execute(action_type="tap_text", text="블로그")  # :769
│   │
│   ├─► [1] OBSERVE: 액션 전 스냅샷
│   │   └─► _capture_snapshot()                     # :716
│   │       └─► refresh_ui()
│   │       └─► UISnapshot 생성 (요소 수, 클릭 가능 요소 등)
│   │
│   ├─► [2] ACT: 액션 실행
│   │   └─► _dispatch_action("tap_text", params)    # :812
│   │       └─► tap_by_text(text="블로그")          # :849
│   │           └─► (위 3.1 흐름 참조)
│   │
│   └─► [3] VERIFY: 액션 후 스냅샷
│       └─► _capture_snapshot()                     # :830
│           └─► UI 변화 확인
│
└─► ExecutionContext 반환
    ├─► snapshot_before: 이전 상태
    ├─► snapshot_after: 이후 상태
    └─► result: ActionResult
```

---

## 4. EnhancedAdbTools 실행 흐름 (휴먼라이크 입력)

### 4.1 탭 (Bezier Offset 적용)

```
EnhancedAdbTools.tap(540, 700)
```

```
src/shared/device_tools/adb_enhanced.py
│
├─► tap(x=540, y=700)                               # :175
│   │
│   ├─► [1] 베지어 오프셋 생성
│   │   └─► behavior.generate_human_tap(x, y)       # :180
│   │       └─► BehaviorInjector.generate_human_tap()  # behavior_injector.py:150
│   │           ├─► _apply_tap_offset()             # 랜덤 오프셋 (±15px)
│   │           └─► TapResult(actual_x, actual_y, offset_x, offset_y)
│   │
│   ├─► [2] ADB 명령 실행
│   │   └─► _shell(f"input tap {actual_x} {actual_y}")  # :190
│   │       └─► subprocess.run(["adb", "-s", serial, "shell", ...])
│   │
│   └─► [3] 결과 반환
│       └─► ActionResult(
│               success=True,
│               details={
│                   'original_x': 540, 'original_y': 700,
│                   'actual_x': 537, 'actual_y': 705,
│                   'offset_x': -3, 'offset_y': +5
│               }
│           )
```

### 4.2 스크롤 (가변 속도 세그먼트)

```
EnhancedAdbTools.scroll_down(distance=600)
```

```
src/shared/device_tools/adb_enhanced.py
│
├─► scroll_down(distance=600)                       # :226
│   │
│   ├─► [1] 시작/끝 좌표 계산
│   │   └─► center_x = screen_width // 2
│   │   └─► start_y = screen_height * 0.7
│   │   └─► end_y = start_y - distance
│   │
│   └─► [2] 가변 속도 스와이프 실행
│       └─► _variable_speed_swipe(x, start_y, x, end_y)  # :240
│           │
│           ├─► [2-1] 세그먼트 생성
│           │   └─► behavior.generate_variable_scroll()  # :245
│           │       └─► BehaviorInjector.generate_variable_scroll()
│           │           │                           # behavior_injector.py:200
│           │           ├─► 가속 구간 (25%): 느림 → 빠름
│           │           ├─► 유지 구간 (50%): 일정 속도
│           │           ├─► 감속 구간 (25%): 빠름 → 느림
│           │           └─► [SwipeSegment, SwipeSegment, ...]
│           │
│           └─► [2-2] 세그먼트별 swipe 실행
│               └─► for segment in segments:        # :260
│                   └─► _shell(f"input swipe {x1} {y1} {x2} {y2} {duration}")
│
└─► ActionResult(
        success=True,
        duration_ms=2450,  # 전체 소요 시간
        details={'segments': 5}  # 세그먼트 수
    )
```

---

## 5. Portal Client 실행 흐름 (UI 트리 획득)

```
PortalClient.get_ui_tree()
```

```
src/shared/portal_client/client.py
│
├─► get_ui_tree()                                   # :130
│   │
│   ├─► [1] 캐시 확인
│   │   └─► if (now - _cache_time) < cache_ttl:
│   │       └─► return _ui_cache
│   │
│   ├─► [2] Content Provider 쿼리
│   │   └─► _query_content_provider("state")        # :110
│   │       └─► _run_adb("shell", "content query --uri content://com.droidrun.portal/state")
│   │           └─► subprocess.run(["adb", ...])
│   │           └─► 응답: Row: 0 result={"status":"success","data":"{...}"}
│   │
│   ├─► [3] JSON 파싱
│   │   └─► json.loads(outer['data'])
│   │       └─► {
│   │             "phone_state": {"packageName": "com.android.chrome", ...},
│   │             "a11y_tree": [{...}, {...}, ...]
│   │           }
│   │
│   └─► [4] UITree 생성
│       └─► _parse_ui_tree(data['a11y_tree'])       # :160
│           └─► UITree(elements=[UIElement, UIElement, ...])
│               └─► 각 UIElement: text, bounds, clickable, children, ...
```

---

## 6. Persona Manager 실행 흐름

### 6.1 페르소나 전환

```
PersonaManager.switch_to_next("least_recent")
```

```
src/shared/persona_manager/manager.py
│
├─► switch_to_next(strategy="least_recent")         # :80
│   │
│   ├─► [1] 페르소나 선택
│   │   └─► store.get_least_recent()                # :90
│   │       └─► PersonaStore.get_least_recent()     # persona_store.py:120
│   │           └─► SELECT * FROM personas ORDER BY last_active ASC LIMIT 1
│   │
│   ├─► [2] ANDROID_ID 변경 (루팅 필요)
│   │   └─► device_identity.set_android_id(persona.android_id)  # :100
│   │       └─► DeviceIdentityManager.set_android_id()  # device_identity.py:50
│   │           └─► adb shell "settings put secure android_id {id}"
│   │           └─► adb shell "am broadcast -a android.intent.action.BOOT_COMPLETED"
│   │
│   ├─► [3] Chrome 데이터 복원
│   │   └─► chrome_data.restore(persona.persona_id)  # :110
│   │       └─► ChromeDataManager.restore()         # chrome_data.py:80
│   │           └─► adb shell "pm clear com.android.chrome"
│   │           └─► adb push {backup_path} /data/data/com.android.chrome/
│   │
│   └─► [4] 결과 반환
│       └─► PersonaSwitchResult(success=True, persona=persona)
```

---

## 7. 파일 위치 요약

### 7.1 엔트리포인트 (scripts/)

| 파일 | 용도 | 주요 함수 |
|------|------|----------|
| `run_pipeline.py` | 메인 파이프라인 실행 | `main()`, `run_single_session()` |
| `test_smart_executor.py` | SmartExecutor 테스트 | `test_smart_executor()` |
| `test_portal_integration.py` | Portal 통합 테스트 | `test_text_based_tap()` |
| `test_humanlike_verification.py` | 휴먼라이크 검증 | `verify_humanlike_behavior()` |
| `test_naver_flow.py` | 기본 플로우 테스트 | `run_naver_flow_test()` |

### 7.2 핵심 모듈 (src/shared/)

| 모듈 | 파일 | 클래스/함수 | 역할 |
|------|------|------------|------|
| **pipeline** | `__init__.py` | `NaverSessionPipeline` | 통합 세션 파이프라인 |
| **smart_executor** | `executor.py` | `SmartExecutor` | Portal + 휴먼라이크 통합 |
| **portal_client** | `client.py` | `PortalClient` | Portal APK 통신 |
| | `element.py` | `UIElement`, `UITree` | UI 요소 데이터 구조 |
| | `finder.py` | `ElementFinder` | 요소 검색 헬퍼 |
| **device_tools** | `adb_enhanced.py` | `EnhancedAdbTools` | ADB + 휴먼라이크 |
| | `behavior_injector.py` | `BehaviorInjector` | 베지어/가변속도 생성 |
| **persona_manager** | `manager.py` | `PersonaManager` | 페르소나 통합 관리 |
| | `persona_store.py` | `PersonaStore` | SQLite 저장소 |
| | `device_identity.py` | `DeviceIdentityManager` | ANDROID_ID 변경 |
| | `chrome_data.py` | `ChromeDataManager` | Chrome 데이터 관리 |

---

## 8. 핵심 데이터 흐름

### 8.1 미션 → 탭 실행 전체 흐름

```
┌─────────────────────────────────────────────────────────────────────────┐
│  1. MISSION: "블로그 탭 클릭"                                            │
└───────────────────────────────────────────────────────────────────────┬─┘
                                                                        │
┌───────────────────────────────────────────────────────────────────────▼─┐
│  2. PORTAL: UI 트리 획득                                                │
│     PortalClient.get_ui_tree()                                          │
│     → adb shell content query --uri content://com.droidrun.portal/state │
│     → JSON 파싱 → UITree(151개 노드)                                     │
└───────────────────────────────────────────────────────────────────────┬─┘
                                                                        │
┌───────────────────────────────────────────────────────────────────────▼─┐
│  3. TEXT MATCHING: 요소 검색                                            │
│     UITree.find_all(text_contains="블로그")                             │
│     → 매칭 요소: [{text: "블로그", bounds: "22,431,191,552"}, ...]       │
└───────────────────────────────────────────────────────────────────────┬─┘
                                                                        │
┌───────────────────────────────────────────────────────────────────────▼─┐
│  4. COORDINATE: 좌표 획득                                               │
│     element.center → (106, 491)                                         │
└───────────────────────────────────────────────────────────────────────┬─┘
                                                                        │
┌───────────────────────────────────────────────────────────────────────▼─┐
│  5. HUMANLIKE: 베지어 오프셋 적용                                        │
│     BehaviorInjector.generate_human_tap(106, 491)                       │
│     → TapResult(actual_x=107, actual_y=499, offset_x=+1, offset_y=+8)   │
└───────────────────────────────────────────────────────────────────────┬─┘
                                                                        │
┌───────────────────────────────────────────────────────────────────────▼─┐
│  6. EXECUTE: ADB 명령 실행                                              │
│     adb shell input tap 107 499                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.2 스크롤 가변 속도 세그먼트

```
┌─────────────────────────────────────────────────────────────────────────┐
│  scroll_down(distance=600)                                              │
└───────────────────────────────────────────────────────────────────────┬─┘
                                                                        │
┌───────────────────────────────────────────────────────────────────────▼─┐
│  BehaviorInjector.generate_variable_scroll()                            │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 세그먼트 1 (가속): y=1638→1538, duration=400ms, speed=느림→중간  │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │ 세그먼트 2 (유지): y=1538→1338, duration=300ms, speed=빠름       │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │ 세그먼트 3 (유지): y=1338→1138, duration=280ms, speed=빠름       │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │ 세그먼트 4 (감속): y=1138→1038, duration=450ms, speed=중간→느림  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  총 소요시간: 1430ms (실제: 1235~3695ms 랜덤 변동)                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 9. 실행 명령어 예시

### 9.1 기본 파이프라인 실행

```bash
# 단일 세션 (기본 키워드)
python scripts/run_pipeline.py

# 커스텀 키워드
python scripts/run_pipeline.py --keywords "맛집 추천" "여행 블로그"

# 여러 세션
python scripts/run_pipeline.py --sessions 5 --pageviews 3

# 상태 확인
python scripts/run_pipeline.py --status
```

### 9.2 테스트 스크립트 실행

```bash
# Portal + SmartExecutor 통합 테스트
python scripts/test_portal_integration.py

# 휴먼라이크 동작 검증
python scripts/test_humanlike_verification.py

# 기본 플로우 테스트
python scripts/test_naver_flow.py
```

---

## 10. 디버깅 포인트

| 문제 | 확인 위치 | 해결 방법 |
|------|----------|----------|
| Portal 빈 트리 | `PortalClient.get_ui_tree()` | Accessibility Service 재시작 |
| 요소 찾기 실패 | `UITree.find_all()` | 텍스트 매칭 조건 완화 |
| 베지어 오프셋 없음 | `BehaviorInjector.generate_human_tap()` | BehaviorConfig 확인 |
| 스크롤 너무 빠름 | `BehaviorInjector.generate_variable_scroll()` | scroll_deceleration_ratio 조정 |
| 페르소나 전환 실패 | `PersonaManager.switch_to_next()` | 루팅 상태, DB 확인 |

---

*최종 업데이트: 2026-01-08*
