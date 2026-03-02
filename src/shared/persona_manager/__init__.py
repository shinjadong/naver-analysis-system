"""
PersonaManager - 가상 사용자 페르소나 관리 시스템

루팅된 디바이스에서 ANDROID_ID 및 Chrome 데이터를 관리하여
네이버에 "재방문자"로 인식되도록 합니다.

Components:
- Persona, BehaviorProfile: 데이터 구조
- PersonaStore: SQLite 기반 저장소
- DeviceIdentityManager: ANDROID_ID 변경 (루팅 필요)
- ChromeDataManager: Chrome 데이터 백업/복원 (루팅 필요)
- PersonaManager: 통합 관리자

Author: Naver AI Evolution System
Created: 2025-12-15
"""

from .persona import (
    Persona,
    BehaviorProfile,
    VisitRecord,
    PersonaStatus,
)
from .persona_store import PersonaStore
from .device_identity import DeviceIdentityManager
from .chrome_data import ChromeDataManager
from .manager import PersonaManager, PersonaSwitchResult

__all__ = [
    # Data classes
    "Persona",
    "BehaviorProfile",
    "VisitRecord",
    "PersonaStatus",
    "PersonaSwitchResult",
    # Managers
    "PersonaStore",
    "DeviceIdentityManager",
    "ChromeDataManager",
    "PersonaManager",
]

__version__ = "0.1.0"
