"""
CDP 네비게이션 액션
"""

import random
import logging
import asyncio
import subprocess
from typing import Dict, Any, Optional

from ...core.action_base import CampaignAction, ActionResult


logger = logging.getLogger("cdp_navigator")


class CdpNavigatorAction(CampaignAction):
    """CDP referrer 네비게이션 액션"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.chrome_package = self.config.get("chrome_package", "com.android.chrome")
        self.wait_load = self.config.get("wait_load", 5)
        self.set_geolocation = self.config.get("set_geolocation", True)
        self.set_sec_fetch = self.config.get("set_sec_fetch_headers", False)
        self.set_instagram_ua = self.config.get("set_instagram_ua", False)

    async def execute(self, context: Dict[str, Any]) -> ActionResult:
        """CDP 네비게이션 실행"""
        cdp_client = self.get_context_value("cdp_client")
        target_url = self.get_context_value("target_url")
        referrer = self.get_context_value("referrer")
        device_serial = self.get_context_value("device_serial")
        location = self.get_context_value("location")
        device_config = self.get_context_value("device_config", {})
        campaign_config = self.get_context_value("campaign_config", {})

        if not cdp_client or not target_url:
            return ActionResult(
                success=False,
                error_message="cdp_client 또는 target_url 없음"
            )

        try:
            # Chrome 재시작 (about:blank)
            self._start_chrome(device_serial)
            await asyncio.sleep(3)

            # CDP 재연결 (Chrome 재시작 후 WebSocket URL 변경)
            cdp_client._connected = False
            ok = await cdp_client.connect()
            if not ok:
                return ActionResult(
                    success=False,
                    error_message="CDP 연결 실패"
                )

            # Instagram UA 오버라이드 (페르소나 디바이스 정보 기반)
            if self.set_instagram_ua and device_config:
                await self._set_instagram_ua(cdp_client, device_config, campaign_config)

            # sec-fetch 헤더 설정 (Instagram cross-site 패턴)
            if self.set_sec_fetch:
                sec_headers = campaign_config.get("sec_fetch_headers", {})
                if sec_headers:
                    await self._set_extra_headers(cdp_client, sec_headers)

            # 위치 오버라이드 (페르소나 지역 반영)
            if self.set_geolocation and location:
                await self._set_geolocation(cdp_client, location)

            # CDP referrer 네비게이션
            ok = await cdp_client.navigate_with_referrer(
                url=target_url,
                referrer=referrer,
                wait_load=self.wait_load
            )

            if not ok:
                return ActionResult(
                    success=False,
                    error_message="CDP navigate 실패"
                )

            # 리퍼러 확인
            doc_ref = await cdp_client.get_document_referrer()
            logger.info(f'CDP 네비게이션 완료: referrer="{doc_ref}"')

            return ActionResult(
                success=True,
                data={
                    "document_referrer": doc_ref,
                    "target_url": target_url
                }
            )

        except Exception as e:
            return ActionResult(
                success=False,
                error_message=f"CDP 네비게이션 실패: {str(e)}"
            )

    def _start_chrome(self, device_serial: str):
        """Chrome 재시작 (about:blank)"""
        try:
            subprocess.run(
                [
                    "adb", "-s", device_serial, "shell", "am", "start",
                    "-a", "android.intent.action.VIEW",
                    "-d", "about:blank",
                    self.chrome_package
                ],
                capture_output=True,
                timeout=10
            )
        except Exception as e:
            logger.warning(f"Chrome 재시작 실패: {e}")

    async def _set_instagram_ua(
        self,
        cdp_client,
        device_config: Dict[str, Any],
        campaign_config: Dict[str, Any],
    ):
        """Instagram 인앱 브라우저 UA로 오버라이드"""
        try:
            insta_versions = campaign_config.get("insta_versions", ["375.0.0.38.112"])
            insta_ver = random.choice(insta_versions)

            # 페르소나의 디바이스 정보 활용
            os_ver = device_config.get("os_version", "14")
            model = device_config.get("model", "SM-S926N")
            build_id = device_config.get("build_id", "UP1A.231005.007")
            chrome_ver = device_config.get("chrome_version", "131.0.6778.135")
            manufacturer = device_config.get("manufacturer", "samsung")
            codename = device_config.get("codename", model.lower())
            dpi = device_config.get("dpi", "480")
            width = device_config.get("screen_width", "1080")
            height = device_config.get("screen_height", "2340")
            api_level = device_config.get("api_level", "34")

            ua = (
                f"Mozilla/5.0 (Linux; Android {os_ver}; {model} Build/{build_id}; wv) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
                f"Chrome/{chrome_ver} Mobile Safari/537.36 "
                f"Instagram {insta_ver} Android ({os_ver}/{api_level}; "
                f"{dpi}dpi; {width}x{height}; {manufacturer}; {model}; "
                f"{codename}; arm64-v8a; ko_KR; 000000000)"
            )

            await cdp_client._send_cdp_command("Emulation.setUserAgentOverride", {
                "userAgent": ua,
            })
            logger.info(f"Instagram UA 설정: ...Instagram {insta_ver}...")

        except Exception as e:
            logger.warning(f"Instagram UA 설정 실패 (무시): {e}")

    async def _set_extra_headers(
        self,
        cdp_client,
        headers: Dict[str, str],
    ):
        """CDP Network.setExtraHTTPHeaders로 추가 헤더 설정"""
        try:
            await cdp_client._send_cdp_command("Network.enable", {})
            await cdp_client._send_cdp_command("Network.setExtraHTTPHeaders", {
                "headers": headers,
            })
            logger.info(f"sec-fetch 헤더 설정: {list(headers.keys())}")
        except Exception as e:
            logger.warning(f"sec-fetch 헤더 설정 실패 (무시): {e}")

    async def _set_geolocation(
        self,
        cdp_client,
        location: Dict[str, Any]
    ):
        """CDP Emulation.setGeolocationOverride로 브라우저 위치 설정"""
        lat = location.get("latitude")
        lng = location.get("longitude")
        acc = location.get("accuracy", 10)

        if lat is None or lng is None:
            return

        try:
            await cdp_client._send_cdp_command("Emulation.setGeolocationOverride", {
                "latitude": float(lat),
                "longitude": float(lng),
                "accuracy": float(acc),
            })
            logger.info(f"위치 설정: {lat:.4f}, {lng:.4f}")
        except Exception as e:
            logger.debug(f"위치 설정 실패 (무시): {e}")
