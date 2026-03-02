# 사용 가이드

## 빠른 시작

### 1. 환경 설정

```bash
# 가상환경 활성화
source .venv/bin/activate

# 프로젝트 루트로 이동
cd /root/projects/careon/cctv/ai-project
```

### 2. 실행

```bash
# 상태 확인
python scripts/boost_campaign_refactor.py --status

# 단일 테스트 (1회 방문)
python scripts/boost_campaign_refactor.py --target 1

# 10회 방문 (짧은 간격)
python scripts/boost_campaign_refactor.py --target 10 --now

# 자동 모드 (일일 목표 계산 + 분산 실행)
python scripts/boost_campaign_refactor.py --auto
```

## 실행 모드

### 1. 테스트 모드 (`--target 1`)
- **용도**: 단일 방문 테스트
- **특징**: 1회만 실행하고 종료
- **사용 시점**: 새 기능 테스트, 디버깅

```bash
python scripts/boost_campaign_refactor.py --target 1
```

### 2. 즉시 모드 (`--now`)
- **용도**: 빠른 연속 실행
- **특징**: 15~35초 짧은 간격으로 연속 실행
- **사용 시점**: 수동 캠페인, 빠른 부스팅

```bash
python scripts/boost_campaign_refactor.py --target 50 --now
```

**실행 예시:**
```
[1/50] "cctv 설치 비용"
  ✓ persona_selector (0.52s)
  ✓ cookie_cleaner (1.23s)
  ✓ ip_rotator (7.15s)
  ✓ android_id_setter (0.89s)
  ✓ cdp_navigator (8.34s)
  ✓ dwell_simulator (87.12s)
  ✓ supabase_logger (0.31s)
[1] 쿨다운 23s (0.4분)
...
```

### 3. 자동 모드 (`--auto`)
- **용도**: 일일 목표 달성
- **특징**:
  - 일일 목표 자동 계산 (D+n × 1.23 성장률)
  - 07~23시 사이 자연스럽게 분산
  - 시간대별 가중치 적용 (점심/저녁 피크)
- **사용 시점**: cron 자동 실행

```bash
python scripts/boost_campaign_refactor.py --auto
```

**실행 예시:**
```
자동 모드: D+2, 목표=61, 완료=23, 잔여=38
=== 네이버 블로그 부스팅 캠페인 (분산) ===
목표: 38회
분산 시간: 14:32~23:00, 평균 간격 13.4분
...
```

### 4. 상태 확인 (`--status`)
- **용도**: 캠페인 현황 조회
- **표시 정보**:
  - 페르소나 상태 (idle/active)
  - 오늘 세션 수 (성공/실패)
  - 일일 목표 및 잔여

```bash
python scripts/boost_campaign_refactor.py --status
```

**출력 예시:**
```
============================================================
  부스팅 캠페인 상태 (모듈화 버전)
============================================================
  캠페인 시작일: 2026-02-06
  경과일: D+2
  오늘 목표: 61회
  성장률: x1.23
============================================================
  페르소나 총: 1024개
    idle: 1017
    active: 7
============================================================
  오늘 세션: 45회
    성공: 43
    실패: 2
    잔여: 18
============================================================
```

## Cron 설정

### 자동 실행 (매일 오전 7시)

```bash
# crontab 편집
crontab -e

# 추가
0 7 * * * cd /root/projects/careon/cctv/ai-project && \
  .venv/bin/python scripts/boost_campaign_refactor.py --auto \
  2>&1 >> logs/boost_refactor.log
```

## 커스터마이징

### 1. YAML 설정 변경

`src/campaign/refactor/campaigns/blog_boost.yaml` 파일 수정:

```yaml
config:
  # 디바이스 변경
  device_serial: "NEW_SERIAL"

  # URL 변경
  base_url: "https://m.blog.naver.com/your_blog/post_id"

  # 키워드 추가/삭제
  keywords:
    - "새 키워드 1"
    - "새 키워드 2"

  # 체류시간 조정
  min_dwell: 45   # 45초 (더 짧게)
  max_dwell: 240  # 4분 (더 길게)

# 시간대별 가중치 조정 (높을수록 해당 시간에 집중)
hourly_weights:
  7: 0.5   # 아침 낮게
  12: 2.0  # 점심 높게
  19: 2.0  # 저녁 높게
  22: 0.3  # 밤 낮게
```

### 2. 새로운 액션 추가

```python
# src/campaign/refactor/actions/custom/screenshot.py
from ...core.action_base import CampaignAction, ActionResult

class ScreenshotAction(CampaignAction):
    async def execute(self, context):
        adb_tools = self.get_context_value("adb_tools")
        # 스크린샷 캡처 로직
        return ActionResult(success=True)
```

**YAML에 추가:**
```yaml
pipelines:
  - name: "interaction"
    actions:
      - "dwell_simulator"
      - "screenshot"  # 새 액션
```

## 트러블슈팅

### 1. "CDP 연결 실패"

```bash
# Chrome 디버깅 포트 확인
adb -s R3CW60BHSAT shell cat /proc/net/tcp | grep 2471  # 9333 hex
```

**해결:**
- Chrome 재시작
- CDP 포트 변경 (YAML의 `cdp_port`)

### 2. "페르소나 없음"

```bash
# Supabase idle 페르소나 확인
python scripts/boost_campaign_refactor.py --status
```

**해결:**
- idle 페르소나가 0개면 `status='active'`를 `'idle'`로 변경
- 또는 새 페르소나 생성

### 3. "ANDROID_ID 변경 실패"

**해결:**
- 루트 권한 확인: `adb shell su -c 'id'`
- settings.db 경로 확인
- DeviceIdentityManager 로그 확인

### 4. 연속 실패 (3회 이상)

자동으로 60초 대기 후 CDP 재연결하지만, 계속 실패하면:

```bash
# Chrome 강제종료 후 재시작
adb -s R3CW60BHSAT shell am force-stop com.android.chrome
sleep 2
adb -s R3CW60BHSAT shell am start \
  -a android.intent.action.VIEW \
  -d about:blank \
  com.android.chrome
```

## 로그 확인

```bash
# 실시간 로그 (자동 모드)
tail -f logs/boost_refactor.log

# 최근 100줄
tail -100 logs/boost_refactor.log

# 에러만 필터링
grep "ERROR\|실패" logs/boost_refactor.log
```

## 성능 팁

### 1. 페르소나 분산
- 1000+ 페르소나 사용으로 중복 최소화
- `used_persona_ids` 세트로 중복 방지

### 2. 시간대별 분산
- `hourly_weights`로 자연스러운 검색 패턴 모방
- 점심(12시), 저녁(19시) 피크 설정

### 3. 체류 시간 다양화
- behavior_profile의 `scroll_speed`, `pause_probability` 활용
- 60~180초 범위에서 랜덤 변동

## 기존 버전과 비교

| 기능 | 기존 (`boost_campaign.py`) | 모듈화 (`refactor`) |
|------|----------------------------|---------------------|
| 파일 수 | 1개 (750줄) | 22개 (모듈화) |
| 재사용성 | 없음 | 액션 재사용 가능 |
| 설정 변경 | 코드 수정 | YAML 수정 |
| 테스트 | 전체 실행 | 액션 단위 |
| 확장성 | 어려움 | 쉬움 |
| 가독성 | 낮음 | 높음 |

**호환성**: 두 버전 모두 동일한 Supabase 테이블 사용, 동시 실행 가능

---

**작성일**: 2026-02-08
