"""
Supabase 페르소나 선택 액션
"""

import random
import logging
from typing import Dict, Any, Optional

from ...core.action_base import CampaignAction, ActionResult


logger = logging.getLogger("persona_selector")


class PersonaSelectorAction(CampaignAction):
    """Supabase에서 랜덤 페르소나 선택"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.max_retries = self.config.get("max_retries", 10)

    async def execute(self, context: Dict[str, Any]) -> ActionResult:
        """페르소나 선택 실행"""
        sb = self.get_context_value("supabase_client")
        used_ids = self.get_context_value("used_persona_ids", set())

        if not sb:
            return ActionResult(
                success=False,
                error_message="Supabase 클라이언트 없음"
            )

        persona = await self._fetch_random_persona(sb, used_ids)

        if not persona:
            return ActionResult(
                success=False,
                error_message="사용 가능한 페르소나 없음"
            )

        # 페르소나 정보 추출
        device_config = persona.get("device_config", {})
        android_id = device_config.get("android_id", "")
        persona_name = persona.get("name", "unknown")
        persona_id = persona["id"]
        behavior = persona.get("behavior_profile", {})
        location = persona.get("location", {})

        # 검증
        if not android_id or len(android_id) != 16:
            return ActionResult(
                success=False,
                error_message=f"잘못된 android_id: {android_id}"
            )

        # used_ids에 추가
        if isinstance(used_ids, set):
            used_ids.add(persona_id)

        logger.info(
            f"페르소나 선택: ID={android_id[:8]} name={persona_name} "
            f"loc={location.get('region', '?')}"
        )

        return ActionResult(
            success=True,
            data={
                "persona": persona,
                "persona_id": persona_id,
                "persona_name": persona_name,
                "android_id": android_id,
                "behavior_profile": behavior,
                "location": location,
                "device_config": device_config,
            }
        )

    async def _fetch_random_persona(
        self,
        sb,
        used_ids: set,
    ) -> Optional[Dict[str, Any]]:
        """Supabase에서 중복 없이 랜덤 페르소나 가져오기"""
        # 전체 idle 페르소나 수 조회
        count_resp = (
            sb.table("personas")
            .select("id", count="exact")
            .eq("status", "idle")
            .execute()
        )
        total = count_resp.count or 0

        if total == 0:
            logger.error("idle 페르소나 없음")
            return None

        # 랜덤 오프셋으로 중복 회피
        for _ in range(self.max_retries):
            offset = random.randint(0, max(0, total - 1))
            resp = (
                sb.table("personas")
                .select("*")
                .eq("status", "idle")
                .range(offset, offset)
                .execute()
            )
            if resp.data and resp.data[0]["id"] not in used_ids:
                return resp.data[0]

        # 최대 재시도 초과 시 아무거나 반환
        if resp and resp.data:
            return resp.data[0]
        return None
