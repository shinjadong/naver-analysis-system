# 02 — 사용자 식별 체계

네이버가 "이놈이 그놈이다"를 판별하는 원리와, 이에 대응하는 페르소나 시스템 설계.

## 문서 목록

| 문서 | 설명 |
|------|------|
| [NID_IDENTIFICATION.md](NID_IDENTIFICATION.md) | **핵심 문서** — 4-Layer 식별 체계 종합. NNB/NID/iv/핑거프린트 분석, 동일인 판별 로직, 블로그 조회수 조건 |
| [PERSONA_SYSTEM_DESIGN.md](PERSONA_SYSTEM_DESIGN.md) | 가상 사용자(페르소나) 관리 시스템 설계. ANDROID_ID/NNB/Chrome 데이터 관리 |
| [FINGERPRINT_EXPERIMENT_PROTOCOL.md](FINGERPRINT_EXPERIMENT_PROTOCOL.md) | 브라우저 핑거프린트 캡처 실험 프로토콜 (3개 시나리오) |

## 핵심: 판별 우선순위

```
1. NID (로그인) → 확정적 식별
2. NNB (쿠키)  → 디바이스 수준 식별 ← 비로그인 시 PRIMARY
3. iv (서버)   → 서버측 세션 연결
4. Fingerprint → 보조 수단 (단독 불충분)
```
