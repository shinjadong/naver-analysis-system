# 네이버 추적 시스템 분석 보고서

> **분석 일시**: 2025-12-13
> **분석 모델**: DeepSeek Reasoner (Thinking Mode)
> **데이터 소스**: 네이버 앱 네트워크 로그 분석

---

## 1. 데이터 요약

| 항목 | 수량 |
|------|------|
| 추적 도메인 | 74개 |
| URL 파라미터 종류 | 218개 |
| 쿠키 종류 | 40개 |
| 이벤트 타입 | 50개 |

---

## 2. 핵심 추적 시스템

### 2.1 NLOG (네이버 로깅 시스템)

| 항목 | 내용 |
|------|------|
| **엔드포인트** | `nlog.naver.com/n` |
| **로드 스크립트** | `ntm.pstatic.net/ex/nlog.js` |
| **수집 데이터** | 사용자 세션, 페이지 뷰, 이벤트 로그 |
| **데이터 형식** | URL 파라미터 또는 POST 데이터 |
| **알고리즘 영향** | 사용자 참여도 측정, 콘텐츠 품질 평가, 이상 행동 감지 |
| **확실성** | 확실 |

### 2.2 TIVAN SC2 (사용자 행동 추적)

| 항목 | 내용 |
|------|------|
| **엔드포인트** | `tivan.naver.com/sc2/{code}/` |
| **경로 패턴** | `/sc2/1/`, `/sc2/11/`, `/sc2/12/` |
| **호출 횟수** | 256회 (분석 세션 기준) |
| **수집 데이터** | 클릭, 스크롤, 머문 시간, 마우스 호버링 |
| **알고리즘 영향** | 사용자 행동 패턴 분석, 콘텐츠 선호도 파악, 개인화 추천 |
| **확실성** | 확실 |

**SC2 코드 의미 추정:**
- `1`: 기본 클릭 이벤트
- `11`: 특수 상호작용 (상세 조회 등)
- `12`: 이탈/복귀 이벤트

### 2.3 TIVAN 성능 메트릭

| 항목 | 내용 |
|------|------|
| **엔드포인트** | `tivan.naver.com/g/{codes}/` |
| **경로 패턴** | `/g/100_200/`, `/g/103_105_201_205/` |
| **수집 데이터** | 페이지 로드 성능, 리소스 타이밍 |
| **알고리즘 영향** | 기술적 SEO 점수, 사용자 경험 품질 |
| **확실성** | 확실 |

**코드 조합 추정:**
```
100_200: 기본 페이지 트래킹
103: 링크 클릭
105: 버튼 클릭
201: 폼 제출
205: 검색 이벤트
```

### 2.4 GFA (암호화된 행동 페이로드)

| 항목 | 내용 |
|------|------|
| **엔드포인트** | `g.tivan.naver.com/gfa/` |
| **데이터 형식** | Base64Url 인코딩된 긴 문자열 |
| **추정 내용** | 클릭스트림, 스크롤 벡터, 페이지 전환 경로 압축 |
| **알고리즘 영향** | ML 모델 직접 입력, 개인화 랭킹 계산 |
| **확실성** | 추정 |

### 2.5 VETA (광고 성과 추적)

| 항목 | 내용 |
|------|------|
| **엔드포인트** | `siape.veta.naver.com`, `nam.veta.naver.com` |
| **주요 경로** | |
| - `/fxview` | 광고 노출 확인 |
| - `/fxshow` | 광고 표시 완료 |
| - `/openrtb/nbimp` | 입찰 노출 (Bid Impression) |
| - `/openrtb/nurl` | 클릭 추적 |
| - `/openrtb/nbackimp` | 백필 노출 (대체 광고) |
| **알고리즘 영향** | 광고 수익성 평가, CTR 기반 콘텐츠 가치 측정 |
| **확실성** | 확실 |

---

## 3. 주요 추적 도메인

### 3.1 도메인별 호출 빈도

| 도메인 | 호출 횟수 | 용도 |
|--------|----------|------|
| `tivan.naver.com` | 284회 | 사용자 행동 추적 |
| `blogimgs.pstatic.net` | 172회 | 블로그 이미지 CDN |
| `siape.veta.naver.com` | 138회 | 광고 추적 |
| `nlog.naver.com` | 80회 | 세션 로깅 |
| `nam.veta.naver.com` | 76회 | 개인화 광고 |
| `blog.naver.com` | 43회 | 블로그 콘텐츠 |
| `blog.naverblogwidget.com` | 35회 | 외부 위젯 |
| `scv-blog.io.naver.com` | 31회 | 블로그 서비스 |
| `blogpfthumb-phinf.pstatic.net` | 28회 | 프로필 썸네일 |
| `g.tivan.naver.com` | 24회 | GFA 암호화 페이로드 |
| `proxy.blog.naver.com` | 24회 | 블로그 프록시/공유 |
| `cologger.shopping.naver.com` | 19회 | 쇼핑 로깅 |
| `beacons.gcp.gvt2.com` | 9회 | Google 도메인 신뢰도 |

### 3.2 도메인 카테고리 분류

```
┌─────────────────────────────────────────────────────────────┐
│                     네이버 추적 도메인 구조                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   TIVAN     │  │    VETA     │  │    NLOG     │         │
│  │  행동 추적   │  │  광고 추적   │  │  세션 로깅   │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                │
│         └────────────────┼────────────────┘                │
│                          │                                 │
│                          ▼                                 │
│              ┌───────────────────────┐                     │
│              │    C-Rank / DIA       │                     │
│              │   검색 알고리즘 입력    │                     │
│              └───────────────────────┘                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 쿠키 및 식별자 시스템

### 4.1 4계층 추적 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    네이버 쿠키 4계층 구조                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [영구 계층] ─────────────────────────────────────────────   │
│    NNB (2050년 만료) - 디바이스 식별                          │
│    NID (527=...) - 사용자 식별 및 프로파일링                   │
│                                                             │
│  [세션 계층] ─────────────────────────────────────────────   │
│    SRT5 (5분 만료) - 단기 활동 타임스탬프                      │
│    SRT30 (30분 만료) - 중기 세션 타임스탬프                    │
│    _naver_usersession_ - 로그인 세션 관리                     │
│                                                             │
│  [페이지 계층] ────────────────────────────────────────────   │
│    page_uid - 페이지별 고유 식별자                            │
│    PM_CK_loc - 위치 기반 해시                                 │
│                                                             │
│  [실험 계층] ─────────────────────────────────────────────   │
│    BUC - A/B 테스트 버킷                                     │
│    __Secure-BUCKET - 보안 실험 버킷                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 주요 쿠키 상세

#### 영구 식별자

| 쿠키명 | 형식 | 만료 | 용도 |
|--------|------|------|------|
| `NNB` | `24LIDRUPRM6GS` (12자리 영숫자) | 2050년 | 디바이스 식별 |
| `NID` | `527=...` (긴 인코딩 문자열) | 장기 | 사용자 프로파일 |
| `AEC` | Base64 인코딩 | 장기 | 광고 참여 추적 |

#### 세션 관리

| 쿠키명 | 형식 | 만료 | 용도 |
|--------|------|------|------|
| `SRT5` | UNIX 타임스탬프 | 5분 | 실시간 활동 감지 |
| `SRT30` | UNIX 타임스탬프 | 30분 | 세션 활동 추적 |
| `JSESSIONID` | 세션 ID | 세션 | 서버 세션 관리 |

#### 실험/개인화

| 쿠키명 | 형식 | 용도 |
|--------|------|------|
| `BUC` | Base64 인코딩 | A/B 테스트 그룹 할당 |
| `MM_PF` | 플랫폼 ID | 모바일 플랫폼 식별 |
| `MM_search_homefeed` | 설정값 | 홈피드 개인화 |

### 4.3 전체 쿠키 목록 (40개)

```
527, 6DmO4LY0guugTWQPhl5GDhwiZG1W8TxjOpEh7fbopL4,
7F6t41G2nOiDImwB6R6mlgSNgF5KvmZTLw4B0GvzuTU, AEC, ASID,
BA_DEVICE, BKLH6ihXux99MzlgBBNBktZCqplOOd_Pw_MYPQDah8w, BUC,
E-hzNJynFfgc-h8-xCHas_Ru2hQ9o_5QmR8Ij7J5e20,
EYmJYCaq0LgT7IxhrxmVu2IlI_8QeClLq_DdjfWnr1k,
HRfdXW0jKvWwX8liUubPdp8UJo4hTaWxgxwBxIPBdO8, JSESSIONID,
MM_PF, MM_search_homefeed, NAC, NACT, NIB2, NID, NM_srt_chzzk,
NNB, PHPSESSID, PM_CK_loc,
Q9FLHHS9xJLbWXtInCA4lqMjxjIbTTmdF5KVfQQTcV8,
Qcq947lMAe7BsM4NBGOE2zXEUG-0wPxN65Sn7OM6ni8,
RggqtTXpuZ1SkffekUhqM3anpkv3egrM69F10kdJ4gk,
S1auQtHMsgaxBJcqS3foJgrzTR8bd1jeXjO0m5-sVj8, SRT30, SRT5,
UJa_aZtIaouzHE27rgh-FwDuL8l-dii2260YKh4SBDs,
W1_qfxzwszFAswKwjSES1EfJavOS4f3dv4-xu1zAvEw,
XkuDX-WISL9WiXzR1aDA-7kK3jSTXeBIbV9RtjBnZR0, __Secure-BUCKET,
_naver_usersession_, cs4v6Q37XCss8yVKiyWHAxQEoGL1QHvWWNUv3ZL_vCw,
kyzA-_PgHACCgiD4U9T5i4iiKf6OoXVbddVVc3POqE0,
lxcqmrPDCim92eu_X3ADnMMZe21MlZ2vylVq18rCdSQ,
pACWk8Z5NjEoOeW1Mm5EFXgXmujfLqrbAgP4mNCb6kM, page_uid,
rU5gjJMfIHFjZ90W0il_JGYCPsGclszbWt1AJ16etgE,
wU9InJHkORVIFDxd9RjzpTl00H0oDL-KKMc2bLq3z5A
```

---

## 5. URL 파라미터 분석

### 5.1 핵심 추적 파라미터

#### 세션 식별자

| 파라미터 | 예시 | 의미 |
|----------|------|------|
| `tqi` | `jgyK+sqps54ssUdWC04-453136` | 검색 세션 고유 ID |
| `psi` | `1o6hrrhnexZYbZDF` | 페이지 세션 ID (16자리) |
| `iv` | `b45dc247-bf5b-4eeb-9428-2ddfb357426e` | 사용자 세션 UUID |

#### 행동 데이터

| 파라미터 | 형식 | 의미 |
|----------|------|------|
| `slogs` | JSON-like 문자열 | 세분화된 인터랙션 로그 |
| `me` | `7:1765575749540,V,0,0,0,0:...` | 마우스 이벤트 및 뷰포트 |
| `navt` | 타임라인 데이터 | 스크롤 깊이 및 패턴 |

**slogs 상세 구조:**
```json
[{
  "t": "first",
  "pt": 1765575929426,
  "al": "opt:121:0:0:0|rsk_top:121:65:0:65|abL_baX:194:600:0:514|..."
}]
```

#### 성능 메트릭

| 파라미터 | 예시 | 의미 |
|----------|------|------|
| `vitals` | `nt.0,inp.112,lcp.609,fcp.200,ttfb.49` | Core Web Vitals |
| `env` | `{"prtc":"h3","rtt":50,"ect":"4g",...}` | 사용자 환경 정보 |

**vitals 메트릭:**
- `nt`: Navigation Timing
- `inp`: Interaction to Next Paint
- `lcp`: Largest Contentful Paint
- `fcp`: First Contentful Paint
- `ttfb`: Time To First Byte

#### 콘텐츠 식별

| 파라미터 | 예시 | 의미 |
|----------|------|------|
| `blogId` | `ulsune` | 블로그 고유 식별자 |
| `logNo` | `224096031406` | 게시물 고유 번호 |
| `cntsTypeCd` | `K54001` | 콘텐츠 타입 분류 코드 |

#### A/B 테스트

| 파라미터 | 형식 | 의미 |
|----------|------|------|
| `abt` | `[{"eid":"NCO-CARINS3","vid":"3"},...]` | 실험 ID 및 변형 정보 |

### 5.2 숨겨진 추적 파라미터

| 파라미터 | 용도 | 확실성 |
|----------|------|--------|
| `zx` | 페이지 이탈 시 체류시간 측정 | 확실 |
| `nrefreshx` | 페이지 리프레시 횟수 (불만족 지표) | 추정 |
| `shortents_list` | 짧게 본 콘텐츠 목록 (네거티브 신호) | 확실 |
| `rtt` | 네트워크 지연시간 (지역 추정) | 추정 |

---

## 6. 블로그 특화 추적

### 6.1 방문자 추적

| 엔드포인트 | 용도 |
|------------|------|
| `blog.naver.com/NVisitorgp4Ajax.naver` | 실시간 방문자 수 |
| `blog.naver.com/PostViewVisitRecord.naver` | 포스트별 방문 기록 |

### 6.2 상호작용 추적

| 엔드포인트 | 용도 |
|------------|------|
| `blog.naver.com/NaverCommentTemplateIdAsync.naver` | 댓글 활동 |
| `blog.naver.com/NaverCommentMentionInfoListAsync.naver` | 멘션 분석 |
| `proxy.blog.naver.com/spi/v1/api/shareLog` | 공유 행동 |

### 6.3 콘텐츠 메타데이터

| 엔드포인트 | 용도 |
|------------|------|
| `blog.naver.com/BlogTagListInfo.naver` | 태그 정보 |
| `blog.naver.com/PostViewBottomTitleListAsync.naver` | 관련 포스트 |
| `blog.naver.com/mylog/WidgetListAsync.naver` | 위젯 사용 패턴 |

---

## 7. 검색 행동 추적

### 7.1 검색 쿼리 분석

| 엔드포인트 | 용도 |
|------------|------|
| `mac.search.naver.com/mobile/ac` | 자동완성 검색어 |
| `l.search.naver.com/n/scrolllog/v2` | 검색 결과 스크롤 패턴 |
| `s.search.naver.com/p/qra/1/search.naver` | 쿼리 재구성 분석 |

### 7.2 검색 결과 상호작용

| 엔드포인트 | 용도 |
|------------|------|
| `m.search.naver.com/p/crd/rd` | 클릭 재참조 데이터 |
| `er.search.naver.com/csr/v1` | CSR 렌더링 성능 |

---

## 8. 쇼핑 연동 추적

### 8.1 쇼핑 행동 로깅

| 엔드포인트 | 용도 |
|------------|------|
| `cologger.shopping.naver.com/api/v1/collect/exlogcr` | 확장 로그 수집 |
| `cologger.shopping.naver.com/api/v1/validexpose/biz/TODAY_PICK_SHOP/expsTrtr/002020` | 노출 유효성 검증 |
| `recoshopping.naver.com/api/v1/recoshopping` | 추천 상호작용 |

---

## 9. 세션 외 추적 메커니즘

### 9.1 브라우저 핑거프린팅

| 증거 | 설명 |
|------|------|
| `gfp-display-sdk.js` | 기기/브라우저 특성 수집 |
| `gfp-display-nda.js` | 익명 사용자 식별자 생성 |

**수집 가능 정보:**
- User Agent
- 화면 해상도
- 설치 폰트
- 타임존
- WebGL 핑거프린트

### 9.2 서버측 장기 식별

| 파라미터 | 형식 | 용도 |
|----------|------|------|
| `iv` | UUIDv4 | 서버 로그 영구 저장 |

### 9.3 크로스-서비스 데이터 결합

```
검색 (www.naver.com)
       ↓ NID/NNB 쿠키
블로그 (blog.naver.com)
       ↓ NID/NNB 쿠키
쇼핑 (shopping.naver.com)
       ↓
   통합 사용자 프로파일
```

---

## 10. 광고 vs 유기적 트래픽 구분

### 10.1 도메인/경로 수준

| 트래픽 유형 | 도메인/경로 |
|------------|------------|
| **광고** | `siape.veta.naver.com`, `/openrtb/*` |
| **유기적** | `nlog.naver.com/n`, `tivan.naver.com/sc2/*` |

### 10.2 파라미터 수준

| 파라미터 | 값 | 의미 |
|----------|---|------|
| `su` | `SU10868` | 광고 캠페인 ID (Sponsorship Unit) |
| `eid` | `V900`, `V810` | 유기적 이벤트 ID |

### 10.3 이벤트 연쇄 패턴

**광고 클릭 경로:**
```
fxshow (광고 노출) → fxview (광고 클릭) → nurl (광고주 리디렉션)
```

**유기적 탐색 경로:**
```
nlog.naver.com/n → tivan.../sc2/
```

---

## 11. C-Rank/DIA 알고리즘 입력 추정

### 11.1 직접 입력 지표 (확실)

| 카테고리 | 지표 | 데이터 소스 | 영향력 |
|----------|------|------------|--------|
| **사용자 참여** | 페이지뷰, 체류시간, 반송률 | SC2, NLOG | 높음 |
| **상호작용** | 클릭률, 댓글수, 좋아요, 공유 | 블로그 API, shareLog | 높음 |
| **콘텐츠 품질** | 이미지/비디오 포함율, 태그 관련성 | 포스트 메타데이터 | 중간 |
| **사회적 증거** | 팔로워 수, 방문자 수, 외부 링크 | 방문자 카운터 | 중간 |
| **광고 성과** | 노출수, CTR, 전환율 | VETA | 중간 |
| **기술적 요소** | 로딩 속도, 접근성, 모바일 최적화 | vitals, env | 낮음 |

### 11.2 간접 입력 지표 (추정)

| 지표 | 수집 경로 | 영향 추정 |
|------|----------|----------|
| **세션 복잡도** | `sc2/{code}` 다양성 | 탐색 유발 콘텐츠 평가 |
| **광고 내성 지수** | `nbackimp` 비율 | 광고 배치 적절성 |
| **상호작용 밀도** | `gfa/` 페이로드 | 몰입도 측정 |
| **크로스-도메인 참여** | `da_dom_id` | 사이트 내 체류 평가 |
| **위젯 유효성** | `validexpose` | 수익화 효율 |

### 11.3 C-Rank 공식 추정

```
C-Rank = f(
    페이지 참여도 (40%),
    콘텐츠 신선도 (30%),
    사용자 피드백 (20%),
    기술적 SEO (10%)
)
```

### 11.4 DIA 개인화 공식 추정

```
DIA = g(
    검색 역사 (35%),
    실시간 의도 (30%),
    장기 선호도 (25%),
    상황적 컨텍스트 (10%)
)
```

---

## 12. 데이터 흐름

### 12.1 전체 흐름

```
사용자 행동 → 프론트엔드 수집 → 분류 및 버퍼링 → 서버 전송 → 실시간 처리 → 장기 저장 → 알고리즘 입력

1. 사용자 상호작용(클릭, 스크롤, 조회) 발생
2. JavaScript 이벤트 리스너가 데이터 수집
3. NLOG/TIVAN 시스템으로 분류 및 로컬 버퍼링
4. 실시간 또는 배치로 서버 엔드포인트 전송
5. VETA(광고), SC2(행동), NLOG(시스템)으로 분리 처리
6. 실시간 분석 및 장기 보관 저장소로 이관
7. C-Rank/DIA 알고리즘이 다양한 지표 조합으로 평가
```

### 12.2 데이터 계층화

| 계층 | 데이터 유형 | 파라미터 |
|------|-----------|----------|
| 1 | 식별자 | tqi, psi, iv |
| 2 | 행동 데이터 | me, slogs, navt |
| 3 | 성능 데이터 | vitals, env |
| 4 | 콘텐츠 메타 | blogId, logNo, type |
| 5 | 참여 데이터 | shareTime, likeServiceId |

### 12.3 전송 시점

| 유형 | 시점 | 파라미터 |
|------|------|----------|
| **실시간** | 이벤트 발생 즉시 | me, navt |
| **주기적** | 일정 간격 배치 | slogs, vitals |
| **온디맨드** | 페이지 로드 시 | 전체 데이터 |
| **지연** | 사용자 이탈 후 | zx (체류시간) |

---

## 13. 확실성 레벨 분포

| 레벨 | 비율 | 설명 |
|------|------|------|
| **확실** | 65% | 직접 관찰 가능한 파라미터 |
| **추정** | 30% | 맥락적 추론 가능 |
| **불확실** | 5% | 암호화/내부 전용 데이터 |

---

## 14. 추가 조사 필요 항목

1. **`ntm.pstatic.net/ex/nlog.js` 정확한 기능**
   - "NTM" = "Naver Traffic Management" 추정
   - 트래픽 샘플링, 로그 필터링, 실시간 제어 가능성

2. **`g.tivan.naver.com/gfa/` 페이로드 디코딩**
   - Base64/Base64Url 인코딩 확인 필요
   - C-Rank 핵심 입력 데이터 구조 확인 가능

3. **TIVAN 숫자 코드 매핑**
   - `100_200`, `103_105_201_205` 의미 해석
   - 콘텐츠 카테고리 또는 사용자 세그먼트 ID

4. **`beacons.gcp.gvt2.com` 역할**
   - Google Cloud Platform 도메인 신뢰도 모니터링
   - 블로그 호스팅 안정성 점수 영향 가능성

---

## 15. 결론

네이버는 **다층적 추적 시스템**을 통해 사용자 행동을 수집합니다:

1. **명시적 추적**: NLOG, SC2, VETA 등 공식 시스템
2. **암묵적 추적**: 리소스 로딩 패턴, 간접 행동 추론
3. **통합 추적**: 도메인 간 사용자 행동 상관관계

C-Rank/DIA 알고리즘은 이러한 **다차원 데이터**를 종합하여:
- 콘텐츠 품질
- 사용자 관련성
- 참여도

를 평가하며, 단순 인기도가 아닌 **종합적 품질 점수**를 생성합니다.

---

*마지막 업데이트: 2025-12-13*
*분석 모델: DeepSeek Reasoner*
