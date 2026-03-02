"""
YAML 기반 캠페인 실행기
"""

import os
import yaml
import asyncio
import random
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, date

from supabase import create_client

from ..core import (
    ActionRegistry,
    PipelineEngine,
    PipelineConfig,
    ContextManager,
)
from ..actions import (
    PersonaSelectorAction,
    AndroidIdSetterAction,
    CookieCleanerAction,
    IpRotatorAction,
    CdpNavigatorAction,
    DwellSimulatorAction,
    SupabaseLoggerAction,
)

from src.shared.persona_manager.device_identity import DeviceIdentityManager
from src.shared.device_tools.adb_enhanced import EnhancedAdbTools, AdbConfig
from src.shared.naver_chrome_use.cdp_client import CdpClient


logger = logging.getLogger("campaign_runner")


class CampaignRunner:
    """YAML 기반 캠페인 실행기"""

    def __init__(self, campaign_file: str):
        self.campaign_file = campaign_file
        self.campaign_config = self._load_campaign_config()
        self.registry = ActionRegistry()
        self.pipeline_engine = PipelineEngine(self.registry)
        self.context_manager = ContextManager()

        # 액션 등록
        self._register_actions()
        # 파이프라인 등록
        self._register_pipelines()

        # 컴포넌트
        self.supabase_client = None
        self.identity_manager = None
        self.adb_tools = None
        self.cdp_client = None

    def _load_campaign_config(self) -> Dict[str, Any]:
        """YAML 캠페인 설정 로드"""
        with open(self.campaign_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _register_actions(self):
        """액션 등록"""
        action_configs = self.campaign_config.get("action_configs", {})

        self.registry.register_action(
            "persona_selector",
            PersonaSelectorAction,
            action_configs.get("persona_selector")
        )
        self.registry.register_action(
            "android_id_setter",
            AndroidIdSetterAction,
            action_configs.get("android_id_setter")
        )
        self.registry.register_action(
            "cookie_cleaner",
            CookieCleanerAction,
            action_configs.get("cookie_cleaner")
        )
        self.registry.register_action(
            "ip_rotator",
            IpRotatorAction,
            action_configs.get("ip_rotator")
        )
        self.registry.register_action(
            "cdp_navigator",
            CdpNavigatorAction,
            action_configs.get("cdp_navigator")
        )
        self.registry.register_action(
            "dwell_simulator",
            DwellSimulatorAction,
            action_configs.get("dwell_simulator")
        )
        self.registry.register_action(
            "supabase_logger",
            SupabaseLoggerAction
        )

    def _register_pipelines(self):
        """YAML에서 파이프라인 등록"""
        if "pipelines" in self.campaign_config:
            for pipeline_def in self.campaign_config["pipelines"]:
                config = PipelineConfig(
                    name=pipeline_def.get("name", "unnamed"),
                    actions=pipeline_def.get("actions", []),
                    parallel=pipeline_def.get("parallel", False),
                    max_retries=pipeline_def.get("max_retries", 1),
                    break_on_failure=pipeline_def.get("break_on_failure", False)
                )
                self.pipeline_engine.register_pipeline(config.name, config)

    def _initialize_components(self):
        """컴포넌트 초기화"""
        cfg = self.campaign_config["config"]

        # Supabase
        supabase_url = os.getenv("SUPABASE_URL", cfg.get("supabase_url"))
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("PERSONA_SUPABASE_SERVICE_KEY")
        if not supabase_key:
            # CLAUDE.md에 문서화된 서비스 키 사용
            supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBrZWhjZmJqb3RjdHZuZW9yZG9iIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzE5MjY4MSwiZXhwIjoyMDY4NzY4NjgxfQ.fn1IxRxjJZ6gihy_SCvyQrT6Vx3xb1yMaVzztOsLeyk"

        self.supabase_client = create_client(supabase_url, supabase_key)

        # DeviceIdentityManager
        self.identity_manager = DeviceIdentityManager(cfg["device_serial"])

        # EnhancedAdbTools
        self.adb_tools = EnhancedAdbTools(AdbConfig(
            serial=cfg["device_serial"],
            action_interval_min_ms=50,
            action_interval_max_ms=150,
        ))

        # CdpClient
        self.cdp_client = CdpClient(
            device_serial=cfg["device_serial"],
            cdp_port=cfg.get("cdp_port", 9333)
        )

    async def run_single_visit(
        self,
        visit_num: int,
        total_visits: int,
        keyword: str,
        used_persona_ids: set
    ) -> bool:
        """단일 방문 실행"""
        cfg = self.campaign_config["config"]

        # 타겟 URL: target_urls 리스트가 있으면 랜덤 선택
        target_urls = cfg.get("target_urls")
        if target_urls:
            target_url = random.choice(target_urls)
        else:
            target_url = cfg["base_url"]

        # 리퍼러: fixed 모드면 고정값 사용 (Instagram 등 SNS 유입)
        if cfg.get("referrer_mode") == "fixed":
            referrer = cfg["referrer_fixed"]
        else:
            referrer = cfg["referrer_base"] + keyword.replace(" ", "+")

        # 컨텍스트 생성
        context = {
            # 기본 정보
            "campaign_id": f"boost_{datetime.now().strftime('%Y%m%d')}",
            "device_serial": cfg["device_serial"],
            "visit_num": visit_num,
            "total_visits": total_visits,

            # 타겟
            "target_url": target_url,
            "keyword": keyword,
            "referrer": referrer,

            # 컴포넌트
            "supabase_client": self.supabase_client,
            "identity_manager": self.identity_manager,
            "adb_tools": self.adb_tools,
            "cdp_client": self.cdp_client,

            # 상태
            "used_persona_ids": used_persona_ids,

            # 캠페인 설정 (액션에서 참조 — Instagram UA/sec-fetch 등)
            "campaign_config": cfg,
        }

        try:
            # 파이프라인 순차 실행
            for pipeline_def in self.campaign_config["pipelines"]:
                pipeline_name = pipeline_def["name"]

                logger.info(f"[{visit_num}/{total_visits}] 파이프라인: {pipeline_name}")

                context = await self.pipeline_engine.execute_pipeline(
                    pipeline_name=pipeline_name,
                    initial_context=context,
                    progress_callback=self._on_progress
                )

                # 파이프라인 결과 확인
                results = context.get("pipeline_results", {})
                failed_actions = [
                    name for name, result in results.items()
                    if not result.success
                ]

                if failed_actions and pipeline_def.get("break_on_failure", False):
                    logger.error(f"파이프라인 실패: {pipeline_name}, 실패 액션: {failed_actions}")
                    return False

            logger.info(f"[{visit_num}/{total_visits}] 방문 완료")
            return True

        except Exception as e:
            logger.error(f"[{visit_num}/{total_visits}] 오류: {e}", exc_info=True)
            return False

    def _on_progress(self, action_name: str, result: Any):
        """진행 상황 콜백"""
        status = "✓" if result.success else "✗"
        logger.info(f"  {status} {action_name} ({result.execution_time:.2f}s)")
        if not result.success and result.error_message:
            logger.warning(f"    {result.error_message}")

    async def run_campaign(
        self,
        target: int,
        now_mode: bool = False
    ) -> Dict[str, Any]:
        """
        캠페인 실행

        now_mode=True:  짧은 간격으로 즉시 실행
        now_mode=False: 시간대별 가중치 적용 분산 실행
        """
        mode_label = "즉시" if now_mode else "분산"
        logger.info(f"=== {self.campaign_config['name']} ({mode_label}) ===")
        logger.info(f"목표: {target}회")

        # 컴포넌트 초기화
        self._initialize_components()

        # ADB 연결
        if not await self.adb_tools.connect(self.campaign_config["config"]["device_serial"]):
            logger.error("ADB 연결 실패")
            return {"success": False, "error": "ADB 연결 실패"}

        # 루트 확인
        await self.identity_manager.ensure_root()

        success_count = 0
        fail_streak = 0
        used_persona_ids = set()

        cfg = self.campaign_config["config"]
        keywords = cfg["keywords"]

        for i in range(1, target + 1):
            keyword = random.choice(keywords)
            logger.info(f"--- [{i}/{target}] \"{keyword}\" ---")

            ok = await self.run_single_visit(
                visit_num=i,
                total_visits=target,
                keyword=keyword,
                used_persona_ids=used_persona_ids
            )

            if ok:
                success_count += 1
                fail_streak = 0
            else:
                fail_streak += 1
                if fail_streak >= 3:
                    logger.warning("연속 3회 실패 - 60s 대기 후 CDP 재연결")
                    await asyncio.sleep(60)
                    self.cdp_client._connected = False
                    await self.cdp_client.connect()
                    fail_streak = 0

            # 다음 방문 대기
            if i < target:
                if now_mode:
                    gap = random.randint(cfg["min_visit_gap"], cfg["max_visit_gap"])
                else:
                    gap = self._calc_spread_gap(target, remaining=target - i)

                gap_int = int(gap)
                logger.info(f"[{i}] 쿨다운 {gap_int}s ({gap_int/60:.1f}분)")
                await asyncio.sleep(gap)

        await self.cdp_client.disconnect()
        logger.info(f"=== 캠페인 완료: {success_count}/{target} 성공 ===")

        return {
            "success": True,
            "total": target,
            "success_count": success_count,
            "fail_count": target - success_count
        }

    def _calc_spread_gap(self, target: int, remaining: int) -> float:
        """분산 모드 간격 계산 (시간대별 가중치 적용)"""
        cfg = self.campaign_config["config"]
        weights = self.campaign_config.get("hourly_weights", {})

        now = datetime.now()
        end = now.replace(hour=cfg["spread_end_hour"], minute=0, second=0, microsecond=0)
        available_sec = max(0, (end - now).total_seconds())

        if available_sec < 300 or remaining <= 0:
            return random.randint(cfg["min_visit_gap"], cfg["max_visit_gap"])

        base_gap = available_sec / remaining

        # 시간대 가중치 적용
        hour = now.hour
        weight = weights.get(hour, 1.0)
        adjusted_gap = base_gap / weight

        # ±40% 랜덤 변동
        gap = adjusted_gap * random.uniform(0.6, 1.4)

        return max(cfg["spread_min_gap"], min(gap, cfg["spread_max_gap"]))
