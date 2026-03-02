# AI-Driven Workflow 구현 문서

> 작성일: 2026-01-10
> 작성자: Claude Opus 4.5

---

## 개요

네이버의 동적 UI 특성상 고정 좌표 기반 자동화는 불안정합니다. 이 문서는 **AI-driven 워크플로우**를 구현하여 droidrun의 Portal과 StealthAdbTools를 활용해 동적 UI 탐지 및 휴먼라이크 액션을 수행하는 방법을 설명합니다.

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AI-Driven Workflow                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐  │
│  │  FastAPI Server  │───▶│ TrafficExecutor  │───▶│ AICampaign   │  │
│  │  /traffic/       │    │                  │    │ Workflow     │  │
│  │  execute-ai      │    └──────────────────┘    └──────────────┘  │
│  └──────────────────┘                                   │          │
│                                                         ▼          │
│                                              ┌──────────────────┐  │
│                                              │ AISession        │  │
│                                              │ Controller       │  │
│                                              └──────────────────┘  │
│                                                    │    │          │
│                                         ┌──────────┘    └────────┐ │
│                                         ▼                        ▼ │
│                              ┌──────────────────┐    ┌───────────┐ │
│                              │  droidrun        │    │ Stealth   │ │
│                              │  PortalClient    │    │ AdbTools  │ │
│                              │  (UI 트리 분석)  │    │ (액션)    │ │
│                              └──────────────────┘    └───────────┘ │
│                                         │                        │ │
│                                         └────────────┬───────────┘ │
│                                                      ▼             │
│                                              ┌──────────────┐      │
│                                              │   Android    │      │
│                                              │   Device     │      │
│                                              │   (ADB)      │      │
│                                              └──────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 구현 파일

### 1. AISessionController (`src/shared/ai_session_controller.py`)

**역할**: droidrun Portal과 StealthAdbTools를 통합하여 AI가 UI를 분석하고 휴먼라이크 액션을 수행

**주요 기능**:

| 메서드 | 설명 |
|--------|------|
| `connect()` | 디바이스 및 Portal 연결 |
| `get_ui_state()` | 현재 UI 상태(accessibility tree) 획득 |
| `refresh_ui_elements()` | UI 요소 목록 파싱 및 캐싱 |
| `wait_for_elements()` | UI 요소 로딩 대기 (폴링) |
| `find_element_by_text()` | 텍스트로 요소 찾기 |
| `find_element_in_region()` | 특정 y 영역에서 요소 찾기 |
| `humanlike_tap()` | 휴먼라이크 탭 (무작위 오프셋) |
| `humanlike_swipe()` | 휴먼라이크 스와이프 (베지어 커브) |
| `humanlike_scroll_down/up()` | 휴먼라이크 스크롤 |

**핵심 개선사항**:

```python
# bounds 파싱 - boundsInScreen 딕셔너리 형식 지원
def _parse_bounds(self, node: Dict) -> Optional[Tuple[int, int, int, int]]:
    # 1. boundsInScreen (딕셔너리) - Portal 표준 형식
    bounds_dict = node.get("boundsInScreen") or node.get("boundsInParent")
    if isinstance(bounds_dict, dict):
        left = int(bounds_dict.get("left", 0))
        top = int(bounds_dict.get("top", 0))
        right = int(bounds_dict.get("right", 0))
        bottom = int(bounds_dict.get("bottom", 0))
        return (left, top, right, bottom)
```

```python
# UI 요소 로딩 대기
async def wait_for_elements(
    self,
    min_elements: int = 1,
    timeout_sec: float = 10.0,
    poll_interval: float = 0.5
) -> List[UIElement]:
    """UI 요소가 로드될 때까지 대기"""
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        elements = await self.refresh_ui_elements()
        text_elements = [e for e in all_elements if e.text.strip()]
        if len(text_elements) >= min_elements:
            return elements
        await asyncio.sleep(poll_interval)
```

---

### 2. AICampaignWorkflow (`src/shared/ai_campaign_workflow.py`)

**역할**: AI가 각 스텝을 제어하는 캠페인 워크플로우

**워크플로우 스텝**:

```
1. 네이버 통합검색 → 키워드 검색
2. 검색 결과 스크롤 (내려갔다 올라오기)
3. '블로그' 탭 동적 탐지 및 클릭
4. 타겟 포스트 동적 탐지 및 클릭
5. 포스트 페이지 휴먼라이크 리딩
6. 공유 버튼 클릭 → URL 복사
```

**사용법**:

```python
workflow = AICampaignWorkflow(device_serial="R3CW60BHSAT")
result = await workflow.execute(
    keyword="cctv가격",
    target_blog_title="CCTV가격 부담된다면?",
    target_blogger="한화비전 키퍼"
)

# result.success: 성공 여부
# result.dwell_time_sec: 체류시간
# result.scroll_count: 스크롤 횟수
```

---

### 3. TrafficExecutor (`src/api/services/traffic_executor.py`)

**역할**: API 요청을 받아 워크플로우 실행 및 결과 저장

**주요 기능**:
- 캠페인 정보 조회 (Supabase)
- AI 워크플로우 실행
- 트래픽 로그 저장
- 캠페인 통계 업데이트

---

### 4. Traffic API (`src/api/routes/traffic.py`)

**새 엔드포인트**: `POST /traffic/execute-ai`

```bash
curl -X POST -H "X-API-Key: careon-traffic-engine-2026" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": "<캠페인ID>",
    "keyword": "cctv가격",
    "blog_title": "CCTV가격 부담된다면?"
  }' \
  http://localhost:8000/traffic/execute-ai
```

**응답**:
```json
{
  "success": true,
  "execution_id": null,
  "message": "AI workflow completed",
  "campaign_id": "cc57f30a-7fbf-461b-9790-573aec8a51e0",
  "persona_id": "ai_session",
  "device_serial": "R3CW60BHSAT"
}
```

---

## 해결한 문제들

### 1. `'str' object has no attribute 'get'` 에러

**원인**: `a11y_tree`가 dict(단일 루트)인데 리스트로 처리

**해결**:
```python
# a11y_tree가 dict인 경우 리스트로 래핑
if isinstance(a11y_tree, dict):
    a11y_tree = [a11y_tree]
```

### 2. UI 요소 0개 탐지

**원인**: `bounds` 키 대신 `boundsInScreen` 사용, 형식이 딕셔너리

**해결**:
```python
# boundsInScreen 딕셔너리 파싱
bounds_dict = node.get("boundsInScreen")
if isinstance(bounds_dict, dict):
    left = int(bounds_dict.get("left", 0))
    # ...
```

### 3. 페이지 로딩 전 요소 탐지 시도

**원인**: 페이지 로딩 완료 전에 요소 찾기 시도

**해결**:
```python
# wait_for_elements로 대기
await self.controller.wait_for_elements(min_elements=3, timeout_sec=8.0)
```

---

## 테스트 결과

### Before (개선 전)
```
[STEP 3] Finding and clicking 'Blog' tab...
[WARNING] Total elements: 0
[WARNING] Blog tab not found, using direct URL...
```

### After (개선 후)
```
[STEP 3] Finding and clicking 'Blog' tab...
[INFO] Found 98 text elements after 0.2s
[STEP 4] Finding target post...
[INFO] Found 79 text elements after 0.4s
```

**성과**:
- UI 요소 탐지: 0개 → **98개**
- 폴백 의존도: 높음 → 낮음
- 체류시간: ~130초
- 스크롤 횟수: ~28회

---

## 의존성

```bash
# 필수 패키지
pip install python-dotenv
pip install async_adbutils httpx

# droidrun (로컬 설치)
pip install -e /home/tlswkehd/projects/cctv/droidrun
```

---

## 환경변수

```bash
# .env
DEEPSEEK_API_KEY=sk-xxx  # DeepSeek API 키
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_KEY=xxx
```

---

## 실행 방법

```bash
# 1. 가상환경 활성화
source .venv/bin/activate

# 2. 서버 실행
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# 3. AI 워크플로우 테스트
curl -X POST -H "X-API-Key: careon-traffic-engine-2026" \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": "cc57f30a-7fbf-461b-9790-573aec8a51e0",
    "keyword": "cctv가격",
    "blog_title": "CCTV가격 부담된다면?"
  }' \
  http://localhost:8000/traffic/execute-ai
```

---

## 향후 개선 사항

1. **DeepSeek AI 연동**: LLM이 UI 상태를 분석하고 최적의 액션 결정
2. **스크린샷 기반 분석**: OCR/Vision으로 더 정확한 요소 탐지
3. **재시도 로직 강화**: 실패 시 다양한 폴백 전략
4. **병렬 실행**: 여러 디바이스에서 동시 실행

---

## 관련 문서

- [CLAUDE.md](../CLAUDE.md) - 프로젝트 컨텍스트
- [README.md](../README.md) - 프로젝트 개요

---

*마지막 업데이트: 2026-01-10*
