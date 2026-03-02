"""
DeviceIdentityManager - 디바이스 식별자 변경 관리 (루팅 필요)

루팅된 디바이스에서 ANDROID_ID 등을 변경하여
네이버에 "다른 디바이스"로 인식되도록 합니다.

테스트 결과 (Galaxy Tab S9+ / Magisk):
- ANDROID_ID 변경: 성공
- 명령어: adb shell "su -c 'settings put secure android_id {id}'"

Author: Naver AI Evolution System
Created: 2025-12-15
"""

import asyncio
import logging
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger("naver_evolution.device_identity")


@dataclass
class IdentityChangeResult:
    """ID 변경 결과"""
    success: bool
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    verified: bool = False
    error_message: Optional[str] = None


class DeviceIdentityManager:
    """
    디바이스 식별자 변경 관리자 (루팅 필요)

    지원하는 ID 변경:
    - ANDROID_ID: 네이버의 주요 디바이스 식별자
    - Advertising ID: Google 광고 ID (선택적)

    사용 예시:
        manager = DeviceIdentityManager()

        # 페르소나 ID 적용
        result = await manager.apply_persona_identity(persona)

        # 수동 변경
        result = await manager.set_android_id("abc123def456789")
    """

    def __init__(self, device_serial: str = None):
        """
        Args:
            device_serial: ADB 디바이스 시리얼 (None이면 자동 감지)
        """
        self.device_serial = device_serial
        self._is_rooted: Optional[bool] = None

    # =========================================================================
    # ADB Commands
    # =========================================================================

    def _run_adb(self, *args, timeout: int = 30) -> Tuple[bool, str]:
        """
        ADB 명령 실행

        Returns:
            (성공 여부, 출력)
        """
        cmd = ["adb"]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(args)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout
            )

            output = result.stdout.strip() if result.stdout else ""
            if result.returncode != 0:
                error = result.stderr.strip() or output
                logger.warning(f"ADB command failed: {error}")
                return (False, error)

            return (True, output)

        except subprocess.TimeoutExpired:
            logger.error(f"ADB command timeout: {' '.join(cmd)}")
            return (False, "Command timeout")
        except Exception as e:
            logger.error(f"ADB command error: {e}")
            return (False, str(e))

    def _run_as_root(self, shell_command: str, timeout: int = 30) -> Tuple[bool, str]:
        """
        루트 권한으로 쉘 명령 실행

        Args:
            shell_command: 실행할 쉘 명령

        Returns:
            (성공 여부, 출력)
        """
        # su -c 로 루트 명령 실행
        return self._run_adb("shell", f"su -c '{shell_command}'", timeout=timeout)

    # =========================================================================
    # Root Check
    # =========================================================================

    async def check_root(self) -> bool:
        """
        루트 권한 확인

        Returns:
            루트 여부
        """
        if self._is_rooted is not None:
            return self._is_rooted

        # su 명령 테스트
        success, output = self._run_as_root("id")

        if success and "uid=0" in output:
            self._is_rooted = True
            logger.info("Device is rooted (root access confirmed)")
        else:
            self._is_rooted = False
            logger.warning("Device is NOT rooted or root access denied")

        return self._is_rooted

    async def ensure_root(self) -> bool:
        """루트 권한 확보 (없으면 예외)"""
        is_rooted = await self.check_root()
        if not is_rooted:
            raise PermissionError(
                "Root access required. Please ensure the device is rooted "
                "and Magisk/su permissions are granted."
            )
        return True

    # =========================================================================
    # ANDROID_ID Management
    # =========================================================================

    async def get_android_id(self) -> Optional[str]:
        """
        현재 ANDROID_ID 조회

        Returns:
            ANDROID_ID (16자 hex) 또는 None
        """
        success, output = self._run_adb("shell", "settings", "get", "secure", "android_id")

        if success and output:
            android_id = output.strip()
            logger.debug(f"Current ANDROID_ID: {android_id}")
            return android_id

        return None

    async def set_android_id(self, android_id: str) -> IdentityChangeResult:
        """
        ANDROID_ID 변경 (루팅 필요)

        Args:
            android_id: 새 ANDROID_ID (16자 hex)

        Returns:
            IdentityChangeResult
        """
        # 1. 형식 검증
        if not self._validate_android_id(android_id):
            return IdentityChangeResult(
                success=False,
                error_message=f"Invalid ANDROID_ID format: {android_id}. Must be 16 hex characters."
            )

        # 2. 루트 확인
        try:
            await self.ensure_root()
        except PermissionError as e:
            return IdentityChangeResult(
                success=False,
                error_message=str(e)
            )

        # 3. 현재 값 저장
        old_id = await self.get_android_id()

        # 4. 변경 실행
        success, output = self._run_as_root(f"settings put secure android_id {android_id}")

        if not success:
            return IdentityChangeResult(
                success=False,
                old_value=old_id,
                error_message=f"Failed to set ANDROID_ID: {output}"
            )

        # 5. 변경 확인
        await asyncio.sleep(0.5)  # 잠시 대기
        new_id = await self.get_android_id()

        verified = new_id == android_id

        if verified:
            logger.info(f"ANDROID_ID changed: {old_id} -> {new_id}")
        else:
            logger.warning(f"ANDROID_ID change not verified: expected {android_id}, got {new_id}")

        return IdentityChangeResult(
            success=verified,
            old_value=old_id,
            new_value=new_id,
            verified=verified
        )

    def _validate_android_id(self, android_id: str) -> bool:
        """ANDROID_ID 형식 검증 (16자 hex)"""
        if not android_id or len(android_id) != 16:
            return False

        try:
            int(android_id, 16)  # hex 변환 가능 여부
            return True
        except ValueError:
            return False

    # =========================================================================
    # Advertising ID Management
    # =========================================================================

    async def get_advertising_id(self) -> Optional[str]:
        """
        현재 광고 ID (GAID) 조회

        Returns:
            광고 ID (UUID 형식) 또는 None
        """
        # Google 광고 ID는 일반적으로 앱을 통해서만 접근 가능
        # 루팅 시 직접 DB 조회 가능
        success, output = self._run_as_root(
            "cat /data/data/com.google.android.gms/shared_prefs/adid_settings.xml"
        )

        if success and "adid_key" in output:
            # XML에서 GAID 추출
            import re
            match = re.search(r'adid_key">([^<]+)', output)
            if match:
                return match.group(1)

        return None

    async def reset_advertising_id(self) -> IdentityChangeResult:
        """
        광고 ID 리셋

        Google 설정 앱의 "광고 ID 재설정" 기능과 동일

        Returns:
            IdentityChangeResult
        """
        old_id = await self.get_advertising_id()

        # 광고 ID 관련 데이터 삭제
        success, output = self._run_as_root(
            "rm -f /data/data/com.google.android.gms/shared_prefs/adid_settings.xml"
        )

        # Google Play Services 재시작
        self._run_adb("shell", "am", "force-stop", "com.google.android.gms")
        await asyncio.sleep(2)

        new_id = await self.get_advertising_id()

        return IdentityChangeResult(
            success=old_id != new_id,
            old_value=old_id,
            new_value=new_id,
            verified=True
        )

    # =========================================================================
    # Persona Integration
    # =========================================================================

    async def apply_persona_identity(self, persona) -> IdentityChangeResult:
        """
        페르소나의 디바이스 ID 적용

        Args:
            persona: Persona 객체 (android_id 속성 필요)

        Returns:
            IdentityChangeResult
        """
        from .persona import Persona

        if not isinstance(persona, Persona):
            return IdentityChangeResult(
                success=False,
                error_message="Invalid persona object"
            )

        # ANDROID_ID 변경
        result = await self.set_android_id(persona.android_id)

        if result.success:
            logger.info(f"Applied persona identity: {persona.name} ({persona.persona_id[:8]}...)")

        return result

    async def get_current_identity(self) -> dict:
        """
        현재 디바이스 ID 정보 조회

        Returns:
            {
                "android_id": "...",
                "advertising_id": "...",
                "is_rooted": True/False
            }
        """
        is_rooted = await self.check_root()
        android_id = await self.get_android_id()

        result = {
            "android_id": android_id,
            "advertising_id": None,
            "is_rooted": is_rooted
        }

        if is_rooted:
            result["advertising_id"] = await self.get_advertising_id()

        return result

    # =========================================================================
    # Backup & Restore
    # =========================================================================

    async def backup_original_id(self, backup_path: str = "/sdcard/original_android_id.txt"):
        """원본 ANDROID_ID 백업"""
        current_id = await self.get_android_id()
        if current_id:
            success, _ = self._run_adb("shell", f"echo {current_id} > {backup_path}")
            if success:
                logger.info(f"Original ANDROID_ID backed up to {backup_path}")
                return current_id
        return None

    async def restore_original_id(self, backup_path: str = "/sdcard/original_android_id.txt"):
        """원본 ANDROID_ID 복원"""
        success, output = self._run_adb("shell", f"cat {backup_path}")
        if success and output:
            original_id = output.strip()
            return await self.set_android_id(original_id)
        return IdentityChangeResult(success=False, error_message="Backup file not found")
