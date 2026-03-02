"""
휴먼라이크 체류 시뮬레이션
"""

import asyncio
import logging
import random
import time
from typing import Dict, Any, Tuple

from src.shared.device_tools.adb_enhanced import EnhancedAdbTools

from .config import MIN_DWELL, MAX_DWELL

logger = logging.getLogger("boost")


async def simulate_dwell(
    adb_tools: EnhancedAdbTools,
    behavior: Dict[str, Any],
) -> Tuple[int, int, float]:
    """
    Supabase behavior_profile 기반 휴먼라이크 체류 시뮬레이션

    behavior 구조:
        scroll_speed: float (0.5~2.0)
        avg_dwell_time: int (초)
        pause_probability: float (0~0.5)
    """
    scroll_speed = behavior.get("scroll_speed", 1.0)
    avg_dwell = behavior.get("avg_dwell_time", 120)
    pause_prob = behavior.get("pause_probability", 0.2)

    dwell_sec = random.randint(
        max(MIN_DWELL, int(avg_dwell * 0.6)),
        min(MAX_DWELL, int(avg_dwell * 1.4)),
    )

    scroll_interval = max(2, int(4 / scroll_speed))
    num_scrolls = max(4, dwell_sec // scroll_interval)

    start = time.time()
    scroll_count = 0
    max_scroll_y = 0

    sw = adb_tools.config.screen_width or 1080
    sh = adb_tools.config.screen_height or 2400
    center_x = sw // 2

    await asyncio.sleep(random.uniform(1, 2.5))

    for i in range(num_scrolls):
        elapsed = time.time() - start
        if elapsed >= dwell_sec:
            break

        roll = random.random()

        if roll < 0.15 and scroll_count > 2:
            dist = random.randint(200, 400)
            start_y = int(sh * 0.3)
            dur = random.randint(300, 600)
            await adb_tools.swipe(
                center_x, start_y, center_x, start_y + dist,
                duration_ms=dur, use_curved_path=False,
            )
        elif roll < 0.25 and scroll_count > 0:
            await asyncio.sleep(random.uniform(1.5, 4))
        else:
            dist = random.randint(300, 700)
            start_y = int(sh * 0.7)
            dur = random.randint(300, 600)
            await adb_tools.swipe(
                center_x, start_y, center_x, start_y - dist,
                duration_ms=dur, use_curved_path=False,
            )
            scroll_count += 1
            max_scroll_y += dist

        pause_base = scroll_interval + random.uniform(-1, 1)
        if random.random() < pause_prob:
            pause_base += random.uniform(1, 3)

        await asyncio.sleep(max(0.8, pause_base))

    actual_dwell = int(time.time() - start)
    scroll_depth = min(1.0, max_scroll_y / 12000)

    return actual_dwell, scroll_count, scroll_depth
