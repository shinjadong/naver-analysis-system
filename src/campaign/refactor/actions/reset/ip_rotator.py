"""
IP 회전 액션
"""

import logging
import time
import subprocess
from typing import Dict, Any

from ...core.action_base import CampaignAction, ActionResult


logger = logging.getLogger("ip_rotator")


class IpRotatorAction(CampaignAction):
    """모바일 데이터 재연결로 IP 회전"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.disable_wait = self.config.get("disable_wait", 2)
        self.enable_wait = self.config.get("enable_wait", 5)

    async def execute(self, context: Dict[str, Any]) -> ActionResult:
        """IP 회전 실행"""
        device_serial = self.get_context_value("device_serial")

        if not device_serial:
            return ActionResult(
                success=False,
                error_message="device_serial 없음"
            )

        try:
            # 모바일 데이터 비활성화
            self._adb(device_serial, "shell", "svc", "data", "disable")
            time.sleep(self.disable_wait)

            # 모바일 데이터 활성화
            self._adb(device_serial, "shell", "svc", "data", "enable")
            time.sleep(self.enable_wait)

            logger.info("IP 회전 완료")

            return ActionResult(success=True)

        except Exception as e:
            return ActionResult(
                success=False,
                error_message=f"IP 회전 실패: {str(e)}"
            )

    def _adb(self, device_serial: str, *args: str, timeout: int = 15) -> str:
        """ADB 명령 실행"""
        cmd = ["adb", "-s", device_serial, *args]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return r.stdout.strip()
        except Exception as e:
            logger.warning(f"ADB error: {e}")
            return ""
