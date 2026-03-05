# 네이버 블로그 Direct API 역분석

> SE ONE 에디터 v1.73.1 / Document Model v2.9.0 기준

---

## 1. 발행 엔드포인트

### 1.1 RabbitWrite.naver (새 글 발행)

| 항목 | 값 |
|------|-----|
| URL | `https://blog.naver.com/RabbitWrite.naver` |
| Method | POST |
| Content-Type | `application/x-www-form-urlencoded` |
| 인증 | 쿠키 (`NID_AUT`, `NID_SES` 필수) |
| CSRF 토큰 | **불필요** |

#### Form 필드 (4개)

| 필드 | 타입 | 설명 |
|------|------|------|
| `blogId` | string | 블로그 ID (예: `"tlswkehd_"`) |
| `documentModel` | JSON string | SE ONE 문서 모델 (URL-encoded) |
| `mediaResources` | JSON string | 미디어 리소스 (항상 빈 배열) |
| `populationParams` | JSON string | 발행 설정 (공개, 카테고리, 태그 등) |

#### 성공 응답

```json
{
  "isSuccess": true,
  "result": {
    "redirectUrl": "https://blog.naver.com/PostView.naver?blogId=tlswkehd_&logNo=224205607821"
  }
}
```

### 1.2 RabbitUpdate.naver (글 수정)

| 항목 | 값 |
|------|-----|
| URL | `https://blog.naver.com/RabbitUpdate.naver` |
| Method | POST |
| Content-Type | `application/x-www-form-urlencoded` |
| Form 필드 | RabbitWrite와 동일 (4개) |

**RabbitWrite와의 차이점:**
- `documentModel.documentId` = `str(logNo)` (기존 글 번호를 문자열로)
- `populationMeta.logNo` = `logNo` (기존 글 번호, 정수)
- 응답에 `isAfterUpdateOnly: true` 포함

> **주의**: `RabbitWrite.naver`에 `logNo`를 넣으면 수정이 아닌 **새 글이 생성**됨. 수정은 반드시 `RabbitUpdate.naver` 사용.

### 1.3 RabbitAutoSaveWrite.naver (자동저장)

| 항목 | 값 |
|------|-----|
| URL | `https://blog.naver.com/RabbitAutoSaveWrite.naver` |
| 구조 | RabbitWrite와 동일 (같은 4개 필드) |
| 차이점 | 응답에 `autoSaveNo` 반환 → 다음 autosave에 포함 |

---

## 2. documentModel 구조 (SE ONE v2.9.0)

```json
{
  "documentId": "",
  "document": {
    "version": "2.9.0",
    "theme": "default",
    "language": "ko-KR",
    "id": "01XXXXXXXXXXXXXXXXXXXXXXXX",
    "components": [ /* 아래 컴포넌트 참조 */ ],
    "di": {
      "dif": false,
      "dio": [{ "dis": "N", "dia": { "t": 0, "p": 0, "st": 45, "sk": 1 } }]
    }
  }
}
```

### 2.1 문서 ID 생성 규칙

- `documentId`: 빈 문자열 (새 글) / `str(logNo)` (수정)
- `document.id`: `"01"` + 24자리 랜덤 영숫자 (ULID-like)
- 컴포넌트 `id`: `"SE-"` + UUID v4

### 2.2 di (Document Intelligence) 필드

```json
{
  "dif": false,
  "dio": [{ "dis": "N", "dia": { "t": 0, "p": 0, "st": 45, "sk": 1 } }]
}
```

- `dif`: AI 작성 여부 플래그
- `dio`: 작성 통계 (입력 시간, 붙여넣기 횟수 등)
- `st`: 작성 소요 시간(초), `sk`: 키 입력 횟수

---

## 3. 컴포넌트 타입 (@ctype)

### 3.1 documentTitle (제목)

```json
{
  "@ctype": "documentTitle",
  "id": "SE-uuid",
  "layout": "default",
  "title": [{
    "@ctype": "paragraph",
    "id": "SE-uuid",
    "nodes": [{
      "@ctype": "textNode",
      "id": "SE-uuid",
      "value": "제목 텍스트",
      "style": { "fontFamily": "nanumsquare", "@ctype": "nodeStyle" }
    }]
  }],
  "subTitle": null,
  "align": "left"
}
```

### 3.2 text (본문)

```json
{
  "@ctype": "text",
  "id": "SE-uuid",
  "layout": "default",
  "value": [
    {
      "@ctype": "paragraph",
      "id": "SE-uuid",
      "nodes": [{
        "@ctype": "textNode",
        "id": "SE-uuid",
        "value": "본문 단락 텍스트",
        "style": { "fontFamily": "nanumsquare", "@ctype": "nodeStyle" }
      }]
    }
  ]
}
```

- 각 줄바꿈은 별도의 `paragraph` 객체로 분리
- `nodes` 배열에 여러 `textNode`를 넣으면 인라인 스타일 가능

### 3.3 image (이미지)

```json
{
  "@ctype": "image",
  "id": "SE-uuid",
  "layout": "default",
  "src": "https://blogfiles.pstatic.net{url}?type=w1",
  "internalResource": true,
  "represent": true,
  "path": "{path}",
  "domain": "https://blogfiles.pstatic.net",
  "fileSize": 8229,
  "width": 800,
  "widthPercentage": 0,
  "height": 600,
  "originalWidth": 800,
  "originalHeight": 600,
  "fileName": "filename.jpg",
  "caption": null,
  "format": "normal",
  "displayFormat": "normal",
  "imageLoaded": true,
  "contentMode": "fit",
  "origin": { "srcFrom": "local", "@ctype": "imageOrigin" },
  "ai": false
}
```

- `represent`: 첫 번째 이미지만 `true` (대표이미지)
- `width`: 에디터 표시 크기 (max 966px, 원본보다 크면 축소)
- `height`: 비율 유지 계산 (`originalHeight * displayWidth / originalWidth`)
- `src`: 반드시 `?type=w1` 쿼리 파라미터 포함

### 3.4 quotation (인용문)

```json
{
  "@ctype": "quotation",
  "id": "SE-uuid",
  "layout": "default",
  "value": [
    {
      "@ctype": "paragraph",
      "id": "SE-uuid",
      "nodes": [{
        "@ctype": "textNode",
        "id": "SE-uuid",
        "value": "인용 텍스트",
        "style": { "fontFamily": "nanumsquare", "@ctype": "nodeStyle" }
      }]
    }
  ],
  "style": "line"
}
```

- `style` 옵션: `"line"` (왼쪽 세로선), `"box"` (박스 형태) 등

### 3.5 horizontalLine (구분선)

```json
{
  "@ctype": "horizontalLine",
  "id": "SE-uuid",
  "layout": "default"
}
```

> **주의**: `horizontalRule`이 아니라 **`horizontalLine`**. SE ONE JS 소스(`se-editor.js`)에서 확인.

### 3.6 미확인 타입

- `link` - 링크 카드
- `sticker` - 스티커
- `map` - 지도
- `schedule` - 일정
- `code` - 코드 블록

---

## 4. populationParams (발행 설정)

```json
{
  "configuration": {
    "openType": 2,
    "commentYn": true,
    "searchYn": true,
    "sympathyYn": true,
    "scrapType": 2,
    "outSideAllowYn": true,
    "twitterPostingYn": false,
    "facebookPostingYn": false,
    "cclYn": false
  },
  "populationMeta": {
    "categoryId": 37,
    "logNo": null,
    "directorySeq": 30,
    "directoryDetail": null,
    "mrBlogTalkCode": null,
    "postWriteTimeType": "now",
    "tags": "태그1,태그2",
    "moviePanelParticipation": false,
    "greenReviewBannerYn": false,
    "continueSaved": false,
    "noticePostYn": false,
    "autoByCategoryYn": false,
    "postLocationSupportYn": false,
    "postLocationJson": null,
    "prePostDate": null,
    "thisDayPostInfo": null,
    "scrapYn": false
  },
  "editorSource": "g7F1c16Ykxq+qdR4TxQpvA=="
}
```

### 주요 필드 설명

| 필드 | 값 | 설명 |
|------|-----|------|
| `openType` | `2` / `3` / `0` | 전체공개 / 이웃공개 / 비공개 |
| `categoryId` | 정수 | 블로그 카테고리 ID |
| `logNo` | `null` / 정수 | 수정 시 기존 글 번호 |
| `postWriteTimeType` | `"now"` / `"reserve"` | 즉시발행 / 예약발행 |
| `tags` | 문자열 | 콤마 구분 태그 (예: `"CCTV,설치"`) |
| `prePostDate` | `null` / 정수 | 예약발행 시 Unix epoch (초 단위) |
| `editorSource` | 문자열 | 에디터 식별자 (고정값) |

### 예약발행 주의사항

- `prePostDate`는 **반드시 Unix epoch 초 단위 정수** (`int(datetime.timestamp())`)
- 문자열 형식 (`"YYYY-MM-DD HH:mm"`, ISO 8601 등) → 모두 `"invalid parameter"` 에러
- 밀리초 단위도 실패 → 초 단위만 유효

---

## 5. mediaResources (미디어 리소스)

```json
{ "image": [], "video": [], "file": [] }
```

- 이미지 포함 발행 시에도 **항상 빈 배열**
- 이미지 정보는 `documentModel.components`에만 포함
- 이 필드는 서버측 미디어 관리용 (에디터 동작과 무관)

---

## 6. 이미지 업로드 API (3단계)

### Step A: SE JWT 토큰 발급

```
GET https://blog.naver.com/PostWriteFormSeOptions.naver?blogId={blogId}
인증: 쿠키만
```

**응답:**
```json
{
  "isSuccess": true,
  "result": {
    "token": "eyJ...(JWT)...",
    "appCode": "blogpc001"
  }
}
```

**JWT 구조:**
```json
{
  "sub": "blogpc001",
  "iss": "se3embed",
  "exp": "<현재시간 + 1시간>",
  "userId": "tlsdntjd89"
}
```

### Step B: 업로드 세션키 획득

```
GET https://platform.editor.naver.com/api/blogpc001/v1/photo-uploader/session-key
헤더: SE-Authorization: {JWT}
      Accept: application/json
```

**응답:**
```json
{
  "sessionKey": "MjAy...(base64)...",
  "isSuccess": true
}
```

### Step C: 이미지 업로드

```
POST https://blog.upphoto.naver.com/{sessionKey}/simpleUpload/0
     ?userId={userId}&extractExif=true&extractAnimatedCnt=false
     &extractAnimatedInfo=true&autorotate=true&extractDominantColor=false
     &type=&customQuery=&denyAnimatedImage=false&skipXcamFiltering=false
Content-Type: multipart/form-data
FormData key: "image"
```

**응답 (XML):**
```xml
<item>
  <url>/MjAy.../filename.jpg</url>
  <path>/MjAy.../</path>
  <fileName>filename.jpg</fileName>
  <width>800</width>
  <height>600</height>
  <fileSize>8229</fileSize>
</item>
```

### 이미지 업로드 → 컴포넌트 변환

```
업로드 응답                    →   image 컴포넌트
─────────────────────────────────────────────────
url: "/MjAy.../file.jpg"      →   src: "https://blogfiles.pstatic.net/MjAy.../file.jpg?type=w1"
path: "/MjAy.../"             →   path: "/MjAy.../"
                               →   domain: "https://blogfiles.pstatic.net"
fileName: "file.jpg"           →   fileName: "file.jpg"
width: 800                     →   originalWidth: 800, width: min(800, 966)
height: 600                    →   originalHeight: 600, height: 비율계산
fileSize: 8229                 →   fileSize: 8229
```

---

## 7. 인증 체계

### 필수 쿠키

| 쿠키 | 역할 |
|------|------|
| `NID_AUT` | 네이버 인증 토큰 |
| `NID_SES` | 네이버 세션 토큰 |
| `NID_JST` | JWT 스타일 보조 토큰 |

### 쿠키 추출 방법

1. Chrome을 `--remote-debugging-port=9222`로 실행
2. 네이버 로그인 (수동 또는 기존 세션)
3. CDP `Network.getAllCookies`로 추출 → JSON 저장
4. httpx에서 `{name: value}` 딕셔너리로 사용

### 쿠키 수명

- 일반적으로 수시간~수일 유지
- `CookieManager`로 자동 검증 및 갱신 가능

---

## 8. SE ONE 에디터 정보

| 항목 | 값 |
|------|-----|
| 에디터 이름 | SE ONE (Smart Editor ONE) |
| JS 파일 | `se-editor.js` (minified) |
| 문서 모델 버전 | 2.9.0 |
| 에디터 버전 | v1.73.1 |
| 앱 코드 | `blogpc001` |
| editorSource | `g7F1c16Ykxq+qdR4TxQpvA==` |
| 이미지 도메인 | `https://blogfiles.pstatic.net` |

---

*작성: 2026-03-05*
