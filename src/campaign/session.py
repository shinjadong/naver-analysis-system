"""
세션 리셋 (FRE 방지 - pm clear 사용 안 함)
"""

import logging
import time

from .adb_utils import adb, adb_root
from .config import CHROME_DATA_DIR, CHROME_PACKAGE

logger = logging.getLogger("boost")


def reset_session_cookies():
    """
    Chrome 쿠키/캐시만 삭제 (FRE 방지)

    pm clear 사용 시 Chrome First Run Experience가 다시 나타나므로
    루트로 쿠키/캐시 파일만 직접 삭제합니다.
    """
    adb("shell", "am", "force-stop", CHROME_PACKAGE)
    time.sleep(1)

    adb_root(f"rm -rf {CHROME_DATA_DIR}/Cookies*")
    adb_root(f"rm -rf {CHROME_DATA_DIR}/Cache*")
    adb_root(f"rm -rf {CHROME_DATA_DIR}/GPUCache*")
    adb_root(f"rm -rf {CHROME_DATA_DIR}/Session*")
    adb_root(f"rm -rf {CHROME_DATA_DIR}/Web\\ Data*")

    logger.debug("쿠키/캐시 삭제 완료")


def rotate_ip():
    """
    모바일 데이터 재연결로 IP 회전

    airplane mode는 ADB 연결이 끊기므로
    svc data disable/enable 사용
    """
    adb("shell", "svc", "data", "disable")
    time.sleep(2)
    adb("shell", "svc", "data", "enable")
    time.sleep(5)
    logger.debug("IP 회전 완료")
