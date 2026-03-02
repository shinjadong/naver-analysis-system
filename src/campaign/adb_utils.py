"""
ADB 유틸리티 함수
"""

import logging
import subprocess

from .config import DEVICE_SERIAL

logger = logging.getLogger("boost")


def adb(*args: str, timeout: int = 15) -> str:
    """ADB 명령 실행 유틸리티"""
    cmd = ["adb", "-s", DEVICE_SERIAL, *args]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""
    except Exception as e:
        logger.warning(f"ADB error: {e}")
        return ""


def adb_root(shell_cmd: str, timeout: int = 15) -> str:
    """루트 ADB 쉘 명령"""
    return adb("shell", f"su -c '{shell_cmd}'", timeout=timeout)
