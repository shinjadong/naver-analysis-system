# 쿠키 자동 갱신 (CookieManager)

> `blog-writer/src/publisher/cookie_manager.py`

---

## 문제

네이버 세션 쿠키(`NID_AUT`, `NID_SES`)는 수시간~수일 후 만료됨.
배치 발행 중 쿠키 만료 시 전체 배치 실패.

## 해결: Lazy Refresh 패턴

```
get_cookies() 호출
    │
    ├── 캐시 유효 (5분 이내)?  → 캐시 반환
    │
    ├── 파일에서 로드 → API 검증
    │   ├── 유효 → 캐시 갱신 → 반환
    │   └── 만료 ↓
    │
    └── CDP에서 재추출
        ├── Chrome 실행 중? → WebSocket 연결
        │   └── Network.getAllCookies → .naver.com 필터
        │       ├── 필수 쿠키 존재? → 검증 → 파일 저장 → 반환
        │       └── 미존재 → RuntimeError
        └── Chrome 미실행 → RuntimeError
```

---

## 동작 상세

### 1. 검증 (Validation)

```python
def _validate(self, cookies: Dict[str, str]) -> bool:
    # PostWriteFormSeOptions.naver로 SE 토큰 발급 시도
    # isSuccess=true → 쿠키 유효
    # HTTP 에러/isSuccess=false → 쿠키 만료
```

- 검증 API: `PostWriteFormSeOptions.naver?blogId={blogId}`
- 이 API가 SE 토큰을 반환하면 쿠키가 유효한 것
- 5분 캐시 (`_validation_interval = 300`)로 불필요한 호출 방지

### 2. CDP 추출

```python
def _extract_from_cdp(self) -> Optional[Dict[str, str]]:
    # 1. CDP /json/version 으로 WebSocket URL 획득
    # 2. websockets.sync.client로 연결
    # 3. Network.getAllCookies 호출
    # 4. .naver.com 도메인 필터링
    # 5. {name: value} 딕셔너리 반환
```

- Chrome이 `--remote-debugging-port=9222`로 실행되어 있어야 함
- `scripts/chrome_session.sh`로 Chrome 시작/관리
- `websockets` 패키지 필요 (`pip install websockets`)

### 3. 발행 시 자동 재시도

```python
# DirectPublisher.publish() 내부
except httpx.HTTPStatusError as e:
    if e.response.status_code in (401, 403) and self._cookie_manager:
        self._cookie_manager.invalidate()  # 캐시 무효화
        cookies = self._load_cookies()     # CDP에서 재추출
        # 동일 요청 1회 재시도
```

---

## 설정

```python
config = DirectPublishConfig(
    blog_id="tlswkehd_",
    user_id="tlsdntjd89",
    cookies_path="data/cookies/naver_cookies.json",
    cdp_url="http://localhost:9222",
    auto_refresh_cookies=True,  # 기본값
)
```

`auto_refresh_cookies=False`로 설정하면 기존 방식 (파일 직접 로드)으로 동작.

---

## 전제 조건

1. Chrome이 CDP 포트와 함께 실행 중
2. Chrome에 네이버 로그인이 되어 있음
3. `websockets` 패키지 설치

### Chrome 시작 (chrome_session.sh)

```bash
#!/bin/bash
CDP_PROFILE="$HOME/.config/google-chrome-cdp"
google-chrome \
    --remote-debugging-port=9222 \
    --no-first-run \
    --user-data-dir="$CDP_PROFILE"
```

---

## 쿠키 JSON 형식

```json
{
  "NID_AUT": "dvzStt...",
  "NID_SES": "AAABqn...",
  "NID_JST": "8NPe8o...",
  "NNB": "OMK5MR...",
  "JSESSIONID": "7D633..."
}
```

- `{name: value}` 딕셔너리 형식 (리스트 아님)
- httpx에서 `cookies=` 파라미터로 직접 전달 가능

---

*작성: 2026-03-05*
