#!/usr/bin/env python3
"""
boost_campaign_v2.py - 모듈화 버전 엔트리포인트

기존 boost_campaign.py와 동일한 기능.
코드는 src/campaign/ 모듈에서 관리.

사용법:
    python scripts/boost_campaign_v2.py --target 1
    python scripts/boost_campaign_v2.py --target 50 --now
    python scripts/boost_campaign_v2.py --auto
    python scripts/boost_campaign_v2.py --status
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from src.campaign.cli import main

if __name__ == "__main__":
    main()
