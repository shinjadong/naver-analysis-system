"""
Supabase 로깅 액션
"""

import logging
from datetime import datetime
from typing import Dict, Any

from ...core.action_base import CampaignAction, ActionResult


logger = logging.getLogger("supabase_logger")


class SupabaseLoggerAction(CampaignAction):
    """Supabase에 방문 기록 저장"""

    async def execute(self, context: Dict[str, Any]) -> ActionResult:
        """Supabase 로깅 실행"""
        sb = self.get_context_value("supabase_client")
        persona_id = self.get_context_value("persona_id")
        device_serial = self.get_context_value("device_serial")
        keyword = self.get_context_value("keyword")
        target_url = self.get_context_value("target_url")

        # 체류 결과
        dwell_sec = self.get_context_value("dwell_sec", 0)
        scroll_count = self.get_context_value("scroll_count", 0)
        scroll_depth = self.get_context_value("scroll_depth", 0.0)

        if not sb or not persona_id:
            return ActionResult(
                success=False,
                error_message="supabase_client 또는 persona_id 없음"
            )

        try:
            now = datetime.now().isoformat()

            # 페르소나 통계 업데이트
            cur = (
                sb.table("personas")
                .select("total_sessions, total_dwell_time")
                .eq("id", persona_id)
                .execute()
            )

            update_data = {
                "last_active_at": now,
                "updated_at": now
            }

            if cur.data:
                update_data["total_sessions"] = (cur.data[0].get("total_sessions") or 0) + 1
                update_data["total_dwell_time"] = (cur.data[0].get("total_dwell_time") or 0) + dwell_sec

            sb.table("personas").update(update_data).eq("id", persona_id).execute()

            # persona_sessions 기록
            sb.table("persona_sessions").insert({
                "persona_id": persona_id,
                "device_serial": device_serial,
                "mission": {
                    "type": "blog_boost",
                    "keyword": keyword,
                    "blog_url": target_url,
                },
                "success": True,
                "duration_sec": dwell_sec,
                "scroll_count": scroll_count,
                "scroll_depth": float(scroll_depth),
                "started_at": now,
                "completed_at": now,
                "status": "completed",
                "campaign_type": "traffic",
            }).execute()

            logger.info(f"Supabase 로깅 완료: persona_id={persona_id}")

            return ActionResult(success=True)

        except Exception as e:
            return ActionResult(
                success=False,
                error_message=f"Supabase 로깅 실패: {str(e)}"
            )
