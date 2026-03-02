"""
PersonaManager - 통합 페르소나 관리자

모든 페르소나 관련 컴포넌트를 통합하여
원스톱으로 페르소나 전환을 처리합니다.

Author: Naver AI Evolution System
Created: 2025-12-15
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any

from .persona import Persona, BehaviorProfile, VisitRecord, PersonaStatus
from .persona_store import PersonaStore
from .device_identity import DeviceIdentityManager, IdentityChangeResult
from .chrome_data import ChromeDataManager, ChromeDataResult

logger = logging.getLogger("naver_evolution.persona_manager")


@dataclass
class PersonaSwitchResult:
    """페르소나 전환 결과"""
    success: bool
    persona: Optional[Persona] = None
    identity_changed: bool = False
    chrome_data_restored: bool = False
    error_message: Optional[str] = None
    duration_sec: float = 0.0


class PersonaManager:
    """
    통합 페르소나 관리자

    페르소나 시스템의 모든 기능을 통합:
    - 페르소나 저장/조회 (PersonaStore)
    - ANDROID_ID 변경 (DeviceIdentityManager)
    - Chrome 데이터 관리 (ChromeDataManager)

    사용 예시:
        manager = PersonaManager()

        # 새 페르소나 생성
        persona = manager.create_persona("직장인_30대")

        # 페르소나로 전환
        result = await manager.switch_to_persona(persona)

        # 세션 종료 시 저장
        await manager.save_current_session(persona)

        # 다음 세션을 위해 페르소나 선택
        next_persona = manager.select_next_persona()
    """

    def __init__(
        self,
        db_path: str = "data/personas.db",
        device_serial: str = None
    ):
        """
        Args:
            db_path: 페르소나 DB 경로
            device_serial: ADB 디바이스 시리얼
        """
        self.store = PersonaStore(db_path)
        self.identity_manager = DeviceIdentityManager(device_serial)
        self.chrome_manager = ChromeDataManager(device_serial)
        self._current_persona: Optional[Persona] = None

    # =========================================================================
    # Persona CRUD
    # =========================================================================

    def create_persona(
        self,
        name: str,
        tags: List[str] = None,
        behavior_profile: BehaviorProfile = None
    ) -> Persona:
        """
        새 페르소나 생성

        Args:
            name: 페르소나 이름
            tags: 태그 목록
            behavior_profile: 행동 프로필 (None이면 랜덤 생성)

        Returns:
            생성된 Persona
        """
        persona = self.store.create_persona(name, tags, behavior_profile)
        logger.info(f"Created persona: {persona.name}")
        return persona

    def get_persona(self, persona_id: str) -> Optional[Persona]:
        """ID로 페르소나 조회"""
        return self.store.get(persona_id)

    def get_all_personas(self) -> List[Persona]:
        """모든 페르소나 조회"""
        return self.store.get_all()

    def update_persona(self, persona: Persona):
        """페르소나 업데이트"""
        self.store.update(persona)

    def delete_persona(self, persona_id: str) -> bool:
        """페르소나 삭제"""
        return self.store.delete(persona_id)

    # =========================================================================
    # Persona Selection
    # =========================================================================

    def select_next_persona(self, strategy: str = "least_recent") -> Optional[Persona]:
        """
        다음 사용할 페르소나 선택

        Args:
            strategy: 선택 전략
                - least_recent: 가장 오래 활동 안 한 것
                - round_robin: 순차
                - random: 랜덤
                - needs_revisit: 재방문 필요한 것
                - lowest_sessions: 세션 수 가장 적은 것

        Returns:
            선택된 Persona
        """
        return self.store.select_persona(strategy)

    @property
    def current_persona(self) -> Optional[Persona]:
        """현재 활성 페르소나"""
        return self._current_persona

    # =========================================================================
    # Persona Switching
    # =========================================================================

    async def switch_to_persona(self, persona: Persona) -> PersonaSwitchResult:
        """
        페르소나로 전환

        1. Chrome 종료
        2. ANDROID_ID 변경 (루팅 필요)
        3. Chrome 데이터 복원
        4. 페르소나 상태 업데이트

        Args:
            persona: 전환할 Persona

        Returns:
            PersonaSwitchResult
        """
        import time
        start_time = time.time()

        logger.info(f"Switching to persona: {persona.name}")

        # 1. 루팅 확인
        try:
            await self.identity_manager.ensure_root()
        except PermissionError as e:
            return PersonaSwitchResult(
                success=False,
                error_message=str(e)
            )

        # 2. Chrome 종료
        await self.chrome_manager.stop_chrome()

        # 3. ANDROID_ID 변경
        identity_result = await self.identity_manager.apply_persona_identity(persona)

        if not identity_result.success:
            return PersonaSwitchResult(
                success=False,
                persona=persona,
                error_message=f"Failed to change ANDROID_ID: {identity_result.error_message}"
            )

        # 4. Chrome 데이터 복원 (백업이 있는 경우)
        chrome_result = ChromeDataResult(success=True, operation="skip")

        if persona.chrome_data_path:
            chrome_result = await self.chrome_manager.restore_for_persona(persona)

            if not chrome_result.success:
                logger.warning(f"Chrome data restore failed: {chrome_result.error_message}")
                # 실패해도 계속 진행 (첫 방문으로 처리)

        # 5. 페르소나 상태 업데이트
        persona.start_session()
        self.store.update(persona)
        self._current_persona = persona

        duration = time.time() - start_time

        logger.info(f"Switched to persona: {persona.name} ({duration:.1f}s)")

        return PersonaSwitchResult(
            success=True,
            persona=persona,
            identity_changed=identity_result.success,
            chrome_data_restored=chrome_result.success,
            duration_sec=duration
        )

    async def switch_to_persona_by_id(self, persona_id: str) -> PersonaSwitchResult:
        """ID로 페르소나 전환"""
        persona = self.store.get(persona_id)
        if not persona:
            return PersonaSwitchResult(
                success=False,
                error_message=f"Persona not found: {persona_id}"
            )
        return await self.switch_to_persona(persona)

    async def switch_to_next(self, strategy: str = "least_recent") -> PersonaSwitchResult:
        """다음 페르소나로 전환"""
        persona = self.select_next_persona(strategy)
        if not persona:
            return PersonaSwitchResult(
                success=False,
                error_message="No available persona"
            )
        return await self.switch_to_persona(persona)

    # =========================================================================
    # Session Management
    # =========================================================================

    async def save_current_session(
        self,
        persona: Persona = None,
        cooldown_minutes: int = 30
    ) -> ChromeDataResult:
        """
        현재 세션 저장 및 종료

        1. Chrome 데이터 백업
        2. 페르소나 상태 업데이트
        3. 쿨다운 시작

        Args:
            persona: 저장할 Persona (None이면 현재 페르소나)
            cooldown_minutes: 쿨다운 시간 (분)

        Returns:
            ChromeDataResult
        """
        persona = persona or self._current_persona

        if not persona:
            return ChromeDataResult(
                success=False,
                operation="save_session",
                error_message="No active persona"
            )

        logger.info(f"Saving session for persona: {persona.name}")

        # 1. Chrome 데이터 백업
        result = await self.chrome_manager.backup_for_persona(persona, force=True)

        if not result.success:
            logger.warning(f"Chrome data backup failed: {result.error_message}")

        # 2. 페르소나 상태 업데이트
        persona.end_session(cooldown_minutes)
        self.store.update(persona)

        # 3. 현재 페르소나 해제
        if self._current_persona and self._current_persona.persona_id == persona.persona_id:
            self._current_persona = None

        logger.info(f"Session saved. Cooldown: {cooldown_minutes} min")

        return result

    def add_visit_record(
        self,
        persona: Persona,
        url: str,
        domain: str = "",
        content_type: str = "unknown",
        dwell_time: int = 0,
        scroll_depth: float = 0.0,
        actions: List[str] = None
    ):
        """방문 기록 추가"""
        record = VisitRecord(
            url=url,
            domain=domain or self._extract_domain(url),
            content_type=content_type,
            dwell_time=dwell_time,
            scroll_depth=scroll_depth,
            actions=actions or []
        )

        persona.add_visit(record)
        self.store.update(persona)

        # DB에도 별도 저장
        self.store.add_visit_record(
            persona.persona_id,
            url, domain, content_type,
            dwell_time, scroll_depth, actions
        )

    def _extract_domain(self, url: str) -> str:
        """URL에서 도메인 추출"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ""

    # =========================================================================
    # Batch Operations
    # =========================================================================

    def create_personas_batch(
        self,
        count: int,
        name_prefix: str = "Persona",
        tags: List[str] = None
    ) -> List[Persona]:
        """
        여러 페르소나 일괄 생성

        Args:
            count: 생성할 수
            name_prefix: 이름 접두사
            tags: 공통 태그

        Returns:
            생성된 Persona 목록
        """
        personas = []

        for i in range(count):
            name = f"{name_prefix}_{i + 1:02d}"
            persona = self.create_persona(name, tags)
            personas.append(persona)

        logger.info(f"Created {count} personas with prefix '{name_prefix}'")
        return personas

    async def initialize_all_personas(self) -> Dict[str, bool]:
        """
        모든 페르소나 초기화 (첫 방문 시뮬레이션)

        각 페르소나로 전환 후 네이버 접속하여
        NNB 쿠키를 생성하고 저장합니다.

        Returns:
            {persona_id: 성공여부} 딕셔너리
        """
        results = {}
        personas = self.get_all_personas()

        for persona in personas:
            logger.info(f"Initializing persona: {persona.name}")

            # 페르소나로 전환
            switch_result = await self.switch_to_persona(persona)

            if switch_result.success:
                # Chrome 시작 (네이버 접속)
                await self.chrome_manager.start_chrome("https://www.naver.com")
                await asyncio.sleep(5)  # 페이지 로드 대기

                # 세션 저장
                await self.save_current_session(persona, cooldown_minutes=1)
                results[persona.persona_id] = True
            else:
                results[persona.persona_id] = False

        return results

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """전체 통계"""
        stats = self.store.get_stats()
        stats["current_persona"] = self._current_persona.name if self._current_persona else None
        return stats

    def get_persona_stats(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """개별 페르소나 통계"""
        persona = self.store.get(persona_id)
        if not persona:
            return None

        return {
            "persona_id": persona.persona_id,
            "name": persona.name,
            "status": persona.status.value,
            "total_sessions": persona.total_sessions,
            "total_pageviews": persona.total_pageviews,
            "total_dwell_time_min": persona.total_dwell_time / 60,
            "avg_dwell_time": persona.avg_session_dwell_time,
            "visit_count": persona.visit_count,
            "last_active": persona.last_active.isoformat(),
            "created_at": persona.created_at.isoformat(),
            "behavior_profile": persona.behavior_profile.to_dict(),
        }

    # =========================================================================
    # Device Status
    # =========================================================================

    async def check_device_status(self) -> Dict[str, Any]:
        """디바이스 상태 확인"""
        identity = await self.identity_manager.get_current_identity()

        # 현재 페르소나와 일치하는지 확인
        persona_match = False
        if self._current_persona and identity.get("android_id"):
            persona_match = identity["android_id"] == self._current_persona.android_id

        return {
            "is_rooted": identity.get("is_rooted", False),
            "android_id": identity.get("android_id"),
            "advertising_id": identity.get("advertising_id"),
            "current_persona": self._current_persona.name if self._current_persona else None,
            "persona_match": persona_match,
        }

    async def verify_persona_active(self, persona: Persona = None) -> bool:
        """페르소나가 실제로 적용되어 있는지 확인"""
        persona = persona or self._current_persona
        if not persona:
            return False

        current_id = await self.identity_manager.get_android_id()
        return current_id == persona.android_id
