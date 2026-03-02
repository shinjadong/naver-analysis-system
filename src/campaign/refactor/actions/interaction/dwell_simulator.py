"""
휴먼라이크 체류 시뮬레이션 액션
"""

import logging
import random
import time
import asyncio
from typing import Dict, Any

from ...core.action_base import CampaignAction, ActionResult


logger = logging.getLogger("dwell_simulator")


class DwellSimulatorAction(CampaignAction):
    """휴먼라이크 체류 시뮬레이션"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.min_dwell = self.config.get("min_dwell", 60)
        self.max_dwell = self.config.get("max_dwell", 180)

    async def execute(self, context: Dict[str, Any]) -> ActionResult:
        """체류 시뮬레이션 실행"""
        adb_tools = self.get_context_value("adb_tools")
        behavior = self.get_context_value("behavior_profile", {})

        if not adb_tools:
            return ActionResult(
                success=False,
                error_message="adb_tools 없음"
            )

        try:
            dwell_sec, scroll_count, scroll_depth = await self._simulate_dwell(
                adb_tools, behavior
            )

            logger.info(f"체류 시뮬레이션 완료: {dwell_sec}s ({scroll_count}회 스크롤)")

            return ActionResult(
                success=True,
                data={
                    "dwell_sec": dwell_sec,
                    "scroll_count": scroll_count,
                    "scroll_depth": scroll_depth
                }
            )

        except Exception as e:
            return ActionResult(
                success=False,
                error_message=f"체류 시뮬레이션 실패: {str(e)}"
            )

    async def _simulate_dwell(
        self,
        adb_tools,
        behavior: Dict[str, Any]
    ) -> tuple[int, int, float]:
        """
        Supabase behavior_profile 기반 휴먼라이크 체류

        behavior 구조:
            scroll_speed: float (0.5~2.0)
            avg_dwell_time: int (초)
            pause_probability: float (0~0.5)
        """
        scroll_speed = behavior.get("scroll_speed", 1.0)
        avg_dwell = behavior.get("avg_dwell_time", 120)
        pause_prob = behavior.get("pause_probability", 0.2)

        # 체류 시간 결정
        dwell_sec = random.randint(
            max(self.min_dwell, int(avg_dwell * 0.6)),
            min(self.max_dwell, int(avg_dwell * 1.4)),
        )

        # 스크롤 간격 및 횟수 계산
        scroll_interval = max(2, int(4 / scroll_speed))
        num_scrolls = max(4, dwell_sec // scroll_interval)

        start = time.time()
        scroll_count = 0
        max_scroll_y = 0

        # 화면 크기
        sw = adb_tools.config.screen_width or 1080
        sh = adb_tools.config.screen_height or 2400
        center_x = sw // 2

        # 초기 대기 (페이지 로딩 시간)
        await asyncio.sleep(random.uniform(1, 2.5))

        # 스크롤 시뮬레이션
        for i in range(num_scrolls):
            elapsed = time.time() - start
            if elapsed >= dwell_sec:
                break

            roll = random.random()

            if roll < 0.15 and scroll_count > 2:
                # 위로 스크롤 (되돌아 읽기)
                dist = random.randint(200, 400)
                start_y = int(sh * 0.3)
                dur = random.randint(300, 600)
                await adb_tools.swipe(
                    center_x, start_y, center_x, start_y + dist,
                    duration_ms=dur, use_curved_path=False
                )
            elif roll < 0.25 and scroll_count > 0:
                # 읽기 멈춤
                await asyncio.sleep(random.uniform(1.5, 4))
            else:
                # 아래로 스크롤
                dist = random.randint(300, 700)
                start_y = int(sh * 0.7)
                dur = random.randint(300, 600)
                await adb_tools.swipe(
                    center_x, start_y, center_x, start_y - dist,
                    duration_ms=dur, use_curved_path=False
                )
                scroll_count += 1
                max_scroll_y += dist

            # 스크롤 후 멈춤
            pause_base = scroll_interval + random.uniform(-1, 1)
            if random.random() < pause_prob:
                pause_base += random.uniform(1, 3)

            await asyncio.sleep(max(0.8, pause_base))

        actual_dwell = int(time.time() - start)
        scroll_depth = min(1.0, max_scroll_y / 12000)

        return actual_dwell, scroll_count, scroll_depth
