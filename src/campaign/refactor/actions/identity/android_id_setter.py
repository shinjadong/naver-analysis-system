"""
ANDROID_ID 설정 액션
"""

import logging
import time
import subprocess
from typing import Dict, Any

from ...core.action_base import CampaignAction, ActionResult


logger = logging.getLogger("android_id_setter")


class AndroidIdSetterAction(CampaignAction):
    """ANDROID_ID 변경 액션"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.chrome_package = self.config.get("chrome_package", "com.android.chrome")

    async def execute(self, context: Dict[str, Any]) -> ActionResult:
        """ANDROID_ID 변경 실행"""
        identity_mgr = self.get_context_value("identity_manager")
        android_id = self.get_context_value("android_id")
        device_serial = self.get_context_value("device_serial")

        if not identity_mgr or not android_id:
            return ActionResult(
                success=False,
                error_message="identity_manager 또는 android_id 없음"
            )

        # Chrome 강제종료
        self._force_stop_chrome(device_serial)
        time.sleep(0.5)

        # ANDROID_ID 변경
        result = await identity_mgr.set_android_id(android_id)

        if not result.success:
            return ActionResult(
                success=False,
                error_message=f"ANDROID_ID 변경 실패: {result.error_message}"
            )

        logger.info(f"ANDROID_ID 변경: {android_id[:8]}...")

        return ActionResult(
            success=True,
            data={"android_id": android_id}
        )

    def _force_stop_chrome(self, device_serial: str):
        """Chrome 강제종료"""
        try:
            subprocess.run(
                ["adb", "-s", device_serial, "shell", "am", "force-stop", self.chrome_package],
                capture_output=True,
                timeout=5
            )
        except Exception as e:
            logger.warning(f"Chrome 강제종료 실패: {e}")
