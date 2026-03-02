#!/usr/bin/env python3
"""
boost_campaign_refactor.py - 모듈화 버전 엔트리포인트

기존 boost_campaign.py를 재사용 가능한 액션 기반 아키텍처로 리팩토링.
코드는 src/campaign/refactor/ 모듈에서 관리.

사용법:
    # 단일 테스트
    python scripts/boost_campaign_refactor.py --target 1

    # 즉시 실행 (짧은 간격)
    python scripts/boost_campaign_refactor.py --target 10 --now

    # 자동 모드 (일일 목표 계산 + 분산 실행)
    python scripts/boost_campaign_refactor.py --auto

    # 상태 확인
    python scripts/boost_campaign_refactor.py --status
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from src.campaign.refactor.cli import main

if __name__ == "__main__":
    main()
