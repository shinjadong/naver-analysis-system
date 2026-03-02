# 모듈화된 캠페인 프레임워크 (Refactor)

`boost_campaign.py`를 재사용 가능한 **액션 기반 아키텍처**로 리팩토링한 버전입니다.

## 📁 폴더 구조

```
src/campaign/refactor/
├── core/                     # 핵심 엔진
│   ├── action_base.py        # CampaignAction 베이스 클래스
│   ├── action_registry.py    # 액션 등록/관리
│   ├── pipeline_engine.py    # 파이프라인 실행 엔진
│   └── context_manager.py    # 실행 컨텍스트 관리
├── actions/                  # 재사용 가능한 액션
│   ├── identity/             # 페르소나 선택, ANDROID_ID 설정
│   ├── reset/                # 쿠키 삭제, IP 회전
│   ├── navigation/           # CDP 네비게이션
│   ├── interaction/          # 체류 시뮬레이션
│   └── logging/              # Supabase 로깅
├── campaigns/                # 캠페인 정의
│   ├── blog_boost.yaml       # 네이버 검색 유입 캠페인
│   ├── instagram_boost.yaml  # Instagram 리퍼러 유입 캠페인
│   └── campaign_runner.py    # 캠페인 실행기
├── cli.py                    # CLI 엔트리포인트
└── README.md                 # 이 문서
```

## 🎯 핵심 개념

### 1. **액션 (Action)**
캠페인을 구성하는 재사용 가능한 최소 단위 작업

```python
class CampaignAction(ABC):
    async def execute(self, context: Dict[str, Any]) -> ActionResult:
        """액션 실행"""
        pass
```

**사용 가능한 액션:**
- `persona_selector` - Supabase에서 랜덤 페르소나 선택
- `android_id_setter` - ANDROID_ID 변경
- `cookie_cleaner` - Chrome 쿠키/캐시 삭제
- `ip_rotator` - 모바일 데이터 재연결로 IP 회전
- `cdp_navigator` - CDP referrer 네비게이션 (UA/sec-fetch 오버라이드 지원)
- `dwell_simulator` - 휴먼라이크 체류 시뮬레이션
- `supabase_logger` - Supabase 로깅

### 2. **파이프라인 (Pipeline)**
여러 액션을 순차/병렬로 조합한 실행 흐름

```yaml
pipelines:
  - name: "prepare_session"
    actions:
      - "persona_selector"
      - "cookie_cleaner"
      - "ip_rotator"
    parallel: false
    break_on_failure: true
```

### 3. **컨텍스트 (Context)**
파이프라인 실행 중 공유되는 데이터 저장소

```python
context = {
    "device_serial": "R3CW60BHSAT",
    "persona_id": "abc123",
    "android_id": "1234567890abcdef",
    "target_url": "https://...",
    # ...
}
```

## 🚀 사용법

### CLI 실행

```bash
# 단일 테스트 (즉시 실행)
python scripts/boost_campaign_refactor.py --target 1

# 10회 방문 (짧은 간격)
python scripts/boost_campaign_refactor.py --target 10 --now

# 자동 모드 (일일 목표 계산 + 분산 실행)
python scripts/boost_campaign_refactor.py --auto

# 상태 확인
python scripts/boost_campaign_refactor.py --status

# Instagram 캠페인 실행
python scripts/boost_campaign_refactor.py --campaign instagram_boost.yaml --target 5 --now
```

### 프로그래밍 방식

```python
from src.campaign.refactor.campaigns import CampaignRunner

runner = CampaignRunner("src/campaign/refactor/campaigns/blog_boost.yaml")
await runner.run_campaign(target=10, now_mode=True)
```

## 📝 YAML 캠페인 정의

### 캠페인 유형

| 파일 | 유형 | 리퍼러 | 설명 |
|------|------|--------|------|
| `blog_boost.yaml` | 검색 유입 | `m.search.naver.com` | 네이버 검색 → 블로그 |
| `instagram_boost.yaml` | SNS 유입 | `l.instagram.com` | Instagram → 블로그 |

### 검색 유입 캠페인 (blog_boost.yaml)

```yaml
name: "네이버 블로그 부스팅 캠페인"
config:
  device_serial: "R3CW60BHSAT"
  base_url: "https://m.blog.naver.com/..."
  referrer_base: "https://m.search.naver.com/search.naver?where=blog&query="
  keywords:
    - "cctv 설치 비용"
    - "사무실 cctv"
```

### Instagram 유입 캠페인 (instagram_boost.yaml)

```yaml
name: "Instagram Referer 블로그 부스팅 캠페인"
config:
  referrer_mode: "fixed"
  referrer_fixed: "https://l.instagram.com/"
  target_urls:
    - "https://m.blog.naver.com/tidtyd222"
    - "https://m.blog.naver.com/wngmlxx12"
  instagram_ua: true           # Instagram 인앱 브라우저 UA 오버라이드
  sec_fetch_headers:           # cross-site 헤더 자동 설정
    sec-fetch-site: "cross-site"
    sec-fetch-mode: "navigate"
    sec-fetch-dest: "document"
```

**Instagram 캠페인 특징:**
- `referrer_mode: "fixed"` — 키워드 조합 없이 고정 리퍼러 사용
- `target_urls` 리스트 — 방문마다 랜덤 선택
- Instagram 인앱 브라우저 UA 자동 생성 (페르소나 디바이스 정보 기반)
- `sec-fetch-site: cross-site` 헤더로 SNS 유입 패턴 재현

### 파이프라인 정의

```yaml
pipelines:
  - name: "prepare_session"
    actions:
      - "persona_selector"
      - "cookie_cleaner"
    parallel: false        # 순차 실행
    break_on_failure: true # 실패 시 중단
    max_retries: 1         # 재시도 횟수
```

### 액션별 설정

```yaml
action_configs:
  dwell_simulator:
    min_dwell: 60
    max_dwell: 180

  cdp_navigator:
    wait_load: 5
    set_geolocation: true
```

## 🔧 새로운 액션 추가하기

### 1. 액션 클래스 작성

```python
# actions/custom/my_action.py
from ...core.action_base import CampaignAction, ActionResult

class MyCustomAction(CampaignAction):
    async def execute(self, context: Dict[str, Any]) -> ActionResult:
        # 컨텍스트에서 값 가져오기
        value = self.get_context_value("some_key")

        # 작업 수행
        result = do_something(value)

        # 결과 반환
        return ActionResult(
            success=True,
            data={"result": result}
        )
```

### 2. 액션 등록

```python
# campaigns/campaign_runner.py
self.registry.register_action("my_custom_action", MyCustomAction)
```

### 3. YAML에 추가

```yaml
pipelines:
  - name: "custom_pipeline"
    actions:
      - "my_custom_action"
```

## 🎨 장점

### 기존 `boost_campaign.py` 대비

| 항목 | 기존 (모놀리식) | 리팩토링 (모듈화) |
|------|----------------|-------------------|
| 코드 재사용 | ❌ 불가능 | ✅ 액션 재사용 |
| 새 캠페인 추가 | 코드 수정 | YAML만 작성 |
| 테스트 | 전체 실행 | 액션 단위 테스트 |
| 유지보수 | 750줄 단일 파일 | 모듈별 분리 |
| 확장성 | 어려움 | 새 액션 추가 쉬움 |
| 가독성 | 낮음 | 높음 (YAML) |

### 구체적 개선점

1. **액션 독립성**: 각 액션이 독립적으로 동작, 재사용 가능
2. **파이프라인 유연성**: YAML로 액션 조합 및 순서 변경
3. **설정 분리**: 코드와 설정(YAML) 분리
4. **테스트 용이성**: 액션 단위로 독립 테스트 가능
5. **확장 용이성**: 새 액션 추가 시 기존 코드 수정 불필요

## 📊 실행 흐름

```
1. YAML 로드 → 캠페인 설정
           ↓
2. 액션 등록 → ActionRegistry
           ↓
3. 파이프라인 등록 → PipelineEngine
           ↓
4. 컴포넌트 초기화 (Supabase, ADB, CDP, ...)
           ↓
5. 각 방문마다:
   ├─ 컨텍스트 생성
   ├─ 파이프라인 순차 실행
   │  ├─ prepare_session (페르소나, 쿠키, IP)
   │  ├─ identity_setup (ANDROID_ID)
   │  ├─ navigation (CDP)
   │  ├─ interaction (체류)
   │  └─ logging (Supabase)
   └─ 다음 방문 대기
```

## 🧪 테스트

### 단일 액션 테스트

```python
from src.campaign.refactor.actions.identity import PersonaSelectorAction

action = PersonaSelectorAction()
context = {"supabase_client": sb, "used_persona_ids": set()}
result = await action.execute(context)

assert result.success
assert "persona_id" in result.data
```

### 파이프라인 테스트

```python
from src.campaign.refactor.core import PipelineEngine, ActionRegistry

registry = ActionRegistry()
registry.register_action("action1", MyAction1)
registry.register_action("action2", MyAction2)

engine = PipelineEngine(registry)
engine.register_pipeline("test", PipelineConfig(
    name="test",
    actions=["action1", "action2"],
    parallel=False
))

context = await engine.execute_pipeline("test", initial_context={})
```

## 📚 참고

- 기존 스크립트: `scripts/boost_campaign.py`
- 모듈화 버전: `scripts/boost_campaign_refactor.py`
- 검색 유입 캠페인: `src/campaign/refactor/campaigns/blog_boost.yaml`
- Instagram 유입 캠페인: `src/campaign/refactor/campaigns/instagram_boost.yaml`
- Instagram 리다이렉트 분석: `../../naver-blog/research/reports/instagram_to_naver_redirect_analysis.md`

---

**작성일**: 2026-02-08
**업데이트**: 2026-02-10 — Instagram 리퍼러 캠페인 추가
**버전**: 1.1.0
