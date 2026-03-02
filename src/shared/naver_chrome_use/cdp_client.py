"""
CdpClient - Chrome DevTools Protocol 클라이언트

ADB를 통해 Android Chrome에 CDP WebSocket으로 연결하여
Page.navigate(url, referrer) 등의 명령을 실행합니다.

실험 결과 (experiments/referrer_test):
- about:blank에서 Page.navigate(url, referrer) 한 번이면
  document.referrer가 설정됨 (검색 페이지 로딩 불필요)
- Referrer-Policy: strict-origin-when-cross-origin 적용 →
  오리진만 전달 (https://m.search.naver.com/)

사용법:
    cdp = CdpClient(device_serial="R3CW60BHSAT")
    await cdp.connect()
    await cdp.navigate_with_referrer(
        url="https://m.blog.naver.com/blogId/postId",
        referrer="https://m.search.naver.com/search.naver?where=blog&query=cctv"
    )
    ref = await cdp.get_document_referrer()
    await cdp.disconnect()
"""

import asyncio
import json
import logging
import subprocess
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger("cdp_client")

# CDP 포트 포워딩 기본값
DEFAULT_CDP_PORT = 9222
# Page.navigate 후 로드 대기 (초)
DEFAULT_PAGE_LOAD_WAIT = 5.0
# WebSocket 메시지 수신 타임아웃 (초)
WS_RECV_TIMEOUT = 10.0


class CdpClient:
    """
    Chrome DevTools Protocol 클라이언트

    ADB 포트 포워딩을 통해 Android Chrome의 CDP WebSocket에 연결하고,
    Page.navigate, Runtime.evaluate 등의 명령을 실행합니다.
    """

    def __init__(
        self,
        device_serial: str = None,
        cdp_port: int = DEFAULT_CDP_PORT,
    ):
        self.device_serial = device_serial
        self.cdp_port = cdp_port
        self._connected = False
        self._ws = None
        self._ws_url: Optional[str] = None
        self._msg_id = 0

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """
        CDP 연결 설정

        1. ADB 포트 포워딩 설정
        2. CDP 타겟(탭) 조회
        3. 첫 번째 page 타겟의 WebSocket URL 확보

        Returns:
            연결 성공 여부
        """
        try:
            self._setup_port_forward()
            await asyncio.sleep(0.5)

            targets = self._get_targets()
            if not targets:
                logger.error("No CDP targets found")
                return False

            target = self._find_page_target(targets)
            if not target:
                logger.error("No page target found")
                return False

            ws_url = target.get("webSocketDebuggerUrl", "")
            if not ws_url:
                logger.error("No webSocketDebuggerUrl in target")
                return False

            # localhost로 통일
            self._ws_url = ws_url.replace("127.0.0.1", "localhost")
            self._connected = True
            logger.info(f"CDP ready: {self._ws_url[:60]}...")
            return True

        except Exception as e:
            logger.error(f"CDP connect failed: {e}")
            return False

    def _setup_port_forward(self) -> None:
        """ADB 포트 포워딩 설정 (이미 열려있으면 skip)"""
        # 이미 포트가 열려있는지 확인 (socat 등으로 미리 설정된 경우)
        try:
            req = urllib.request.Request(f"http://localhost:{self.cdp_port}/json/version")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    logger.debug(f"Port {self.cdp_port} already forwarded, skip adb forward")
                    return
        except Exception:
            pass

        cmd = ["adb"]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend([
            "forward",
            f"tcp:{self.cdp_port}",
            "localabstract:chrome_devtools_remote",
        ])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            raise RuntimeError(f"ADB forward failed: {result.stderr}")

        logger.debug(f"Port forwarding: tcp:{self.cdp_port} → chrome_devtools_remote")

    def _get_targets(self) -> List[Dict]:
        """CDP 타겟(탭) 목록 조회"""
        url = f"http://localhost:{self.cdp_port}/json"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            logger.error(f"Failed to get CDP targets: {e}")
            return []

    def _find_page_target(
        self, targets: List[Dict], url_contains: str = ""
    ) -> Optional[Dict]:
        """page 타입 타겟 찾기"""
        for t in targets:
            if t.get("type") == "page":
                if not url_contains or url_contains in t.get("url", ""):
                    return t
        # url_contains 매칭 실패 시 첫 번째 page 반환
        for t in targets:
            if t.get("type") == "page":
                return t
        return None

    async def _send_cdp_command(
        self,
        method: str,
        params: Dict = None,
        timeout: float = WS_RECV_TIMEOUT,
    ) -> Dict:
        """
        CDP 명령 전송 및 응답 수신

        매번 새 WebSocket 연결을 열고 닫는다.
        (Chrome은 한 탭에 하나의 WebSocket만 허용)
        """
        import websockets

        self._msg_id += 1
        msg_id = self._msg_id

        msg = {"id": msg_id, "method": method}
        if params:
            msg["params"] = params

        async with websockets.connect(
            self._ws_url,
            max_size=10 * 1024 * 1024,
        ) as ws:
            await ws.send(json.dumps(msg))

            start = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start < timeout:
                try:
                    resp = await asyncio.wait_for(ws.recv(), timeout=5)
                    data = json.loads(resp)
                    if data.get("id") == msg_id:
                        return data
                except asyncio.TimeoutError:
                    break

        return {}

    async def navigate_with_referrer(
        self,
        url: str,
        referrer: str,
        wait_load: float = DEFAULT_PAGE_LOAD_WAIT,
    ) -> bool:
        """
        CDP Page.navigate로 URL 이동 + referrer 설정

        실험 결과: about:blank에서 바로 호출해도
        document.referrer가 정상 설정됨 (Experiment E).

        Args:
            url: 이동할 URL
            referrer: 설정할 referrer URL
            wait_load: 페이지 로드 대기 시간 (초)

        Returns:
            성공 여부
        """
        if not self._connected:
            logger.error("CDP not connected")
            return False

        try:
            result = await self._send_cdp_command(
                "Page.navigate",
                {"url": url, "referrer": referrer},
            )

            if "error" in result:
                logger.error(f"Page.navigate error: {result['error']}")
                return False

            # 페이지 로드 대기
            await asyncio.sleep(wait_load)

            # 타겟 갱신 (페이지 변경 후 WebSocket URL이 바뀔 수 있음)
            targets = self._get_targets()
            target = self._find_page_target(targets)
            if target and "webSocketDebuggerUrl" in target:
                self._ws_url = target["webSocketDebuggerUrl"].replace(
                    "127.0.0.1", "localhost"
                )

            logger.info(f"Navigated to {url[:60]}... with referrer")
            return True

        except Exception as e:
            logger.error(f"navigate_with_referrer failed: {e}")
            return False

    async def evaluate(self, expression: str) -> Any:
        """
        CDP Runtime.evaluate로 JavaScript 실행

        Args:
            expression: 실행할 JS 표현식

        Returns:
            실행 결과 값
        """
        if not self._connected:
            return None

        try:
            result = await self._send_cdp_command(
                "Runtime.evaluate",
                {"expression": expression, "returnByValue": True},
            )
            return result.get("result", {}).get("result", {}).get("value")
        except Exception as e:
            logger.error(f"evaluate failed: {e}")
            return None

    async def get_document_referrer(self) -> str:
        """현재 페이지의 document.referrer 값 반환"""
        result = await self.evaluate("document.referrer")
        return result if isinstance(result, str) else ""

    async def get_current_url(self) -> str:
        """현재 페이지 URL 반환"""
        result = await self.evaluate("window.location.href")
        return result if isinstance(result, str) else ""

    async def disconnect(self) -> None:
        """CDP 연결 해제 및 포트 포워딩 제거"""
        self._connected = False
        self._ws_url = None

        try:
            cmd = ["adb"]
            if self.device_serial:
                cmd.extend(["-s", self.device_serial])
            cmd.extend(["forward", "--remove", f"tcp:{self.cdp_port}"])
            subprocess.run(cmd, capture_output=True, timeout=5)
            logger.debug("Port forwarding removed")
        except Exception:
            pass
