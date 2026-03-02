"""
Supabase 페르소나 관리
"""

import logging
import os
import random
from datetime import datetime
from typing import Optional, Dict, Any

from supabase import create_client

from .config import DEVICE_SERIAL, BLOG_URL

logger = logging.getLogger("boost")

# 페르소나 Supabase 프로젝트 (pkehcfbjotctvneordob)
PERSONA_SUPABASE_URL = "https://pkehcfbjotctvneordob.supabase.co"
PERSONA_SUPABASE_KEY = os.getenv(
    "PERSONA_SUPABASE_SERVICE_KEY",
    os.getenv("SUPABASE_SERVICE_KEY_PERSONA", ""),
)


def get_supabase():
    """페르소나 Supabase 클라이언트 생성"""
    url = os.getenv("PERSONA_SUPABASE_URL", PERSONA_SUPABASE_URL)
    key = os.getenv("PERSONA_SUPABASE_SERVICE_KEY", PERSONA_SUPABASE_KEY)
    if not key:
        key = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBrZWhjZmJqb3RjdHZuZW9yZG9iIiwi"
            "cm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzE5MjY4MSwiZXhwIjoyMDY4"
            "NzY4NjgxfQ.fn1IxRxjJZ6gihy_SCvyQrT6Vx3xb1yMaVzztOsLeyk"
        )
    return create_client(url, key)


def fetch_random_persona(
    sb,
    used_ids: set = None,
    max_retries: int = 10,
) -> Optional[Dict[str, Any]]:
    """Supabase에서 중복 없이 랜덤 페르소나 1개 가져오기"""
    if used_ids is None:
        used_ids = set()

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

    resp = None
    for _ in range(max_retries):
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

    if resp and resp.data:
        return resp.data[0]
    return None


def update_persona_after_visit(
    sb,
    persona_id: str,
    dwell_sec: int,
    scroll_count: int,
    scroll_depth: float,
    success: bool,
    keyword: str,
):
    """방문 후 Supabase 페르소나 통계 업데이트 + persona_sessions 기록"""
    now = datetime.now().isoformat()

    update_data = {"last_active_at": now, "updated_at": now}
    if success:
        cur = (
            sb.table("personas")
            .select("total_sessions, total_dwell_time")
            .eq("id", persona_id)
            .execute()
        )
        if cur.data:
            update_data["total_sessions"] = (cur.data[0].get("total_sessions") or 0) + 1
            update_data["total_dwell_time"] = (cur.data[0].get("total_dwell_time") or 0) + dwell_sec
    sb.table("personas").update(update_data).eq("id", persona_id).execute()

    sb.table("persona_sessions").insert({
        "persona_id": persona_id,
        "device_serial": DEVICE_SERIAL,
        "mission": {
            "type": "blog_boost",
            "keyword": keyword,
            "blog_url": BLOG_URL,
        },
        "success": success,
        "duration_sec": dwell_sec,
        "scroll_count": scroll_count,
        "scroll_depth": float(scroll_depth),
        "started_at": now,
        "completed_at": now,
        "status": "completed" if success else "failed",
        "campaign_type": "traffic",
    }).execute()
