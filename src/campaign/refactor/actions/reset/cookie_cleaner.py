"""
쿠키/캐시 삭제 액션 (FRE 방지)
"""

import logging
import time
import subprocess
from typing import Dict, Any

from ...core.action_base import CampaignAction, ActionResult


logger = logging.getLogger("cookie_cleaner")


class CookieCleanerAction(CampaignAction):
    """Chrome 쿠키/캐시 삭제 액션 (pm clear 사용 안 함)"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.chrome_package = self.config.get("chrome_package", "com.android.chrome")
        self.chrome_data_dir = self.config.get(
            "chrome_data_dir",
            "/data/data/com.android.chrome/app_chrome/Default"
        )

    async def execute(self, context: Dict[str, Any]) -> ActionResult:
        """쿠키/캐시 삭제 실행"""
        device_serial = self.get_context_value("device_serial")

        if not device_serial:
            return ActionResult(
                success=False,
                error_message="device_serial 없음"
            )

        try:
            # Chrome 강제종료
            self._adb(device_serial, "shell", "am", "force-stop", self.chrome_package)
            time.sleep(1)

            # 루트로 쿠키/캐시 삭제
            self._adb_root(device_serial, f"rm -rf {self.chrome_data_dir}/Cookies*")
            self._adb_root(device_serial, f"rm -rf {self.chrome_data_dir}/Cache*")
            self._adb_root(device_serial, f"rm -rf {self.chrome_data_dir}/GPUCache*")
            self._adb_root(device_serial, f"rm -rf {self.chrome_data_dir}/Session*")
            self._adb_root(device_serial, f"rm -rf {self.chrome_data_dir}/Web\\ Data*")

            logger.info("쿠키/캐시 삭제 완료")

            return ActionResult(success=True)

        except Exception as e:
            return ActionResult(
                success=False,
                error_message=f"쿠키 삭제 실패: {str(e)}"
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

    def _adb_root(self, device_serial: str, shell_cmd: str, timeout: int = 15) -> str:
        """루트 ADB 쉘 명령"""
        return self._adb(device_serial, "shell", f"su -c '{shell_cmd}'", timeout=timeout)
