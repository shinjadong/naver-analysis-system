"""
디바이스 관리자 모듈
ADB를 통한 안드로이드 디바이스 통합 관리
모든 입력은 EnhancedAdbTools를 통해 휴먼라이크로 수행
"""
import subprocess
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
from enum import Enum

from ..device_tools import EnhancedAdbTools, AdbConfig


class DeviceType(Enum):
    """디바이스 타입"""
    EMULATOR = "emulator"
    PHYSICAL = "physical"
    UNKNOWN = "unknown"


class DeviceStatus(Enum):
    """디바이스 상태"""
    ONLINE = "online"
    OFFLINE = "offline"
    UNAUTHORIZED = "unauthorized"
    BOOTING = "booting"


@dataclass
class DeviceInfo:
    """디바이스 정보"""
    serial: str
    device_type: DeviceType
    status: DeviceStatus
    model: str = ""
    android_version: str = ""
    fingerprint: Dict = field(default_factory=dict)
    
    @property
    def is_available(self) -> bool:
        """사용 가능 여부"""
        return self.status == DeviceStatus.ONLINE


class DeviceManager:
    """디바이스 관리자 (EnhancedAdbTools 기반 휴먼라이크 입력)"""

    def __init__(self, adb_path: Optional[str] = None):
        self.adb_path = adb_path or self._find_adb()
        self.devices: Dict[str, DeviceInfo] = {}
        self.logger = logging.getLogger("DeviceManager")
        # EnhancedAdbTools 캐시 (디바이스별)
        self._adb_tools: Dict[str, EnhancedAdbTools] = {}
    
    def _find_adb(self) -> str:
        """ADB 경로 자동 탐색"""
        import platform
        import os
        
        if platform.system() == "Windows":
            # Windows 기본 경로들
            paths = [
                Path(os.environ.get("LOCALAPPDATA", "")) / "Android/Sdk/platform-tools/adb.exe",
                Path("C:/Android/sdk/platform-tools/adb.exe"),
                Path("C:/Program Files/Android/platform-tools/adb.exe"),
            ]
            for p in paths:
                if p.exists():
                    return str(p)
        
        # 시스템 PATH에서 찾기
        return "adb"

    def _run_adb(self, args: List[str], serial: Optional[str] = None) -> subprocess.CompletedProcess:
        """ADB 명령 실행"""
        cmd = [self.adb_path]
        if serial:
            cmd.extend(["-s", serial])
        cmd.extend(args)
        
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    def discover_devices(self) -> List[DeviceInfo]:
        """연결된 디바이스 탐색"""
        self.devices.clear()
        
        try:
            result = self._run_adb(["devices", "-l"])
            lines = result.stdout.strip().split('\n')[1:]  # 헤더 제외
            
            for line in lines:
                if not line.strip():
                    continue
                    
                parts = line.split()
                if len(parts) < 2:
                    continue
                    
                serial = parts[0]
                status_str = parts[1]
                
                # 상태 파싱
                status = DeviceStatus.UNKNOWN
                if status_str == "device":
                    status = DeviceStatus.ONLINE
                elif status_str == "offline":
                    status = DeviceStatus.OFFLINE
                elif status_str == "unauthorized":
                    status = DeviceStatus.UNAUTHORIZED
                
                # 디바이스 타입 판별
                device_type = DeviceType.EMULATOR if "emulator" in serial else DeviceType.PHYSICAL
                
                # 상세 정보 수집
                model = ""
                for part in parts[2:]:
                    if part.startswith("model:"):
                        model = part.split(":")[1]
                        break
                
                device = DeviceInfo(
                    serial=serial,
                    device_type=device_type,
                    status=status,
                    model=model
                )
                self.devices[serial] = device
                
        except subprocess.TimeoutExpired:
            self.logger.error("ADB devices 명령 타임아웃")
        except Exception as e:
            self.logger.error(f"디바이스 탐색 실패: {e}")
        
        self.logger.info(f"발견된 디바이스: {len(self.devices)}대")
        return list(self.devices.values())
    
    def execute_command(self, serial: str, command: str) -> str:
        """디바이스에서 셸 명령 실행"""
        try:
            result = self._run_adb(["shell", command], serial=serial)
            return result.stdout.strip()
        except Exception as e:
            self.logger.error(f"명령 실행 실패 ({serial}): {e}")
            return ""

    def _get_adb_tools(self, serial: str) -> EnhancedAdbTools:
        """디바이스별 EnhancedAdbTools 인스턴스 반환"""
        if serial not in self._adb_tools:
            config = AdbConfig(serial=serial)
            self._adb_tools[serial] = EnhancedAdbTools(config)
        return self._adb_tools[serial]

    async def tap_async(self, serial: str, x: int, y: int) -> bool:
        """화면 탭 (EnhancedAdbTools 휴먼라이크)"""
        tools = self._get_adb_tools(serial)
        result = await tools.tap(x, y)
        return result.success

    async def swipe_async(self, serial: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        """스와이프 (EnhancedAdbTools 휴먼라이크)"""
        tools = self._get_adb_tools(serial)
        result = await tools.swipe(x1, y1, x2, y2, duration_ms)
        return result.success

    async def input_text_async(self, serial: str, text: str) -> bool:
        """텍스트 입력 (EnhancedAdbTools 휴먼라이크)"""
        tools = self._get_adb_tools(serial)
        result = await tools.input_text(text)
        return result.success

    def tap(self, serial: str, x: int, y: int) -> bool:
        """화면 탭 (동기 래퍼 - EnhancedAdbTools 휴먼라이크)"""
        return asyncio.get_event_loop().run_until_complete(self.tap_async(serial, x, y))

    def swipe(self, serial: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        """스와이프 (동기 래퍼 - EnhancedAdbTools 휴먼라이크)"""
        return asyncio.get_event_loop().run_until_complete(self.swipe_async(serial, x1, y1, x2, y2, duration_ms))

    def input_text(self, serial: str, text: str) -> bool:
        """텍스트 입력 (동기 래퍼 - EnhancedAdbTools 휴먼라이크)"""
        return asyncio.get_event_loop().run_until_complete(self.input_text_async(serial, text))


# 싱글톤 인스턴스
_manager: Optional[DeviceManager] = None

def get_device_manager() -> DeviceManager:
    """디바이스 관리자 인스턴스 반환"""
    global _manager
    if _manager is None:
        _manager = DeviceManager()
    return _manager
