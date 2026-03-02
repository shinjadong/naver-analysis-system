"""
ChromeDataManager - Chrome 데이터 백업/복원 관리 (루팅 필요)

Chrome 쿠키는 encrypted_value로 암호화되어 직접 주입이 어려움.
대신 Chrome 데이터 폴더 전체를 페르소나별로 백업/복원하는 방식 사용.

테스트 결과 (Galaxy Tab S9+ / Magisk):
- Chrome 데이터 경로: /data/data/com.android.chrome/app_chrome/Default/
- 쿠키 DB 접근: 성공 (루팅 필요)
- 쿠키 값 암호화: encrypted_value 필드 사용
- 해결책: 폴더 전체 백업/복원

Author: Naver AI Evolution System
Created: 2025-12-15
"""

import asyncio
import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

logger = logging.getLogger("naver_evolution.chrome_data")


# Chrome 데이터 경로
CHROME_PACKAGE = "com.android.chrome"
CHROME_DATA_PATH = f"/data/data/{CHROME_PACKAGE}/app_chrome/Default"
CHROME_COOKIES_DB = f"{CHROME_DATA_PATH}/Cookies"

# 페르소나 데이터 저장 경로 (SD 카드)
PERSONAS_BASE_PATH = "/sdcard/personas"


@dataclass
class ChromeDataResult:
    """Chrome 데이터 작업 결과"""
    success: bool
    operation: str  # "backup", "restore", "clear"
    path: Optional[str] = None
    size_bytes: int = 0
    error_message: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class CookieInfo:
    """쿠키 정보"""
    name: str
    host_key: str
    value: str  # 복호화된 값 (가능한 경우)
    encrypted: bool
    expires_utc: int
    is_secure: bool
    is_httponly: bool


class ChromeDataManager:
    """
    Chrome 데이터 백업/복원 관리자 (루팅 필요)

    쿠키 암호화 문제로 인해 직접 주입 대신
    Chrome 데이터 폴더 전체를 페르소나별로 관리합니다.

    사용 예시:
        manager = ChromeDataManager()

        # 현재 Chrome 데이터를 페르소나로 백업
        result = await manager.backup_for_persona(persona)

        # 페르소나의 Chrome 데이터 복원
        result = await manager.restore_for_persona(persona)

        # Chrome 데이터 초기화 (새 세션용)
        result = await manager.clear_chrome_data()
    """

    def __init__(self, device_serial: str = None):
        """
        Args:
            device_serial: ADB 디바이스 시리얼 (None이면 자동 감지)
        """
        self.device_serial = device_serial
        self._chrome_owner: Optional[str] = None

    # =========================================================================
    # ADB Commands
    # =========================================================================

    def _run_adb(self, *args, timeout: int = 60) -> Tuple[bool, str]:
        """ADB 명령 실행"""
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
                return (False, error)

            return (True, output)

        except subprocess.TimeoutExpired:
            logger.error(f"ADB command timeout: {' '.join(cmd)}")
            return (False, "Command timeout")
        except Exception as e:
            logger.error(f"ADB command error: {e}")
            return (False, str(e))

    def _run_as_root(self, shell_command: str, timeout: int = 60) -> Tuple[bool, str]:
        """루트 권한으로 쉘 명령 실행"""
        return self._run_adb("shell", f"su -c '{shell_command}'", timeout=timeout)

    async def _get_chrome_owner(self) -> str:
        """Chrome 앱 소유자 (uid) 확인"""
        if self._chrome_owner:
            return self._chrome_owner

        success, output = self._run_adb(
            "shell", "stat", "-c", "%U:%G", f"/data/data/{CHROME_PACKAGE}"
        )

        if success and ":" in output:
            self._chrome_owner = output.strip()
            logger.debug(f"Chrome owner: {self._chrome_owner}")
            return self._chrome_owner

        # 기본값
        self._chrome_owner = "u0_a264:u0_a264"
        return self._chrome_owner

    # =========================================================================
    # Chrome Control
    # =========================================================================

    async def stop_chrome(self) -> bool:
        """Chrome 앱 종료"""
        success, _ = self._run_adb("shell", "am", "force-stop", CHROME_PACKAGE)
        if success:
            logger.info("Chrome stopped")
            await asyncio.sleep(1)  # 완전히 종료될 때까지 대기
        return success

    async def start_chrome(self, url: str = None) -> bool:
        """Chrome 앱 실행"""
        if url:
            success, _ = self._run_adb(
                "shell", "am", "start",
                "-a", "android.intent.action.VIEW",
                "-d", url,
                CHROME_PACKAGE
            )
        else:
            success, _ = self._run_adb(
                "shell", "monkey",
                "-p", CHROME_PACKAGE,
                "-c", "android.intent.category.LAUNCHER", "1"
            )

        if success:
            logger.info(f"Chrome started{' with URL' if url else ''}")
            await asyncio.sleep(2)  # 앱 로딩 대기

        return success

    # =========================================================================
    # Data Backup
    # =========================================================================

    async def backup_for_persona(self, persona, force: bool = False) -> ChromeDataResult:
        """
        현재 Chrome 데이터를 페르소나용으로 백업

        Args:
            persona: Persona 객체
            force: 기존 백업 덮어쓰기 여부

        Returns:
            ChromeDataResult
        """
        from .persona import Persona

        if not isinstance(persona, Persona):
            return ChromeDataResult(
                success=False,
                operation="backup",
                error_message="Invalid persona object"
            )

        # 백업 경로
        backup_path = f"{PERSONAS_BASE_PATH}/{persona.persona_id}/chrome_data"

        # 기존 백업 확인
        if not force:
            success, _ = self._run_adb("shell", f"test -d {backup_path} && echo exists")
            if success and "exists" in _:
                logger.info(f"Backup already exists for persona: {persona.name}")
                # 기존 백업 사용
                persona.chrome_data_path = backup_path
                return ChromeDataResult(
                    success=True,
                    operation="backup",
                    path=backup_path,
                    error_message="Using existing backup"
                )

        # Chrome 종료
        await self.stop_chrome()

        # 백업 디렉토리 생성
        self._run_adb("shell", f"mkdir -p {PERSONAS_BASE_PATH}/{persona.persona_id}")

        # Chrome 데이터 복사 (루팅 필요)
        logger.info(f"Backing up Chrome data for persona: {persona.name}")

        # 기존 백업 삭제
        self._run_as_root(f"rm -rf {backup_path}")

        # 복사
        success, output = self._run_as_root(
            f"cp -r {CHROME_DATA_PATH} {backup_path}"
        )

        if not success:
            return ChromeDataResult(
                success=False,
                operation="backup",
                error_message=f"Failed to copy Chrome data: {output}"
            )

        # 권한 설정 (일반 사용자가 접근 가능하도록)
        self._run_as_root(f"chmod -R 755 {backup_path}")

        # 크기 확인
        success, output = self._run_adb("shell", f"du -s {backup_path}")
        size_bytes = 0
        if success:
            try:
                size_bytes = int(output.split()[0]) * 1024  # du 출력은 KB 단위
            except (ValueError, IndexError):
                pass

        # 페르소나에 경로 저장
        persona.chrome_data_path = backup_path

        logger.info(f"Chrome data backed up: {backup_path} ({size_bytes / 1024 / 1024:.1f} MB)")

        return ChromeDataResult(
            success=True,
            operation="backup",
            path=backup_path,
            size_bytes=size_bytes
        )

    # =========================================================================
    # Data Restore
    # =========================================================================

    async def restore_for_persona(self, persona) -> ChromeDataResult:
        """
        페르소나의 Chrome 데이터 복원

        Args:
            persona: Persona 객체

        Returns:
            ChromeDataResult
        """
        from .persona import Persona

        if not isinstance(persona, Persona):
            return ChromeDataResult(
                success=False,
                operation="restore",
                error_message="Invalid persona object"
            )

        backup_path = persona.chrome_data_path or f"{PERSONAS_BASE_PATH}/{persona.persona_id}/chrome_data"

        # 백업 존재 확인
        success, output = self._run_adb("shell", f"test -d {backup_path} && echo exists")
        if not success or "exists" not in output:
            logger.warning(f"No backup found for persona: {persona.name}")
            return ChromeDataResult(
                success=False,
                operation="restore",
                error_message=f"Backup not found: {backup_path}"
            )

        # Chrome 종료
        await self.stop_chrome()

        # 현재 Chrome 데이터 삭제
        logger.info(f"Restoring Chrome data for persona: {persona.name}")
        self._run_as_root(f"rm -rf {CHROME_DATA_PATH}")

        # 백업에서 복원
        success, output = self._run_as_root(
            f"cp -r {backup_path} {CHROME_DATA_PATH}"
        )

        if not success:
            return ChromeDataResult(
                success=False,
                operation="restore",
                error_message=f"Failed to restore Chrome data: {output}"
            )

        # 소유권 복원
        owner = await self._get_chrome_owner()
        self._run_as_root(f"chown -R {owner} {CHROME_DATA_PATH}")
        self._run_as_root(f"chmod -R 700 {CHROME_DATA_PATH}")

        # 쿠키 DB 권한 조정
        self._run_as_root(f"chmod 600 {CHROME_COOKIES_DB}")

        logger.info(f"Chrome data restored from: {backup_path}")

        return ChromeDataResult(
            success=True,
            operation="restore",
            path=backup_path
        )

    # =========================================================================
    # Data Clear
    # =========================================================================

    async def clear_chrome_data(self) -> ChromeDataResult:
        """
        Chrome 데이터 초기화 (새 세션용)

        pm clear를 사용하여 앱 데이터 전체 삭제
        """
        await self.stop_chrome()

        logger.info("Clearing Chrome data...")
        success, output = self._run_adb("shell", "pm", "clear", CHROME_PACKAGE)

        if success and "Success" in output:
            logger.info("Chrome data cleared successfully")
            return ChromeDataResult(success=True, operation="clear")
        else:
            return ChromeDataResult(
                success=False,
                operation="clear",
                error_message=f"Failed to clear Chrome data: {output}"
            )

    async def clear_cookies_only(self) -> ChromeDataResult:
        """
        Chrome 쿠키만 삭제 (루팅 필요)

        앱 데이터는 유지하고 쿠키 DB만 삭제
        """
        await self.stop_chrome()

        logger.info("Clearing Chrome cookies only...")

        # 쿠키 DB 삭제
        success, output = self._run_as_root(f"rm -f {CHROME_COOKIES_DB}")

        if success:
            logger.info("Chrome cookies cleared")
            return ChromeDataResult(success=True, operation="clear_cookies")
        else:
            return ChromeDataResult(
                success=False,
                operation="clear_cookies",
                error_message=f"Failed to clear cookies: {output}"
            )

    # =========================================================================
    # Cookie Inspection
    # =========================================================================

    async def get_naver_cookies(self) -> List[CookieInfo]:
        """
        네이버 쿠키 조회 (루팅 필요)

        참고: value는 대부분 비어있고 encrypted_value에 암호화된 값이 있음

        Returns:
            네이버 관련 쿠키 목록
        """
        await self.stop_chrome()

        # 쿠키 DB를 임시 위치로 복사
        temp_path = "/data/local/tmp/cookies_temp.db"
        self._run_as_root(f"cp {CHROME_COOKIES_DB} {temp_path}")
        self._run_as_root(f"chmod 644 {temp_path}")

        # SQLite 쿼리
        query = "SELECT name, host_key, value, expires_utc, is_secure, is_httponly FROM cookies WHERE host_key LIKE '%naver%'"
        success, output = self._run_adb(
            "shell", f"sqlite3 {temp_path} \"{query}\""
        )

        # 임시 파일 삭제
        self._run_adb("shell", f"rm -f {temp_path}")

        cookies = []
        if success and output:
            for line in output.strip().split('\n'):
                parts = line.split('|')
                if len(parts) >= 6:
                    cookies.append(CookieInfo(
                        name=parts[0],
                        host_key=parts[1],
                        value=parts[2],
                        encrypted=not bool(parts[2]),  # value가 비어있으면 암호화됨
                        expires_utc=int(parts[3]) if parts[3] else 0,
                        is_secure=parts[4] == "1",
                        is_httponly=parts[5] == "1"
                    ))

        logger.info(f"Found {len(cookies)} Naver cookies")
        return cookies

    async def get_nnb_cookie(self) -> Optional[str]:
        """
        NNB 쿠키 값 조회

        NNB는 네이버의 주요 디바이스 식별자 쿠키
        (암호화된 경우 복호화 불가)
        """
        cookies = await self.get_naver_cookies()
        for cookie in cookies:
            if cookie.name == "NNB":
                if cookie.value:
                    return cookie.value
                else:
                    logger.warning("NNB cookie is encrypted")
                    return None
        return None

    # =========================================================================
    # Persona Integration
    # =========================================================================

    async def switch_to_persona(self, persona) -> ChromeDataResult:
        """
        페르소나로 전환 (Chrome 데이터 복원)

        1. Chrome 종료
        2. Chrome 데이터 복원
        3. (옵션) Chrome 시작

        Args:
            persona: Persona 객체

        Returns:
            ChromeDataResult
        """
        result = await self.restore_for_persona(persona)

        if result.success:
            logger.info(f"Switched to persona: {persona.name}")

        return result

    async def save_current_to_persona(self, persona, force: bool = False) -> ChromeDataResult:
        """
        현재 상태를 페르소나에 저장

        Args:
            persona: Persona 객체
            force: 기존 백업 덮어쓰기

        Returns:
            ChromeDataResult
        """
        return await self.backup_for_persona(persona, force=force)

    # =========================================================================
    # Utilities
    # =========================================================================

    async def get_data_size(self) -> int:
        """현재 Chrome 데이터 크기 (bytes)"""
        success, output = self._run_as_root(f"du -s {CHROME_DATA_PATH}")
        if success:
            try:
                return int(output.split()[0]) * 1024
            except (ValueError, IndexError):
                pass
        return 0

    async def list_persona_backups(self) -> List[Dict[str, Any]]:
        """저장된 페르소나 백업 목록"""
        success, output = self._run_adb("shell", f"ls -la {PERSONAS_BASE_PATH}")

        backups = []
        if success and output:
            for line in output.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 8 and parts[0].startswith('d'):
                    persona_id = parts[-1]
                    if persona_id not in ['.', '..']:
                        # 크기 확인
                        _, size_output = self._run_adb(
                            "shell", f"du -s {PERSONAS_BASE_PATH}/{persona_id}/chrome_data"
                        )
                        size = 0
                        if size_output:
                            try:
                                size = int(size_output.split()[0]) * 1024
                            except (ValueError, IndexError):
                                pass

                        backups.append({
                            "persona_id": persona_id,
                            "path": f"{PERSONAS_BASE_PATH}/{persona_id}/chrome_data",
                            "size_bytes": size
                        })

        return backups

    async def delete_persona_backup(self, persona_id: str) -> bool:
        """페르소나 백업 삭제"""
        backup_path = f"{PERSONAS_BASE_PATH}/{persona_id}"
        success, _ = self._run_adb("shell", f"rm -rf {backup_path}")
        if success:
            logger.info(f"Deleted backup for persona: {persona_id[:8]}...")
        return success
