# 09. 네이버 블로그 Direct API 발행

> CDP/Playwright UI 자동화를 **HTTP 직접 호출(쿠키 + form data)** 방식으로 완전 대체

---

## 개요

네이버 블로그 SE ONE 에디터의 내부 API를 역분석하여, 브라우저 자동화 없이 **httpx + 쿠키만으로** 블로그 글을 발행하는 시스템.

### 달성 성과

| 항목 | 기존 (CDP/Playwright) | Direct API |
|------|----------------------|------------|
| 코드량 | ~1800줄 (3개 파일) | ~350줄 (1개 파일) |
| 의존성 | Playwright, Chrome, CDP | httpx |
| 실행시간 | 30-60초 | ~2초 (이미지 포함) |
| 안정성 | UI 변경에 취약 | API 구조 의존 |
| 셀렉터 관리 | selector_map.json | 불필요 |
| Self-Healing | DeepSeek/Claude 필요 | 불필요 |
| Chrome 프로세스 | 필수 (headless/headful) | 쿠키 추출 시에만 |
| 이미지 발행 | 파일 다이얼로그 자동화 | HTTP multipart |

---

## 문서 목록

| 문서 | 내용 |
|------|------|
| [NAVER_BLOG_API_ANALYSIS.md](NAVER_BLOG_API_ANALYSIS.md) | 네이버 블로그 API 전체 역분석 (엔드포인트, 데이터 구조, 인증) |
| [DIRECT_PUBLISHER_IMPLEMENTATION.md](DIRECT_PUBLISHER_IMPLEMENTATION.md) | DirectPublisher 구현 상세 (소스코드 + 아키텍처) |
| [COOKIE_AUTO_REFRESH.md](COOKIE_AUTO_REFRESH.md) | 쿠키 자동 갱신 메커니즘 (CookieManager) |
| [POC_TEST_RESULTS.md](POC_TEST_RESULTS.md) | POC 테스트 결과 및 검증 이력 |

---

## 핵심 발견 요약

### 네이버 블로그 발행 API 체계

```
┌─────────────────────────────────────────────────────────┐
│                  네이버 블로그 발행 API                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  인증: 쿠키 (NID_AUT + NID_SES)                          │
│  CSRF: 불필요                                           │
│                                                         │
│  ┌─────────────────┐  ┌─────────────────────────────┐   │
│  │ SE JWT 토큰 발급 │→│ 이미지 업로드 세션키 발급      │   │
│  │ PostWriteForm   │  │ photo-uploader/session-key  │   │
│  │ SeOptions.naver │  └──────────┬──────────────────┘   │
│  └─────────────────┘             │                      │
│                                  ▼                      │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 이미지 업로드 (multipart/form-data)                │  │
│  │ blog.upphoto.naver.com/{sessionKey}/simpleUpload  │  │
│  └───────────────────────┬───────────────────────────┘  │
│                          │                              │
│                          ▼                              │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 글 발행 (application/x-www-form-urlencoded)       │  │
│  │ RabbitWrite.naver  (새 글)                        │  │
│  │ RabbitUpdate.naver (수정)                         │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### SE ONE 에디터 문서 모델

```
documentModel
├── documentId: "" (새 글) / "logNo" (수정)
└── document
    ├── version: "2.9.0"
    ├── id: "01" + 24자리 랜덤
    └── components[]
        ├── @ctype: "documentTitle" (제목)
        ├── @ctype: "text" (본문)
        ├── @ctype: "image" (이미지)
        ├── @ctype: "quotation" (인용문)
        └── @ctype: "horizontalLine" (구분선)
```

---

## 관련 소스 위치 (blog-writer 리포)

| 파일 | 용도 |
|------|------|
| `src/publisher/direct_publisher.py` | DirectPublisher 프로덕션 코드 |
| `src/publisher/cookie_manager.py` | CookieManager 쿠키 자동 갱신 |
| `src/pipeline/batch_publisher.py` | BatchPublisher Direct API 통합 |
| `scripts/test_direct_publish.py` | POC 테스트 스크립트 |

---

*작성: 2026-03-05*
