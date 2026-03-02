# Chrome + Naver 브라우저 카드

> Chrome 브라우저를 통한 네이버 서비스 자동화 명세

## Package Info

- **Package Name**: `com.android.chrome`
- **Main Activity**: `com.google.android.apps.chrome.Main`
- **우선순위**: 1 (기본 브라우저)

## 실행 명령어 (ADB Intent)

### 기본 실행
```bash
am start -n com.android.chrome/com.google.android.apps.chrome.Main
```

### URL 직접 열기
```bash
# 네이버 홈
am start -a android.intent.action.VIEW -d 'https://m.naver.com' com.android.chrome

# 네이버 블로그
am start -a android.intent.action.VIEW -d 'https://m.blog.naver.com' com.android.chrome

# 네이버 쇼핑
am start -a android.intent.action.VIEW -d 'https://msearch.shopping.naver.com' com.android.chrome
```

### 검색 URL
```bash
# 통합 검색
am start -a android.intent.action.VIEW -d 'https://search.naver.com/search.naver?query={검색어}' com.android.chrome

# 블로그 검색
am start -a android.intent.action.VIEW -d 'https://search.naver.com/search.naver?where=blog&query={검색어}' com.android.chrome

# 뉴스 검색
am start -a android.intent.action.VIEW -d 'https://search.naver.com/search.naver?where=news&query={검색어}' com.android.chrome

# 쇼핑 검색
am start -a android.intent.action.VIEW -d 'https://msearch.shopping.naver.com/search/all?query={검색어}' com.android.chrome
```

### 시크릿 모드
```bash
am start -a android.intent.action.VIEW -d 'https://m.naver.com' --ez create_new_tab true --ez incognito true com.android.chrome
```

## UI 요소 좌표 (1080x2400 기준)

| 요소 | X | Y | 용도 |
|-----|---|---|------|
| 뒤로가기 | 60 | 130 | 이전 페이지 |
| 공유 버튼 | 980 | 130 | 공유 메뉴 |
| 주소창 | 540 | 80 | URL 입력 |
| 탭 버튼 | 920 | 80 | 탭 관리 |
| 메뉴 버튼 | 1020 | 80 | Chrome 메뉴 |

### 네이버 페이지 내 요소

| 요소 | X | Y | 용도 |
|-----|---|---|------|
| 검색창 (홈) | 540 | 180 | 검색 시작 |
| 검색창 (결과) | 540 | 130 | 재검색 |
| 첫 번째 결과 | 540 | 700 | 결과 클릭 |
| 블로그 탭 | 650 | 350 | 탭 전환 |
| 뉴스 탭 | 450 | 350 | 탭 전환 |
| 이미지 탭 | 250 | 350 | 탭 전환 |

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
  search_method: "url_direct"       # URL 직접 열기 (검색창 입력 대신)
  scroll_speed_variance: 0.3        # ±30% 속도 변화
  scroll_pause_probability: 0.15    # 15% 멈춤 확률
  tap_offset_max: 15                # 최대 15px 오프셋
  tap_duration_range: [50, 150]     # 탭 지속시간 범위
  page_load_wait: [2.0, 4.0]        # 페이지 로드 대기
  action_interval: [0.5, 1.5]       # 액션 간 간격
```

## 특이사항

- 하단 네비게이션 바 없음
- 공유 버튼이 상단에 위치
- 시크릿 모드 Intent 파라미터 지원
