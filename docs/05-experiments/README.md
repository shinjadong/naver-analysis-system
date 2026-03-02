# 05 — 실험 결과

네이버 식별 시스템에 대한 실험과 검증 결과.

## 문서 목록

| 문서 | 날짜 | 핵심 결과 |
|------|------|-----------|
| [FINGERPRINT_FINDINGS.md](FINGERPRINT_FINDINGS.md) | 2025-12-13 | IP+쿠키삭제 → 완전히 새 NNB → 신규사용자. 98K→166K 이벤트 |
| [REVISIT_TEST_RESULT.md](REVISIT_TEST_RESULT.md) | 2026-02-05 | Chrome 데이터 복원 → NNB 100% 동일 → 재방문자 인식 확인 |
| [REVISIT_TEST_INSTRUCTIONS.md](REVISIT_TEST_INSTRUCTIONS.md) | 2026-02-05 | 재방문 시뮬레이션 테스트 방법 (Python + ADB) |
| [ROOTING_TEST_RESULTS.md](ROOTING_TEST_RESULTS.md) | 2026-01-28 | ANDROID_ID 변경 성공, Chrome cookie DB 스키마 분석 |
| [TEST_RESULTS.md](TEST_RESULTS.md) | - | 32/32 테스트 통과 (BehaviorInjector, ChromeUse, AdbTools) |
| [PIPELINE_TEST_REPORT.md](PIPELINE_TEST_REPORT.md) | - | NaverSessionPipeline 통합 테스트 보고서 |

## 핵심 실험 결론

```
실험 1: IP 변경 + 쿠키 삭제 = 새 NNB = 신규 사용자    ✅ 확인
실험 2: Chrome 데이터 복원 = NNB 유지 = 재방문자        ✅ 확인
실험 3: ANDROID_ID 루팅 변경 = 성공                     ✅ 확인
실험 4: CDP referrer 조작 = 작동                        ✅ 확인
```

## 원본 실험 데이터

원본 데이터는 [experiments/](../../experiments/) 디렉토리에 있습니다:
- `network_capture/capture_result.json` — 네트워크 캡처 결과
- `network_capture/naver_capture.pcap` — 원본 패킷 캡처
- `referrer_test/test_referrer.py` — CDP 리퍼러 테스트 스크립트
