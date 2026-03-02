# NaverChromeUse - 크롬 브라우저 기반 네이버 자동화 명세서

> **작성일**: 2025-12-14
> **기반**: DroidRun 앱 카드 시스템
> **목적**: Chrome 브라우저를 통한 네이버 서비스 자동화
> **핵심 원칙**: 디바이스 루팅 불필요, 브라우저 레벨 자동화

---

## 1. 개요

### 1.1 NaverChromeUse란?

NaverChromeUse는 **Chrome 브라우저를 통해 네이버 서비스에 접속하는 자동화 패턴**입니다.

**왜 Chrome 기반인가?**
- 네이티브 네이버 앱(com.nhn.android.search)은 탐지가 더 엄격함
- Chrome은 범용 브라우저로서 자동화 탐지 우회가 용이
- 디바이스 루팅 없이 ADB 레벨에서 충분히 제어 가능
- 쿠키/세션 관리가 표준 웹 방식으로 동작

**핵심 구성요소**:
- **ADB Intent 명령어**: URL 직접 열기, 검색 등
- **UI 요소 좌표**: 해상도별 주요 UI 요소 위치
- **워크플로우 패턴**: 자연스러운 사용 흐름
- **탐지 회피 설정**: BehaviorInjector 연동 파라미터

### 1.2 지원 브라우저

| 브라우저 | 패키지명 | 우선순위 | 상태 |
|---------|---------|---------|------|
| Chrome | `com.android.chrome` | 1순위 (기본) | 완료 |
| Samsung Internet | `com.sec.android.app.sbrowser` | 2순위 (삼성 기기) | 완료 |
| Edge | `com.microsoft.emmx` | 3순위 (대안) | 계획 |

> **참고**: 네이티브 네이버 앱(com.nhn.android.search)은 사용하지 않음

---

## 2. Chrome + 네이버 명세 (Primary)

### 2.1 기본 정보

```yaml
package_name: com.android.chrome
main_activity: com.google.android.apps.chrome.Main
naver_domains:
  - m.naver.com          # 모바일 홈
  - search.naver.com     # 검색
  - m.blog.naver.com     # 블로그
  - m.cafe.naver.com     # 카페
  - msearch.shopping.naver.com  # 쇼핑
```

### 2.2 실행 명령어 (ADB Intent)

#### 기본 실행
```bash
am start -n com.android.chrome/com.google.android.apps.chrome.Main
```

#### URL 직접 열기 (권장)
```bash
# 네이버 모바일 홈
am start -a android.intent.action.VIEW -d 'https://m.naver.com' com.android.chrome

# 네이버 블로그 홈
am start -a android.intent.action.VIEW -d 'https://m.blog.naver.com' com.android.chrome

# 네이버 카페 홈
am start -a android.intent.action.VIEW -d 'https://m.cafe.naver.com' com.android.chrome

# 네이버 쇼핑 홈
am start -a android.intent.action.VIEW -d 'https://msearch.shopping.naver.com' com.android.chrome
```

#### 검색 URL (검색창 입력 대신 사용)
```bash
# 통합 검색
am start -a android.intent.action.VIEW \
  -d 'https://search.naver.com/search.naver?query={검색어}' \
  com.android.chrome

# 블로그 검색
am start -a android.intent.action.VIEW \
  -d 'https://search.naver.com/search.naver?where=blog&query={검색어}' \
  com.android.chrome

# 뉴스 검색
am start -a android.intent.action.VIEW \
  -d 'https://search.naver.com/search.naver?where=news&query={검색어}' \
  com.android.chrome

# 이미지 검색
am start -a android.intent.action.VIEW \
  -d 'https://search.naver.com/search.naver?where=image&query={검색어}' \
  com.android.chrome

# 쇼핑 검색
am start -a android.intent.action.VIEW \
  -d 'https://msearch.shopping.naver.com/search/all?query={검색어}' \
  com.android.chrome
```

#### 시크릿 모드 (세션 격리)
```bash
am start -a android.intent.action.VIEW \
  -d 'https://m.naver.com' \
  --ez create_new_tab true \
  --ez incognito true \
  com.android.chrome
```

### 2.3 UI 요소 좌표 (1080x2400 기준)

| 요소 | X | Y | 용도 |
|-----|---|---|------|
| 검색창 (네이버 홈) | 540 | 180 | 검색 시작 |
| 검색창 (검색 결과) | 540 | 130 | 재검색 |
| 첫 번째 검색 결과 | 540 | 700 | 결과 클릭 |
| 블로그 탭 | 650 | 350 | 탭 전환 |
| 뉴스 탭 | 450 | 350 | 탭 전환 |
| 이미지 탭 | 250 | 350 | 탭 전환 |
| 뒤로가기 (Chrome) | 60 | 130 | 네비게이션 |
| 공유 버튼 | 980 | 130 | 공유 메뉴 |
| Chrome 주소창 | 540 | 80 | URL 입력 |
| Chrome 탭 버튼 | 920 | 80 | 탭 관리 |
| Chrome 메뉴 | 1020 | 80 | 브라우저 메뉴 |

### 2.4 해상도별 좌표 변환

| 해상도 | 기기 예시 | 변환 비율 |
|--------|----------|----------|
| 1080x2400 | Galaxy S21, Pixel 6 | 기준 (1.0x) |
| 1080x2340 | Galaxy A52 | Y: 0.975x |
| 1440x3200 | Galaxy S21 Ultra | 1.33x |
| 720x1560 | 저가형 | 0.67x |

**좌표 변환 공식**:
```python
def convert_coordinates(base_x, base_y, target_width, target_height):
    target_x = base_x * (target_width / 1080)
    target_y = base_y * (target_height / 2400)
    return int(target_x), int(target_y)
```

### 2.5 스크롤 패턴

```python
# 기본 스크롤 (아래로) - 콘텐츠 탐색
swipe(540, 1800, 540, 800, 500)

# 느린 스크롤 (콘텐츠 읽기) - 체류시간 확보
swipe(540, 1600, 540, 1000, 800)

# 빠른 스크롤 (스킵) - 관심 없는 콘텐츠
swipe(540, 1800, 540, 500, 300)

# 위로 스크롤 (다시 보기) - 자연스러운 행동
swipe(540, 800, 540, 1500, 500)

# 좌우 스크롤 (탭 전환/캐러셀)
swipe(800, 350, 300, 350, 300)
```

---

## 3. BehaviorInjector 연동 설정

### 3.1 탐지 회피 설정

```yaml
naver_chrome_use_stealth:
  # 검색 방식
  search_method: "url_direct"  # URL 직접 열기 (권장)
  # Alternative: "input_box" (검색창 타이핑)

  # 스크롤 패턴
  scroll_speed_variance: 0.3      # ±30% 속도 변화
  scroll_pause_probability: 0.15  # 15% 확률로 멈춤
  scroll_pause_duration: [0.5, 2.0]  # 멈춤 시간 범위
  scroll_overshoot: true          # 스크롤 오버슈트 효과

  # 탭 패턴
  tap_offset_max: 15              # 최대 오프셋 (px)
  tap_duration_range: [50, 150]   # 탭 지속시간 (ms)
  tap_pressure_variance: 0.2      # 압력 변화

  # 타이밍
  page_load_wait: [2.0, 4.0]      # 페이지 로드 대기
  action_interval: [0.5, 1.5]     # 액션 간 간격
  reading_time_per_scroll: [1.0, 3.0]  # 스크롤당 읽기 시간

  # 세션 패턴
  session_duration: [180, 600]    # 3-10분 세션
  page_transitions: [3, 15]       # 페이지 전환 수
```

### 3.2 BehaviorInjector 적용 예시

```python
from shared.device_tools import BehaviorInjector, EnhancedAdbTools

# 스텔스 모드 인젝터 생성
injector = BehaviorInjector.create_stealth()

# EnhancedAdbTools와 연동
adb = EnhancedAdbTools(
    device_id="emulator-5554",
    behavior_injector=injector
)

# 자연스러운 탭 (오프셋 + 압력 변화 자동 적용)
await adb.tap(540, 700)

# 가변 속도 스크롤 (베지어 커브 적용)
await adb.swipe(540, 1600, 540, 800, style=ScrollStyle.NATURAL)

# 인간적인 타이핑 (오타 + 지연 자동 적용)
await adb.input_text("네이버 검색어")
```

---

## 4. 워크플로우 패턴

### 4.1 블로그 검색 → 글 읽기 워크플로우

```python
async def naver_chrome_blog_workflow(adb: EnhancedAdbTools, keyword: str):
    """
    Chrome에서 네이버 블로그 검색 후 글 읽기

    Args:
        adb: EnhancedAdbTools 인스턴스
        keyword: 검색 키워드
    """
    import random

    # 1. 블로그 검색 결과 바로 열기 (URL 직접 방식)
    search_url = f"https://search.naver.com/search.naver?where=blog&query={keyword}"
    await adb.open_url(search_url, package="com.android.chrome")
    await asyncio.sleep(random.uniform(2.5, 4.0))

    # 2. 첫 번째 블로그 글 클릭
    await adb.tap(540, 700)
    await asyncio.sleep(random.uniform(2.0, 3.5))

    # 3. 콘텐츠 읽기 (자연스러운 스크롤)
    scroll_count = random.randint(5, 8)
    for i in range(scroll_count):
        # 가변 거리/속도 스크롤
        distance = random.randint(400, 700)
        duration = random.randint(500, 800)

        await adb.swipe(
            540, 1600,
            540, 1600 - distance,
            duration,
            style=ScrollStyle.NATURAL
        )

        # 읽기 시간
        await asyncio.sleep(random.uniform(1.0, 3.5))

        # 가끔 위로 살짝 (다시 보기 패턴)
        if random.random() < 0.2:
            await adb.swipe(540, 1000, 540, 1200, 400)
            await asyncio.sleep(random.uniform(0.5, 1.5))

    # 4. 뒤로가기
    await adb.tap(60, 130)

    return {"status": "success", "scrolls": scroll_count}
```

### 4.2 쇼핑 검색 → 상품 탐색 워크플로우

```python
async def naver_chrome_shopping_workflow(adb: EnhancedAdbTools, keyword: str):
    """
    Chrome에서 네이버 쇼핑 검색 후 상품 탐색
    """
    import random

    # 1. 쇼핑 검색 URL 열기
    search_url = f"https://msearch.shopping.naver.com/search/all?query={keyword}"
    await adb.open_url(search_url, package="com.android.chrome")
    await asyncio.sleep(random.uniform(2.5, 4.0))

    # 2. 상품 목록 스크롤
    products_viewed = 0
    for _ in range(random.randint(3, 6)):
        await adb.swipe(540, 1600, 540, 900, random.randint(400, 600))
        await asyncio.sleep(random.uniform(1.5, 3.0))
        products_viewed += 3  # 대략 3개 상품이 보임

    # 3. 상품 클릭 (관심 상품)
    product_positions = [700, 1100, 1500]  # 상품 Y 좌표 예시
    target_y = random.choice(product_positions)

    await adb.tap(540, target_y)
    await asyncio.sleep(random.uniform(2.0, 3.0))

    # 4. 상품 상세 스크롤
    for _ in range(random.randint(3, 5)):
        await adb.swipe(540, 1600, 540, 800, random.randint(500, 700))
        await asyncio.sleep(random.uniform(1.0, 2.5))

    # 5. 뒤로가기
    await adb.tap(60, 130)

    return {"status": "success", "products_viewed": products_viewed}
```

### 4.3 뉴스 검색 → 기사 읽기 워크플로우

```python
async def naver_chrome_news_workflow(adb: EnhancedAdbTools, keyword: str):
    """
    Chrome에서 네이버 뉴스 검색 후 기사 읽기
    """
    import random

    # 1. 뉴스 검색 URL 열기
    search_url = f"https://search.naver.com/search.naver?where=news&query={keyword}"
    await adb.open_url(search_url, package="com.android.chrome")
    await asyncio.sleep(random.uniform(2.5, 4.0))

    articles_read = 0

    # 2. 뉴스 목록에서 기사 선택 (1-3개)
    for _ in range(random.randint(1, 3)):
        # 기사 클릭
        article_y = random.choice([700, 1000, 1300])
        await adb.tap(540, article_y)
        await asyncio.sleep(random.uniform(2.0, 3.5))

        # 기사 읽기
        for _ in range(random.randint(3, 6)):
            await adb.swipe(540, 1600, 540, 900, random.randint(400, 600))
            await asyncio.sleep(random.uniform(1.5, 4.0))  # 뉴스는 읽기 시간 더 김

        articles_read += 1

        # 뒤로가기
        await adb.tap(60, 130)
        await asyncio.sleep(random.uniform(1.0, 2.0))

        # 목록에서 스크롤
        await adb.swipe(540, 1400, 540, 900, 500)
        await asyncio.sleep(random.uniform(0.5, 1.5))

    return {"status": "success", "articles_read": articles_read}
```

---

## 5. 네이버 쿠키/세션 관리

### 5.1 주요 쿠키

| 쿠키 | 필수 | 용도 | 관리 방법 |
|-----|------|------|----------|
| NNB | 필수 | 디바이스 식별 | 자동 생성, 유지 |
| NID | 로그인 시 | 사용자 프로파일 | 로그인 후 유지 |
| SRT5 | 필수 | 5분 세션 | 자동 갱신 |
| SRT30 | 필수 | 30분 세션 | 자동 갱신 |
| page_uid | 필수 | 페이지 식별 | 페이지마다 변경 |

### 5.2 Chrome 쿠키 접근

Chrome 쿠키는 ADB를 통해 직접 접근이 어려우므로, 다음 전략 사용:

1. **정상적인 브라우징으로 쿠키 생성**: URL 방문 시 자동 생성
2. **시크릿 모드로 세션 격리**: 테스트 간 간섭 방지
3. **세션 유지**: 적절한 간격으로 페이지 재방문

```python
async def ensure_session_cookies(adb: EnhancedAdbTools):
    """
    네이버 세션 쿠키가 생성되도록 홈페이지 방문
    """
    # 네이버 홈 방문 (쿠키 생성)
    await adb.open_url("https://m.naver.com", package="com.android.chrome")
    await asyncio.sleep(3.0)  # 쿠키 생성 대기

    # 간단한 상호작용 (세션 활성화)
    await adb.swipe(540, 1200, 540, 800, 500)
    await asyncio.sleep(1.0)

    return True
```

---

## 6. Samsung Internet 지원 (Secondary)

### 6.1 기본 정보

```yaml
package_name: com.sec.android.app.sbrowser
main_activity: .SBrowserMainActivity
features:
  - 삼성 기기 기본 브라우저
  - 삼성 패스 지원
  - 광고 차단 내장
```

### 6.2 실행 명령어

```bash
# 기본 실행
am start -n com.sec.android.app.sbrowser/.SBrowserMainActivity

# URL 직접 열기
am start -a android.intent.action.VIEW \
  -d 'https://m.naver.com' \
  com.sec.android.app.sbrowser

# 블로그 검색
am start -a android.intent.action.VIEW \
  -d 'https://search.naver.com/search.naver?where=blog&query={검색어}' \
  com.sec.android.app.sbrowser
```

### 6.3 UI 요소 차이점 (Chrome 대비)

| 요소 | Chrome | Samsung Internet |
|-----|--------|-----------------|
| 하단 UI | 없음 | 네비게이션 바 있음 |
| 홈 버튼 위치 | 없음 | 540, 2300 |
| 뒤로가기 | 60, 130 | 120, 2300 |
| 공유 버튼 | 980, 130 | 메뉴 내부 |
| 탭 버튼 | 920, 80 | 900, 2300 |
| 메뉴 버튼 | 1020, 80 | 980, 2300 |

### 6.4 Samsung Internet 워크플로우

```python
async def naver_samsung_blog_workflow(adb: EnhancedAdbTools, keyword: str):
    """
    Samsung Internet에서 네이버 블로그 검색
    """
    import random

    # Samsung Internet으로 URL 열기
    search_url = f"https://search.naver.com/search.naver?where=blog&query={keyword}"
    await adb.open_url(search_url, package="com.sec.android.app.sbrowser")
    await asyncio.sleep(random.uniform(2.5, 4.0))

    # 블로그 글 클릭
    await adb.tap(540, 700)
    await asyncio.sleep(random.uniform(2.0, 3.0))

    # 콘텐츠 읽기
    for _ in range(random.randint(4, 6)):
        await adb.swipe(540, 1600, 540, 1000, random.randint(500, 700))
        await asyncio.sleep(random.uniform(1.0, 2.5))

    # 뒤로가기 (하단 버튼)
    await adb.tap(120, 2300)

    return {"status": "success"}
```

---

## 7. 브라우저 선택 로직

### 7.1 자동 브라우저 선택

```python
class NaverChromeUseProvider:
    """NaverChromeUse 브라우저 제공자"""

    BROWSER_PRIORITY = [
        ("com.android.chrome", "Chrome"),
        ("com.sec.android.app.sbrowser", "Samsung Internet"),
        ("com.microsoft.emmx", "Edge"),
    ]

    async def get_available_browser(self, adb: EnhancedAdbTools) -> str:
        """
        설치된 브라우저 중 우선순위가 높은 것 반환
        """
        for package, name in self.BROWSER_PRIORITY:
            result = await adb.shell(f"pm list packages | grep {package}")
            if package in result.output:
                return package

        raise RuntimeError("지원되는 브라우저가 설치되어 있지 않음")

    def get_ui_config(self, package: str) -> dict:
        """
        브라우저별 UI 설정 반환
        """
        configs = {
            "com.android.chrome": {
                "back_button": (60, 130),
                "share_button": (980, 130),
                "has_bottom_nav": False,
            },
            "com.sec.android.app.sbrowser": {
                "back_button": (120, 2300),
                "share_button": None,  # 메뉴 통해 접근
                "has_bottom_nav": True,
            },
        }
        return configs.get(package, configs["com.android.chrome"])
```

---

## 8. 네이버 URL 패턴 참조

### 8.1 서비스별 URL

| 서비스 | 모바일 URL | 검색 파라미터 |
|-------|-----------|-------------|
| 홈 | m.naver.com | - |
| 통합검색 | search.naver.com/search.naver | ?query= |
| 블로그 | m.blog.naver.com | - |
| 블로그 검색 | search.naver.com/search.naver | ?where=blog&query= |
| 뉴스 검색 | search.naver.com/search.naver | ?where=news&query= |
| 이미지 검색 | search.naver.com/search.naver | ?where=image&query= |
| 쇼핑 | msearch.shopping.naver.com | ?query= |
| 카페 | m.cafe.naver.com | - |
| 지도 | m.map.naver.com | ?query= |

### 8.2 URL 생성 헬퍼

```python
class NaverUrlBuilder:
    """네이버 URL 생성 헬퍼"""

    BASE_SEARCH = "https://search.naver.com/search.naver"
    BASE_SHOPPING = "https://msearch.shopping.naver.com/search/all"
    BASE_HOME = "https://m.naver.com"
    BASE_BLOG = "https://m.blog.naver.com"
    BASE_CAFE = "https://m.cafe.naver.com"

    @staticmethod
    def search(query: str, category: str = "all") -> str:
        """검색 URL 생성"""
        from urllib.parse import quote
        encoded = quote(query)

        if category == "blog":
            return f"{NaverUrlBuilder.BASE_SEARCH}?where=blog&query={encoded}"
        elif category == "news":
            return f"{NaverUrlBuilder.BASE_SEARCH}?where=news&query={encoded}"
        elif category == "image":
            return f"{NaverUrlBuilder.BASE_SEARCH}?where=image&query={encoded}"
        elif category == "shopping":
            return f"{NaverUrlBuilder.BASE_SHOPPING}?query={encoded}"
        else:
            return f"{NaverUrlBuilder.BASE_SEARCH}?query={encoded}"
```

---

## 9. 관련 문서

- [DroidRun 통합 가이드](DROIDRUN_INTEGRATION.md)
- [에이전트 아키텍처](AGENT_ARCHITECTURE.md)
- [네이버 추적 시스템 분석](../analysis/naver_complete_analysis.md)

---

*마지막 업데이트: 2025-12-14*
*명명 규칙: NaverChromeUse (네이버 네이티브 앱 미사용)*
