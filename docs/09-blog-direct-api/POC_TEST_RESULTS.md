# POC 테스트 결과

> 2026-03-05 실시

---

## 테스트 환경

| 항목 | 값 |
|------|-----|
| OS | Ubuntu Linux (x86_64) |
| Python | 3.13 |
| HTTP 클라이언트 | httpx |
| 블로그 ID | tlswkehd_ |
| 사용자 ID | tlsdntjd89 |
| Blog No | 47117220 |

---

## 1. 텍스트 전용 발행

| 항목 | 결과 |
|------|------|
| 상태 | **성공** |
| logNo | 224205607821 |
| 소요시간 | ~1초 |
| 코드 | `scripts/test_direct_publish.py` (~150줄) |
| 의존성 | httpx만 (Playwright/Chrome 불필요) |

```
POST https://blog.naver.com/RabbitWrite.naver
Status: 200
Response: {
  "isSuccess": true,
  "result": {
    "redirectUrl": "https://blog.naver.com/PostView.naver?blogId=tlswkehd_&logNo=224205607821"
  }
}
```

---

## 2. 이미지 포함 발행

| 테스트 | logNo | 내용 | 결과 |
|--------|-------|------|------|
| 이미지 1장 | 224205615838 | SE토큰→세션키→업로드→발행 | **성공** |
| 이미지 4장 | 224205620153 | 다중 이미지 + 다중 텍스트 | **성공** |
| 교차 배치 | 224205621536 | 이미지-텍스트-이미지-텍스트 순서 유지 | **성공** |

### 이미지 업로드 플로우 검증

```
[1/4] SE 토큰 발급... ✓
[2/4] 업로드 세션키 획득... ✓
[3/4] 이미지 4장 업로드...
  [1/4] image1.jpg (800x600) ✓
  [2/4] image2.jpg (1200x900) ✓
  [3/4] image3.png (640x480) ✓
  [4/4] image4.jpg (1920x1080) ✓
[4/4] 발행... ✓
```

---

## 3. 리치 콘텐츠 발행

| 컴포넌트 | @ctype | 결과 |
|----------|--------|------|
| 인용문 | `quotation` (style: "line") | **성공** |
| 구분선 | `horizontalLine` | **성공** |

### 발견된 오류와 해결

| 문제 | 원인 | 해결 |
|------|------|------|
| `horizontalRule` 사용 시 parse fail | SE ONE에 해당 타입 없음 | `horizontalLine`으로 변경 (se-editor.js 확인) |

---

## 4. 예약발행

| 시도한 형식 | 결과 |
|------------|------|
| `"2026-03-05 15:00"` (문자열) | **실패** - invalid parameter |
| `"2026-03-05T15:00:00"` (ISO) | **실패** - invalid parameter |
| `1741158000` (epoch 초, int) | **성공** |
| `1741158000000` (epoch 밀리초) | **실패** - invalid parameter |

**결론**: `prePostDate`는 **Unix epoch 초 단위 정수**만 유효.

---

## 5. 글 수정

| 시도 | 엔드포인트 | 결과 |
|------|-----------|------|
| RabbitWrite + logNo | RabbitWrite.naver | **실패** - 새 글 생성됨 |
| RabbitUpdate + logNo + documentId | RabbitUpdate.naver | **성공** |

### 수정 성공 조건

```
엔드포인트: RabbitUpdate.naver
documentModel.documentId = str(logNo)
populationMeta.logNo = logNo
```

응답에 `isAfterUpdateOnly: true` 포함 확인.

---

## 6. 쿠키 관련 오류와 해결

| 문제 | 원인 | 해결 |
|------|------|------|
| `string indices must be integers` | 쿠키가 `[{name,value}]` 리스트가 아닌 `{name:value}` 딕셔너리 | `json.load()` 직접 반환 |
| SE 토큰 401 | `SE-Authorization` 헤더 누락 | `platform.editor.naver.com` API에 JWT 헤더 추가 |

---

## 성능 비교

| 시나리오 | 기존 (CDP/Playwright) | Direct API |
|----------|----------------------|------------|
| 텍스트 전용 | 20-30초 | ~1초 |
| 이미지 1장 | 30-40초 | ~2초 |
| 이미지 4장 | 45-60초 | ~3초 |

**30배 이상 성능 향상** (Chrome 시작/UI 조작 오버헤드 제거)

---

*작성: 2026-03-05*
