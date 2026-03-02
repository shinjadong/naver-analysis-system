# 01 — 네이버 추적 시스템 분석

네이버가 사용자의 행동을 추적하는 5개 시스템과 그 데이터 흐름을 분석합니다.

## 문서 목록

| 문서 | 설명 |
|------|------|
| [NAVER_TRACKING_ANALYSIS.md](NAVER_TRACKING_ANALYSIS.md) | **핵심 문서** — 5개 추적 시스템(NLOG, TIVAN SC2, TIVAN Perf, GFA, VETA) 전체 분석. 74 도메인, 218 URL 파라미터, 40 쿠키, 50 이벤트 타입 |
| [TRAFFIC_BOOSTING_STRATEGY.md](TRAFFIC_BOOSTING_STRATEGY.md) | 추적 시스템 분석 기반 트래픽 부스팅 전략. 검색 클릭 시그널 체인, 세션 카운팅 메커니즘, CDP 리퍼러 조작 |

## 핵심 요약

### 5개 추적 시스템

```
1. NLOG      → nlog.naver.com/n       (세션 로깅, Image pixel)
2. TIVAN SC2 → tivan.naver.com/sc2/   (행동 추적, Beacon API)
3. TIVAN Perf → tivan.naver.com/g/    (성능 추적, Core Web Vitals)
4. GFA       → g.tivan.naver.com/gfa/ (광고 행동, 암호화 POST)
5. VETA      → siape.veta.naver.com   (광고 입찰, OpenRTB)
```

### 데이터 흐름

```
사용자 행동 → 프론트엔드 SDK 수집 → 추적 엔드포인트 전송 → 서버 처리 → C-Rank/DIA 입력
```
