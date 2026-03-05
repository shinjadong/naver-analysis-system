# DirectPublisher 구현 상세

> `blog-writer/src/publisher/direct_publisher.py` 기반

---

## 아키텍처

```
DirectPublisher
├── CookieManager         # 쿠키 로드/검증/자동갱신
├── _get_se_token()       # SE JWT 발급
├── _get_session_key()    # 업로드 세션키
├── _upload_image()       # 이미지 업로드
├── _build_*_component()  # SE ONE 컴포넌트 빌더
│   ├── title
│   ├── text
│   ├── image
│   ├── quotation
│   └── horizontal_line
├── _build_document_model()     # 문서 모델 조립
├── _build_population_params()  # 발행 설정
└── publish()             # 메인 발행 메서드
    ├── 이미지 일괄 업로드
    ├── 컴포넌트 순서 조립
    ├── RabbitWrite/Update 호출
    └── 401/403 시 쿠키 갱신 재시도
```

---

## 설정 (DirectPublishConfig)

```python
@dataclass
class DirectPublishConfig:
    blog_id: str                    # 네이버 블로그 ID
    user_id: str                    # 네이버 사용자 ID (이미지 업로드용)
    cookies_path: str = "data/cookies/naver_cookies.json"
    category_id: int = 37           # 블로그 카테고리 ID
    timeout: int = 30               # HTTP 요청 타임아웃 (초)
    cdp_url: str = "http://localhost:9222"  # Chrome CDP URL
    auto_refresh_cookies: bool = True       # 쿠키 자동 갱신 활성화
```

---

## publish() 메서드 인터페이스

```python
async def publish(
    self,
    title: str,                              # 글 제목
    sections: List[Dict[str, Any]],          # 섹션 리스트
    tags: Optional[List[str]] = None,        # 태그 리스트
    schedule_time: Optional[datetime] = None, # 예약발행 시간
    edit_log_no: Optional[int] = None,       # 수정할 기존 글 번호
) -> PublishResult:
```

### sections 형식

```python
sections = [
    {"type": "image", "path": "/path/to/image.jpg"},
    {"type": "text", "content": "본문 텍스트\n줄바꿈 가능"},
    {"type": "quotation", "content": "인용문", "style": "line"},
    {"type": "hr"},
    {"type": "image", "path": "/path/to/image2.png"},
    {"type": "text", "content": "추가 텍스트"},
]
```

- 이미지-텍스트 교차 배치 지원 (순서 보존)
- 이미지 파일이 존재하지 않으면 해당 섹션 스킵

### PublishResult

```python
@dataclass
class PublishResult:
    success: bool
    blog_url: Optional[str] = None
    error_message: Optional[str] = None
    screenshots: List[str] = field(default_factory=list)
```

---

## 발행 흐름 상세

```
1. 토큰 초기화 (매 발행마다 fresh)
   └─ _se_token = None, _session_key = None

2. 쿠키 로드
   └─ CookieManager.get_cookies() 또는 파일 직접 로드

3. 이미지 업로드 (순서 보존)
   ├─ sections에서 type="image" 추출 (인덱스 기록)
   ├─ SE 토큰 → 세션키 → multipart 업로드
   └─ uploaded_map[section_index] = image_meta

4. 컴포넌트 조립 (sections 순서 유지)
   ├─ 원래 sections 순서대로 순회
   ├─ image → _build_image_component (첫 이미지만 represent=True)
   ├─ text → _build_text_component
   ├─ quotation → _build_quotation_component
   └─ hr → _build_horizontal_line_component

5. 문서 모델 + 발행 설정 생성
   ├─ _build_document_model(title, components, edit_log_no)
   └─ _build_population_params(tags, schedule_time, edit_log_no)

6. HTTP POST
   ├─ edit_log_no 있으면 → RabbitUpdate.naver
   └─ 없으면 → RabbitWrite.naver

7. 오류 처리
   ├─ 401/403 → CookieManager.invalidate() → 쿠키 재추출 → 1회 재시도
   └─ 기타 → PublishResult(success=False, error_message=...)
```

---

## 사용 예시

### 새 글 발행

```python
config = DirectPublishConfig(
    blog_id="tlswkehd_",
    user_id="tlsdntjd89",
    cookies_path="data/cookies/naver_cookies.json",
)
publisher = DirectPublisher(config)

result = await publisher.publish(
    title="테스트 글",
    sections=[
        {"type": "image", "path": "/tmp/photo.jpg"},
        {"type": "text", "content": "안녕하세요.\n본문입니다."},
        {"type": "hr"},
        {"type": "quotation", "content": "인용문입니다.", "style": "line"},
    ],
    tags=["CCTV", "설치"],
)
print(result.blog_url)  # https://blog.naver.com/PostView.naver?blogId=...&logNo=...
```

### 글 수정

```python
result = await publisher.publish(
    title="수정된 제목",
    sections=[{"type": "text", "content": "수정된 본문"}],
    edit_log_no=224205607821,  # 기존 글 번호
)
```

### 예약발행

```python
from datetime import datetime, timedelta

result = await publisher.publish(
    title="예약 글",
    sections=[{"type": "text", "content": "예약 본문"}],
    schedule_time=datetime.now() + timedelta(hours=2),
)
```

### BatchPublisher 통합

```python
from src.pipeline.batch_publisher import BatchPublisher

bp = BatchPublisher(
    csv_path="data/keywords.csv",
    blog_id="tlswkehd_",
    use_direct_api=True,      # Direct API 사용 (기본값)
    user_id="tlsdntjd89",
    cookies_path="data/cookies/naver_cookies.json",
)
result = await bp.publish_batch(limit=5, sleep_between=30)
```

---

## 기존 시스템과의 관계

```
기존 (3파일, ~1800줄):
├── naver_publisher.py         → 사용 안 함 (레거시)
├── deterministic_publisher.py → 사용 안 함 (레거시)
└── adaptive_publisher.py      → PublishResult 인터페이스만 사용

신규 (2파일, ~500줄):
├── direct_publisher.py        → 모든 발행 담당
└── cookie_manager.py          → 쿠키 자동 갱신

통합:
└── batch_publisher.py         → use_direct_api=True (기본) 시 DirectPublisher 사용
```

---

*작성: 2026-03-05*
