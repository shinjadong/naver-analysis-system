"""
캠페인 설정 상수
"""

from datetime import date

# 디바이스
DEVICE_SERIAL = "R3CW60BHSAT"
CDP_PORT = 9333  # 9222는 블로그포스팅 cron 점유

# 타겟 URL
BLOG_URL = "https://m.blog.naver.com/tlswkehd_/224174022465"
REFERRER_BASE = "https://m.search.naver.com/search.naver?where=m_blog&query="

KEYWORDS = [
    "cctv 설치 비용",
    "사무실 cctv",
    "매장 cctv 추천",
    "cctv 월 비용",
    "소상공인 cctv",
    "가게 cctv 가격",
    "cctv 렌탈",
    "kt cctv",
    "cctv 업체 추천",
    "소규모 매장 cctv",
]

# 캠페인 시작일 (일일 목표 계산 기준)
CAMPAIGN_START_DATE = date(2026, 2, 6)
DAILY_BASE = 50
GROWTH_RATE = 1.23

# Chrome 데이터 경로 (루팅)
CHROME_DATA_DIR = "/data/data/com.android.chrome/app_chrome/Default"
CHROME_PACKAGE = "com.android.chrome"

# 체류시간 범위 (초)
MIN_DWELL = 60
MAX_DWELL = 180

# 방문 간 쿨다운 범위 (초) - --now 모드 전용
MIN_VISIT_GAP = 15
MAX_VISIT_GAP = 35

# 분산 모드 (--auto) 시간 설정
SPREAD_START_HOUR = 7
SPREAD_END_HOUR = 23
SPREAD_MIN_GAP = 120   # 최소 간격 (2분)
SPREAD_MAX_GAP = 900   # 최대 간격 (15분)

# 시간대별 트래픽 가중치 (높을수록 해당 시간에 방문 집중)
HOURLY_WEIGHTS = {
    7: 0.5,  8: 0.7,  9: 1.0, 10: 1.2, 11: 1.3,
    12: 1.5, 13: 1.3, 14: 1.0, 15: 0.9, 16: 0.9,
    17: 1.1, 18: 1.3, 19: 1.5, 20: 1.4, 21: 1.2, 22: 0.7,
}
