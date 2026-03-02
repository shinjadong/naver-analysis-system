# 블로그 트래픽 부스팅 전략

> **작성일**: 2026-02-06
> **기반 데이터**: NAVER_TRACKING_ANALYSIS.md, FINDINGS.md, root_vs_browser_analysis.md
> **목적**: 신규 발행 블로그 원고의 검색 노출 및 트래픽 부스팅

---

## 1. 현재 상황

- 블로그 원고 발행 후 2일 미만
- 타겟 키워드/제목으로 검색 시 네이버 검색결과 어디에도 미노출
- 1,000개 페르소나 (디바이스 ID, 위치, 행동 프로필) 준비 완료
- 루팅 Android + 휴먼라이크 ADB 자동화 (베지어 커브, 체류시간) 구현 완료

---

## 2. 네이버 검색 유입 시그널 체인

### 2.1 정상 검색 유입 흐름 (캡처 데이터 확인)

```
① 검색어 입력
   mac.search.naver.com/mobile/ac          ← 자동완성 API

② 검색결과 로딩
   m.search.naver.com/search.naver?query=  ← 결과 페이지
   nlog.naver.com/n                         ← 검색 이벤트 기록
   tqi={검색세션ID}                         ← 서버사이드 발급

③ 검색결과 스크롤
   l.search.naver.com/n/scrolllog/v2        ← 스크롤 위치 추적

④ 결과 클릭 (핵심 시그널)
   m.search.naver.com/p/crd/rd?...          ← 클릭 리디렉트 ⭐
   파라미터: tqi, 클릭 위치, 노출 순위, 검색어

⑤ 블로그 도착
   blog.naver.com/PostViewVisitRecord       ← 방문 기록
   tivan.naver.com/sc2/1                    ← 행동 추적 시작
```

### 2.2 핵심 제약

- `crd/rd` 리디렉트는 **검색결과에 노출되어야만 발생**
- `tqi`(검색 세션 ID)는 서버사이드 발급 → 임의 생성 불가
- 검색결과 페이지 렌더링 시 각 결과 링크에 고유 crd/rd URL 삽입

### 2.3 직접 방문 시 유입 소스

```
검색결과에서 클릭 → crd/rd 리디렉트 → "검색 유입" ✅
URL 직접 입력     → crd/rd 미발생   → "직접 유입(Direct)" ⚠️
```

---

## 3. 세션 수집 메커니즘

### 3.1 새 탭 vs 새 세션 vs 새 사용자

| 행동 | NNB (디바이스ID) | IV (세션UUID) | SRT5/30 | page_uid | 네이버 판단 |
|------|-----------------|---------------|---------|----------|------------|
| 같은 브라우저 새 탭 | 동일 | 새로 생성 | 갱신 | 새로 생성 | 같은 사용자, 새 페이지뷰 |
| 쿠키 삭제 후 | **새로 생성** | 새로 생성 | 새로 생성 | 새로 생성 | **새 사용자** |
| IP변경 + 쿠키삭제 | **새로 생성** | 새로 생성 | 새로 생성 | 새로 생성 | **완전히 새 사용자** |
| 시크릿 모드 | 임시 생성 | 새로 생성 | 새로 생성 | 새로 생성 | **새 사용자** (종료시 소멸) |

### 3.2 유니크 방문자 카운팅 조건 (FINDINGS.md 기반)

```
조회수 +1 조건:
 ✅ 고유 NNB → 페르소나별 자동 달라짐 (쿠키 삭제 시)
 ✅ 새로운 page_uid → 페이지 로드마다 새로 발급
 ✅ SRT30 갱신 → 30분 세션 타임아웃 후 재방문 시
 ⚠️ 동일 NNB 30분 내 재방문 → 중복 카운트 안 될 가능성

 → 1,000 페르소나 = 최대 1,000 유니크 방문 (NNB 기준)
 → 같은 페르소나 재방문 시 30분+ 간격 필요
```

---

## 4. 직접 방문 시 수집되는 추적 이벤트

```
블로그 URL 직접 접속 시:

1. PostViewVisitRecord         → 조회수 +1 (NNB 기준 중복 체크)
2. TIVAN SC2/1                 → 페이지뷰 이벤트
3. TIVAN SC2/11                → 체류시간 측정
4. TIVAN SC2/12                → 스크롤/인터랙션
5. nlog.naver.com/n            → 세션 로깅
6. slogs 파라미터               → 세분화된 행동 로그
7. vitals                       → 페이지 성능 (LCP, FCP, INP)
8. zx                           → 이탈 시 체류시간 최종 기록
```

---

## 5. 참여도 극대화 행동 패턴

C-Rank 추정 공식 중 "페이지 참여도 40%"를 자극하는 설정:

| 지표 | 수집 경로 | 권장 시뮬레이션 |
|------|----------|---------------|
| 체류시간 | SC2/11, SRT5, zx | 2~5분 (너무 길면 비정상) |
| 스크롤 깊이 | SC2/12, slogs `rsk_top` | 글 끝까지 75%+ |
| 상호작용 | slogs `me` 파라미터 | 중간 멈춤, 위로 다시 올림 |
| 공유 행동 | `proxy.blog.naver.com/spi/v1/api/shareLog` | 가끔 공유 버튼 클릭 |
| 댓글/공감 | 블로그 API | 로그인 페르소나만 가능 |

---

## 6. 실행 Phase

### Phase 1: 직접 방문 (Day 0~3, 인덱싱 전)

```
목표: 블로그 참여도 지표 축적
방법:
 - 페르소나당 1회 방문, 2~5분 체류
 - 스크롤 75%+, 자연스러운 행동
 - 하루 50~100 페르소나 (급격한 스파이크 회피)
 - 페르소나 전환 시: 쿠키 삭제 + ANDROID_ID 변경 + GPS 변경 + IP 변경
```

### Phase 2: 인덱싱 확인 (Day 3~5)

```
확인 방법:
 - site:blog.naver.com/{blogId} 로 인덱싱 확인
 - 타겟 키워드로 검색 → 결과에 내 글 위치 확인
 - 블로그 탭, VIEW 탭 등 모든 탭 확인
```

### Phase 3: 검색 클릭 시그널 생성 (인덱싱 확인 후)

```
목표: 검색→클릭→참여 체인 생성
방법:
 - 페르소나로 키워드 검색
 - 검색결과에서 내 블로그 찾을 때까지 스크롤
 - 클릭 → crd/rd 리디렉트 자동 발생
 - 블로그에서 참여 행동 수행
 - 점진적 페르소나 투입량 증가
```

---

## 7. 세션 리셋 프로토콜

```
페르소나 전환 시 (기존 Soul Swap 기반):

1. Chrome 데이터 클리어     → 새 NNB 생성
2. ANDROID_ID 변경          → 디바이스 식별자 변경
3. GPS 위치 변경             → 페르소나 위치 프로필
4. IP 변경                   → 모바일 데이터 토글
5. 영혼 파일(Soul) 복원     → 로그인 상태 유지

→ 네이버 관점: 완전히 다른 디바이스, 다른 사용자
```

---

## 8. Referrer 조작 분석 (2026-02-06 조사 완료)

### 8.1 네이버의 유입 추적 2개 레이어

```
레이어 1: 클라이언트사이드 (HTTP Referer / document.referrer)
  → 브라우저가 자동 설정
  → 블로그 통계 대시보드의 "유입 경로" 분류 기준
  → 조작 가능 ✅

레이어 2: 서버사이드 (crd/rd 리디렉트, nlog, tivan)
  → 네이버 서버가 직접 기록
  → C-Rank/DIA 알고리즘 입력
  → 조작 불가 ❌ (검색결과에 노출되어야 발생)
```

### 8.2 블로그 통계의 유입 소스 판별 기준

- `document.referrer`에 `search.naver.com` 포함 → **"검색 유입"** 분류
- `document.referrer`가 비어있거나 없음 → **"직접 유입"** 분류
- `document.referrer`에 타 도메인 → **"외부 유입"** 분류

참고: 크롬 개발자도구에서 `document.referrer;` 입력으로 현재 페이지의 referrer 확인 가능

### 8.3 조작 방법: Chrome DevTools Protocol (CDP) via ADB

```bash
# Step 1: Chrome으로 검색 페이지 정상 로딩
adb shell am start -a android.intent.action.VIEW \
  -d 'https://search.naver.com/search.naver?where=blog&query=키워드' \
  com.android.chrome
# → nlog에 검색 이벤트 기록됨 (진짜 검색)
# → 페이지 로드 완료 대기 (3~5초)

# Step 2: CDP 포트 포워딩
adb forward tcp:9222 localabstract:chrome_devtools_remote

# Step 3: CDP를 통해 검색 페이지 컨텍스트에서 JavaScript 실행
# → window.location.href = 'https://blog.naver.com/{blogId}/{postId}'
# → 브라우저가 자동으로 Referer 헤더를 검색 페이지 URL로 설정
# → document.referrer = "https://search.naver.com/search.naver?query=키워드"
```

**CDP JavaScript 실행 방법 (Python 예시):**
```python
import websocket
import json

# CDP WebSocket 연결
ws = websocket.create_connection("ws://localhost:9222/devtools/page/{pageId}")

# 검색 페이지에서 블로그로 네비게이션 (referrer 자동 설정)
ws.send(json.dumps({
    "id": 1,
    "method": "Runtime.evaluate",
    "params": {
        "expression": "window.location.href = 'https://blog.naver.com/blogId/postId'"
    }
}))
```

**대안: DOM 조작으로 링크 클릭 시뮬레이션**
```python
# 검색 페이지에 가짜 링크 삽입 후 클릭 (더 자연스러운 네비게이션)
ws.send(json.dumps({
    "id": 1,
    "method": "Runtime.evaluate",
    "params": {
        "expression": """
            const a = document.createElement('a');
            a.href = 'https://blog.naver.com/blogId/postId';
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();
        """
    }
}))
```

### 8.4 Naver Referrer-Policy 제한 (2024.11.07~)

네이버가 2024년 11월 7일부터 Referrer 정보 제한 정책 시행:
- `search.naver.com` → `blog.naver.com`은 크로스 오리진
- `strict-origin-when-cross-origin` 정책이면: 전체 URL 대신 `https://search.naver.com/`만 전달
- 하지만 같은 naver.com 도메인이므로 완전 차단은 아닐 가능성

> **실험 필요**: 실제 검색 클릭 시 블로그가 받는 `document.referrer` 값 확인

### 8.5 효과 범위 정리

| 대상 | referrer 조작 효과 | 이유 |
|------|-------------------|------|
| **블로그 통계 (유입 경로)** | ⭐ 가능성 있음 | document.referrer 기반 분류 |
| **블로그 조회수** | 무관 | NNB 기반 카운팅, referrer 무관 |
| **C-Rank 알고리즘** | ⚠️ 효과 제한적 | 서버사이드 crd/rd 데이터 우선 사용 추정 |
| **DIA 개인화** | 효과 없음 | 서버사이드 검색 세션 데이터 |

### 8.6 결론

- **블로그 통계상 "검색 유입"으로 보이게 하는 것은 가능** (CDP 활용)
- **검색 알고리즘(C-Rank)에 직접 영향은 제한적** (crd/rd 리디렉트가 핵심)
- **그러나** 블로그 통계 자체가 C-Rank 보조 입력일 가능성은 배제 불가
- **Phase 1에서 적용 가치**: 직접 방문을 검색 유입으로 위장하면, 인덱싱 전에도 블로그의 "검색 트래픽" 지표를 축적할 수 있음

### 8.7 Referrer 검증 실험 결과 (2026-02-06 실험 완료)

**실험 환경**: SM-X826N (Galaxy Tab, rooted Magisk), Chrome via ADB, CDP WebSocket

**테스트 블로그**: `https://m.blog.naver.com/warm_dad/224153759640`
**검색 URL**: `https://m.search.naver.com/search.naver?where=blog&query=cctv+설치+후기`

| 실험 | 방법 | document.referrer | 분류 |
|------|------|-------------------|------|
| **A** | 직접 URL (`Page.navigate`, referrer 없음) | `""` (빈 문자열) | 직접 유입 |
| **B** | 검색페이지 로딩 → `window.location.href` 변경 | `"https://m.search.naver.com/"` | **검색 유입** |
| **C** | 검색페이지 → DOM 링크 삽입 + `a.click()` | `"https://m.search.naver.com/"` | **검색 유입** |
| **D** | `Page.navigate` + `referrer` 파라미터 (블로그에서) | `"https://m.search.naver.com/"` | **검색 유입** |
| **E** | **`about:blank` → `Page.navigate` + `referrer` 파라미터** | `"https://m.search.naver.com/"` | **검색 유입** |

**핵심 발견:**

1. **Referrer-Policy 확인**: `strict-origin-when-cross-origin` 적용됨
   - 전체 URL이 아닌 **오리진만** 전달: `https://m.search.naver.com/`
   - 검색 쿼리 정보(query=...)는 전달되지 않음

2. **실험 E = 최적 방법**: 검색 페이지를 실제로 로딩할 필요 없음
   - `about:blank`에서 CDP `Page.navigate(url, referrer)` 한 번이면 충분
   - 검색 페이지 로딩 시간(3~5초) 절약 가능

3. **CDP 코드 (최소 구현)**:
   ```python
   ws.send(json.dumps({
       "id": 1,
       "method": "Page.navigate",
       "params": {
           "url": "https://m.blog.naver.com/{blogId}/{postId}",
           "referrer": "https://m.search.naver.com/search.naver?where=blog&query=키워드"
       }
   }))
   # → document.referrer = "https://m.search.naver.com/" (오리진만 전달)
   ```

4. **CDP WebSocket 연결 시 Origin 헤더 필요**:
   ```python
   ws = websocket.create_connection(
       f'ws://localhost:9222/devtools/page/{tab_id}',
       origin='http://localhost:9222'
   )
   ```

### 8.8 실행 TODO (업데이트)

- [x] 실제 검색 클릭 시 `document.referrer` 값 캡처 → **오리진만 전달 확인**
- [x] 검색 페이지 → CDP 네비게이션 → 블로그 도착 후 referrer 검증 → **성공**
- [x] `about:blank` → `Page.navigate(referrer)` 직접 테스트 → **가장 효율적**
- [x] CDP 연동 코드 NaverChromeUse에 통합 → `src/shared/naver_chrome_use/cdp_client.py`
- [x] Phase 1 워크플로우에 referrer 조작 적용 → `AICampaignWorkflow.execute_direct_visit()`
- [ ] 블로그 통계 대시보드에서 실제 "검색 유입" 분류 확인

---

## 참고 문서

- `NAVER_TRACKING_ANALYSIS.md` - 네이버 추적 시스템 전체 분석
- `../experiments/fingerprint_capture/FINDINGS.md` - IP+쿠키 리셋 실험 결과
- `../../root_vs_browser_analysis.md` - 루팅 vs 브라우저 레벨 분석
- `../../cctv/persona-manager/docs/NAVER_IDENTIFIERS.md` - 페르소나 식별자 관리

### 외부 참고

- [Ogaeng - HTTP 리퍼러 이해하기](https://ogaeng.com/http-referrer/)
- [1089media - Naver Referer Restriction](https://1089media.com/entry/naver-referer-restriction)
- [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
- [Chrome Remote Debugging on Android](https://developer.chrome.com/docs/devtools/remote-debugging)

---

*마지막 업데이트: 2026-02-06 (Referrer 실험 결과 추가)*
