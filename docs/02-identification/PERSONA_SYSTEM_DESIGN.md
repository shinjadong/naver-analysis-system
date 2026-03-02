# Persona Management System 설계서

> **작성일**: 2025-12-15
> **버전**: 1.0.0
> **상태**: 설계 완료, 구현 대기

---

## 1. 개요

### 1.1 문제점

**기존 방식의 한계:**
```
매번 새 사용자 생성 (IP + 쿠키 리셋)
  → 모든 방문자가 "첫 방문"
  → 재방문율 0%
  → 네이버 품질 지표 불리
```

### 1.2 해결책

**Persona 기반 접근:**
```
가상 사용자 ID를 여러 개 생성/관리
  → 각 페르소나가 "재방문자"로 인식
  → 일관된 행동 패턴 유지
  → 네이버 품질 지표 정상화
```

---

## 2. 시스템 아키텍처

### 2.1 전체 레이어

```
+-------------------------------------------------------------------+
|                    Naver AI Evolution v0.4.0                      |
+-------------------------------------------------------------------+
|                                                                   |
|  Layer 1: Persona Management (루팅 필요)                          |
|  +-------------------------------------------------------------+  |
|  |  PersonaStore   DeviceIdentity   CookieState   VisitHistory |  |
|  |  (페르소나 DB)  (ANDROID_ID)     (NNB 쿠키)   (방문 기록)   |  |
|  +-------------------------------------------------------------+  |
|                              |                                    |
|                              v                                    |
|  Layer 2: UI Detection (Portal APK - 루팅 불필요)                 |
|  +-------------------------------------------------------------+  |
|  |  PortalClient     ElementFinder     UIStateCache            |  |
|  |  (HTTP 통신)     (요소 검색)       (상태 캐싱)             |  |
|  +-------------------------------------------------------------+  |
|                              |                                    |
|                              v                                    |
|  Layer 3: Behavior Execution (기존)                               |
|  +-------------------------------------------------------------+  |
|  |  BehaviorInjector  EnhancedAdbTools  EngagementSimulator    |  |
|  |  (베지어 커브)    (탐지 회피 ADB)  (인게이지먼트)          |  |
|  +-------------------------------------------------------------+  |
|                                                                   |
+-------------------------------------------------------------------+
```

### 2.2 모듈 구조

```
src/shared/persona_manager/
├── __init__.py
├── persona.py               # Persona, BehaviorProfile 데이터클래스
├── persona_store.py         # SQLite 기반 저장소
├── device_identity.py       # ANDROID_ID/GSF_ID 변경 (루팅)
├── cookie_state.py          # Chrome 쿠키 직접 조작 (루팅)
└── visit_history.py         # 방문 기록 추적

src/shared/portal_client/
├── __init__.py
├── client.py                # DroidRun Portal HTTP 클라이언트
├── element.py               # UIElement 데이터클래스
├── finder.py                # ElementFinder (텍스트/속성 검색)
└── state_cache.py           # UI 상태 캐싱
```

---

## 3. 데이터 구조

### 3.1 Persona

```python
@dataclass
class Persona:
    """가상 사용자 페르소나"""

    # === 식별자 ===
    persona_id: str                    # 내부 관리 ID (uuid)
    name: str                          # "직장인_30대_남성" 등

    # === 디바이스 ID (루팅 필요) ===
    android_id: str                    # ANDROID_ID (16자 hex)
    gsf_id: str                        # Google Services Framework ID
    advertising_id: str                # 광고 ID (UUID 형식)

    # === 네이버 식별자 ===
    nnb_cookie: str                    # 네이버 NNB 쿠키
    nid_cookie: Optional[str]          # 로그인 시 NID (비로그인: None)
    device_fingerprint: Dict           # 디바이스 정보

    # === 행동 프로필 ===
    behavior_profile: BehaviorProfile

    # === 상태 ===
    visit_history: List[VisitRecord]   # 방문 기록
    last_active: datetime              # 마지막 활동
    total_sessions: int                # 총 세션 수
    total_pageviews: int               # 총 페이지뷰

    # === 메타데이터 ===
    created_at: datetime
    tags: List[str]                    # ["tech_lover", "shopping"]
```

### 3.2 BehaviorProfile

```python
@dataclass
class BehaviorProfile:
    """행동 특성 프로필 - 페르소나별 고유한 행동 패턴"""

    # === 스크롤 패턴 ===
    scroll_speed: float                # 0.5 (느림) ~ 2.0 (빠름)
    scroll_depth_preference: float     # 0.3 ~ 1.0 (얼마나 끝까지 읽는지)
    scroll_pause_frequency: float      # 0.1 ~ 0.4 (멈춤 빈도)

    # === 읽기 패턴 ===
    avg_dwell_time: int                # 평균 체류시간 (초) 60~300
    reading_style: str                 # "skimmer", "deep_reader", "scanner"

    # === 탭 패턴 ===
    tap_accuracy: float                # 0.85 ~ 0.98 (정확도)
    tap_speed: float                   # 0.8 ~ 1.2 (반응 속도)

    # === 세션 패턴 ===
    preferred_session_length: int      # 선호 세션 길이 (분) 3~15
    pages_per_session: int             # 세션당 페이지 수 2~8

    # === 시간 패턴 ===
    active_hours: List[int]            # 활동 시간대 [9,10,11,12,...]
    active_days: List[int]             # 활동 요일 [0,1,2,3,4] (월~금)
```

### 3.3 VisitRecord

```python
@dataclass
class VisitRecord:
    """방문 기록"""
    url: str
    domain: str                        # "blog.naver.com"
    content_type: str                  # "blog", "news", "shopping"
    timestamp: datetime
    dwell_time: int                    # 체류시간 (초)
    scroll_depth: float                # 0.0 ~ 1.0
    actions: List[str]                 # ["scroll", "click_link", "back"]
```

---

## 4. 핵심 컴포넌트

### 4.1 DeviceIdentityManager (루팅 필요)

```python
class DeviceIdentityManager:
    """
    루팅된 디바이스에서 ID 변경
    """

    async def apply_persona_identity(self, persona: Persona) -> bool:
        """페르소나의 디바이스 ID 적용"""

        # 1. ANDROID_ID 변경
        await self._set_android_id(persona.android_id)

        # 2. GSF ID 변경
        await self._set_gsf_id(persona.gsf_id)

        # 3. Advertising ID 변경
        await self._set_advertising_id(persona.advertising_id)

        return True

    async def _set_android_id(self, android_id: str):
        """
        ANDROID_ID 변경 (루팅 필요)

        경로: settings put secure android_id <value>
        """
        cmd = f"settings put secure android_id {android_id}"
        await self.adb.shell_as_root(cmd)

    async def _set_gsf_id(self, gsf_id: str):
        """
        GSF ID 변경 (루팅 필요)

        경로: /data/data/com.google.android.gsf/databases/gservices.db
        """
        db_path = "/data/data/com.google.android.gsf/databases/gservices.db"
        cmd = f'sqlite3 {db_path} "UPDATE main SET value=\'{gsf_id}\' WHERE name=\'android_id\'"'
        await self.adb.shell_as_root(cmd)
```

### 4.2 CookieStateManager (루팅 필요)

```python
class CookieStateManager:
    """
    페르소나별 쿠키 상태 관리

    Chrome 쿠키 저장 위치:
    /data/data/com.android.chrome/app_chrome/Default/Cookies (SQLite)
    """

    async def save_persona_cookies(self, persona: Persona) -> bool:
        """현재 Chrome 쿠키를 페르소나에 저장"""
        cookies = await self._extract_chrome_cookies()

        persona.nnb_cookie = cookies.get('NNB', '')
        # 기타 쿠키도 저장 가능

        return True

    async def restore_persona_cookies(self, persona: Persona) -> bool:
        """페르소나의 쿠키를 Chrome에 복원"""

        # Chrome 종료
        await self.adb.shell("am force-stop com.android.chrome")

        # 쿠키 주입
        await self._inject_chrome_cookie('NNB', persona.nnb_cookie, '.naver.com')

        return True

    async def _extract_chrome_cookies(self) -> Dict[str, str]:
        """Chrome 쿠키 추출 (루팅 필요)"""
        db_path = "/data/data/com.android.chrome/app_chrome/Default/Cookies"
        # SQLite 쿼리로 쿠키 추출
        cmd = f'sqlite3 {db_path} "SELECT name, value FROM cookies WHERE host_key LIKE \'%naver%\'"'
        result = await self.adb.shell_as_root(cmd)
        # 파싱...

    async def _inject_chrome_cookie(self, name: str, value: str, domain: str):
        """Chrome 쿠키 주입 (루팅 필요)"""
        db_path = "/data/data/com.android.chrome/app_chrome/Default/Cookies"
        # SQLite INSERT/UPDATE
```

### 4.3 PersonaStore

```python
class PersonaStore:
    """
    SQLite 기반 페르소나 저장소
    """

    def __init__(self, db_path: str = "data/personas.db"):
        self.db_path = db_path
        self._init_db()

    def create_persona(self, name: str, tags: List[str] = None) -> Persona:
        """새 페르소나 생성 (랜덤 ID 부여)"""
        persona = Persona(
            persona_id=str(uuid.uuid4()),
            name=name,
            android_id=self._generate_android_id(),
            gsf_id=self._generate_gsf_id(),
            advertising_id=str(uuid.uuid4()),
            nnb_cookie="",  # 첫 방문 시 자동 생성됨
            behavior_profile=self._generate_random_profile(),
            visit_history=[],
            last_active=datetime.now(),
            total_sessions=0,
            total_pageviews=0,
            created_at=datetime.now(),
            tags=tags or []
        )
        self._save(persona)
        return persona

    def select_persona(self, strategy: str = "least_recent") -> Persona:
        """
        페르소나 선택 전략

        - least_recent: 가장 오래 활동 안 한 페르소나
        - round_robin: 순차 선택
        - random: 랜덤 선택
        - needs_revisit: 재방문이 필요한 페르소나
        """
        if strategy == "least_recent":
            return self._get_least_recent()
        elif strategy == "round_robin":
            return self._get_next_round_robin()
        elif strategy == "random":
            return self._get_random()
        elif strategy == "needs_revisit":
            return self._get_needs_revisit()

    def _generate_android_id(self) -> str:
        """16자 hex ANDROID_ID 생성"""
        return ''.join(random.choices('0123456789abcdef', k=16))

    def _generate_random_profile(self) -> BehaviorProfile:
        """랜덤 행동 프로필 생성"""
        return BehaviorProfile(
            scroll_speed=random.uniform(0.7, 1.5),
            scroll_depth_preference=random.uniform(0.4, 0.9),
            scroll_pause_frequency=random.uniform(0.1, 0.3),
            avg_dwell_time=random.randint(90, 240),
            reading_style=random.choice(["skimmer", "deep_reader", "scanner"]),
            tap_accuracy=random.uniform(0.88, 0.96),
            tap_speed=random.uniform(0.9, 1.1),
            preferred_session_length=random.randint(5, 12),
            pages_per_session=random.randint(3, 6),
            active_hours=sorted(random.sample(range(9, 22), 6)),
            active_days=sorted(random.sample(range(7), 5))
        )
```

### 4.4 PortalClient

```python
class PortalClient:
    """
    DroidRun Portal APK HTTP 클라이언트

    Portal APK는 디바이스에서 실행되며:
    - UI Hierarchy 제공
    - 스크린샷 제공
    - 요소 정보 제공
    """

    def __init__(self, host: str = "localhost", port: int = 8080):
        self.base_url = f"http://{host}:{port}"

    async def get_ui_hierarchy(self) -> UITree:
        """UI 트리 획득"""
        response = await self._get("/hierarchy")
        return UITree.from_json(response)

    async def get_screenshot(self) -> bytes:
        """스크린샷 획득"""
        return await self._get_binary("/screenshot")

    async def find_element(self, **criteria) -> Optional[UIElement]:
        """요소 검색"""
        tree = await self.get_ui_hierarchy()
        return tree.find(**criteria)

    async def find_elements(self, **criteria) -> List[UIElement]:
        """복수 요소 검색"""
        tree = await self.get_ui_hierarchy()
        return tree.find_all(**criteria)


class ElementFinder:
    """요소 검색 헬퍼"""

    def __init__(self, portal: PortalClient):
        self.portal = portal

    async def find_by_text(self, text: str, exact: bool = False) -> Optional[UIElement]:
        """텍스트로 요소 검색"""
        tree = await self.portal.get_ui_hierarchy()
        if exact:
            return tree.find(text=text)
        return tree.find(text_contains=text)

    async def find_clickable(self, text_contains: str = None) -> List[UIElement]:
        """클릭 가능한 요소 검색"""
        tree = await self.portal.get_ui_hierarchy()
        return tree.find_all(clickable=True, text_contains=text_contains)

    async def find_search_results(self) -> List[UIElement]:
        """네이버 검색 결과 요소 검색"""
        return await self.find_clickable(text_contains=None)
```

---

## 5. 통합 플로우

### 5.1 완전한 세션 플로우

```
1. 페르소나 선택
   +-----------------------------------------------------+
   | persona = store.select_persona("least_recent")      |
   | # 가장 오래 활동 안 한 페르소나 선택                 |
   +-----------------------------------------------------+
                          |
                          v
2. 디바이스 ID 적용 (루팅)
   +-----------------------------------------------------+
   | DeviceIdentityManager.apply_persona_identity()      |
   | # ANDROID_ID, GSF_ID 변경                           |
   | # 네이버 입장: 이 디바이스 식별자 알겠어            |
   +-----------------------------------------------------+
                          |
                          v
3. 쿠키 복원 (루팅)
   +-----------------------------------------------------+
   | CookieStateManager.restore_persona_cookies()        |
   | # NNB 쿠키 주입                                     |
   | # 네이버 입장: 아, 이 사람 전에 왔었네!             |
   +-----------------------------------------------------+
                          |
                          v
4. Chrome 실행 + Portal로 UI 감지
   +-----------------------------------------------------+
   | adb.open_url("https://search.naver.com/...")        |
   | elements = portal.find_elements(clickable=True)     |
   | # 정확한 요소 위치 파악                             |
   +-----------------------------------------------------+
                          |
                          v
5. 페르소나 프로필 기반 행동
   +-----------------------------------------------------+
   | profile = persona.behavior_profile                  |
   | tools = EnhancedAdbTools(config)                    |
   | tools.behavior_profile = profile                    |
   |                                                     |
   | # 이 페르소나 특유의 스크롤 속도/패턴 적용          |
   | await tools.tap(element.bounds.center)              |
   | await tools.scroll_down(speed=profile.scroll_speed) |
   +-----------------------------------------------------+
                          |
                          v
6. 방문 기록 & 상태 저장
   +-----------------------------------------------------+
   | persona.visit_history.append(record)                |
   | CookieStateManager.save_persona_cookies()           |
   | store.update(persona)                               |
   |                                                     |
   | # 다음 방문 시 연속성 유지                          |
   +-----------------------------------------------------+
```

---

## 6. 효과 예측

| 지표 | 기존 (매번 새 사용자) | 신규 (페르소나) |
|------|---------------------|----------------|
| 재방문율 | 0% | 30-60% (조절 가능) |
| 사용자 일관성 | 없음 | 높음 |
| 네이버 품질 점수 | 낮음 (의심) | 정상 |
| 탐지 위험 | 중간 (패턴 탐지) | 낮음 (자연스러움) |
| 루팅 필요 | 불필요 | **필요** |

---

## 7. 구현 우선순위

### Phase 2.5: Portal 통합 (루팅 불필요)
1. DroidRun Portal APK 설치 및 테스트
2. PortalClient 구현
3. ElementFinder 구현
4. EngagementSimulator + Portal 연동

### Phase 3: Persona 시스템 (루팅 필요)
1. Persona 데이터 구조 구현
2. PersonaStore (SQLite) 구현
3. DeviceIdentityManager 구현 (루팅 테스트)
4. CookieStateManager 구현 (루팅 테스트)
5. 전체 플로우 통합 테스트

---

## 8. 테스트 계획

### 8.1 루팅 테스트 (Galaxy Tab)
```bash
# 1. 현재 ANDROID_ID 확인
adb shell settings get secure android_id

# 2. ANDROID_ID 변경 시도
adb shell su -c "settings put secure android_id abc123def456789"

# 3. 변경 확인
adb shell settings get secure android_id

# 4. Chrome 쿠키 DB 접근 테스트
adb shell su -c "ls -la /data/data/com.android.chrome/app_chrome/Default/"
```

### 8.2 Portal APK 테스트
```bash
# 1. Portal APK 설치
adb install droidrun-portal.apk

# 2. Portal 서비스 시작
adb shell am start -n com.droidrun.portal/.MainActivity

# 3. ADB 포트 포워딩
adb forward tcp:8080 tcp:8080

# 4. API 테스트
curl http://localhost:8080/hierarchy
```

---

## 9. 참고 문서

- [시스템 아키텍처](ARCHITECTURE.md)
- [DroidRun 통합 가이드](DROIDRUN_INTEGRATION.md)
- [핑거프린트 실험 결과](../experiments/fingerprint_capture/FINDINGS.md)

---

*마지막 업데이트: 2025-12-15*
