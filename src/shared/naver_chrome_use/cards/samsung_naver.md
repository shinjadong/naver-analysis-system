# Samsung Internet + Naver 브라우저 카드

> Samsung Internet 브라우저를 통한 네이버 서비스 자동화 명세

## Package Info

- **Package Name**: `com.sec.android.app.sbrowser`
- **Main Activity**: `.SBrowserMainActivity`
- **우선순위**: 2 (삼성 기기에서 사용)

## 실행 명령어 (ADB Intent)

### 기본 실행
```bash
am start -n com.sec.android.app.sbrowser/.SBrowserMainActivity
```

### URL 직접 열기
```bash
# 네이버 홈
am start -a android.intent.action.VIEW -d 'https://m.naver.com' com.sec.android.app.sbrowser

# 네이버 블로그
am start -a android.intent.action.VIEW -d 'https://m.blog.naver.com' com.sec.android.app.sbrowser

# 네이버 쇼핑
am start -a android.intent.action.VIEW -d 'https://msearch.shopping.naver.com' com.sec.android.app.sbrowser
```

### 검색 URL
```bash
# 통합 검색
am start -a android.intent.action.VIEW -d 'https://search.naver.com/search.naver?query={검색어}' com.sec.android.app.sbrowser

# 블로그 검색
am start -a android.intent.action.VIEW -d 'https://search.naver.com/search.naver?where=blog&query={검색어}' com.sec.android.app.sbrowser

# 뉴스 검색
am start -a android.intent.action.VIEW -d 'https://search.naver.com/search.naver?where=news&query={검색어}' com.sec.android.app.sbrowser
```

## UI 요소 좌표 (1080x2400 기준)

| 요소 | X | Y | 용도 |
|-----|---|---|------|
| 주소창 | 540 | 130 | URL 입력 |
| 뒤로가기 | 120 | 2300 | 이전 페이지 |
| 홈 버튼 | 540 | 2300 | 홈으로 |
| 탭 버튼 | 900 | 2300 | 탭 관리 |
| 메뉴 버튼 | 980 | 2300 | 브라우저 메뉴 |

### 네이버 페이지 내 요소

| 요소 | X | Y | 용도 |
|-----|---|---|------|
| 검색창 (홈) | 540 | 180 | 검색 시작 |
| 검색창 (결과) | 540 | 130 | 재검색 |
| 첫 번째 결과 | 540 | 700 | 결과 클릭 |
| 블로그 탭 | 650 | 350 | 탭 전환 |
| 뉴스 탭 | 450 | 350 | 탭 전환 |

## 스크롤 패턴

```python
# 기본 스크롤 (콘텐츠 탐색)
swipe(540, 1800, 540, 800, 500)

# 느린 스크롤 (읽기)
swipe(540, 1600, 540, 1000, 800)

# 빠른 스크롤 (스킵)
swipe(540, 1800, 540, 500, 300)

# 위로 스크롤 (다시 보기)
swipe(540, 800, 540, 1500, 500)
```

## 탐지 회피 설정

```yaml
stealth_config:
  search_method: "url_direct"       # URL 직접 열기
  scroll_speed_variance: 0.3        # ±30% 속도 변화
  scroll_pause_probability: 0.15    # 15% 멈춤 확률
  tap_offset_max: 15                # 최대 15px 오프셋
  tap_duration_range: [50, 150]     # 탭 지속시간 범위
  page_load_wait: [2.0, 4.0]        # 페이지 로드 대기
  action_interval: [0.5, 1.5]       # 액션 간 간격
```

## Chrome과의 차이점

| 항목 | Chrome | Samsung Internet |
|-----|--------|-----------------|
| 하단 UI | 없음 | 네비게이션 바 있음 |
| 뒤로가기 위치 | 상단 좌측 (60, 130) | 하단 좌측 (120, 2300) |
| 공유 버튼 | 상단 우측 | 메뉴 내부 |
| 시크릿 모드 | Intent 파라미터 | Secret Mode 탭 전환 필요 |

## 공유 기능 사용

Samsung Internet에서 공유 기능은 메뉴를 통해 접근:

```python
# 1. 메뉴 버튼 클릭
tap(980, 2300)
wait(0.5)

# 2. 공유 버튼 클릭 (메뉴 내)
tap_by_text("공유")  # 또는 좌표 사용
wait(0.5)

# 3. URL 복사 선택
tap_by_text("URL 복사")
```

## 특이사항

- 하단 네비게이션 바 존재
- 공유 버튼이 메뉴 내부에 위치
- 삼성 패스 지원 (자동 로그인)
- 광고 차단 기능 내장
