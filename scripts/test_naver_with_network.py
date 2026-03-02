"""
네이버 검색 플로우 테스트 + 네트워크 요청 캡처

Chrome DevTools Protocol을 사용해서 네트워크 요청을 캡처합니다.
"""

import asyncio
import json
import sys
import os
import time
import websockets
from collections import defaultdict
from datetime import datetime

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.shared.device_tools import EnhancedAdbTools, AdbConfig


class NetworkCapture:
    """Chrome DevTools Protocol을 사용한 네트워크 캡처"""

    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.requests = []
        self.domain_stats = defaultdict(int)
        self.tracking_domains = [
            'tivan.naver.com', 'nlog.naver.com', 'lcs.naver.com',
            'siape.veta.naver.com', 'nam.veta.naver.com',
            'g.tivan.naver.com', 'ntm.pstatic.net'
        ]
        self.ws = None
        self.msg_id = 0

    async def connect(self):
        """WebSocket 연결"""
        self.ws = await websockets.connect(self.ws_url)
        # Network 도메인 활성화
        await self._send("Network.enable", {})
        print("Network capture enabled")

    async def _send(self, method: str, params: dict):
        """CDP 메서드 호출"""
        self.msg_id += 1
        msg = {"id": self.msg_id, "method": method, "params": params}
        await self.ws.send(json.dumps(msg))
        return self.msg_id

    async def capture_loop(self, duration_sec: int = 60):
        """네트워크 이벤트 캡처 루프"""
        end_time = time.time() + duration_sec

        while time.time() < end_time:
            try:
                msg = await asyncio.wait_for(self.ws.recv(), timeout=0.5)
                data = json.loads(msg)

                if data.get("method") == "Network.requestWillBeSent":
                    self._handle_request(data["params"])

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error: {e}")
                break

    def _handle_request(self, params: dict):
        """요청 처리"""
        request = params.get("request", {})
        url = request.get("url", "")

        # URL에서 도메인 추출
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc

        # 통계 업데이트
        self.domain_stats[domain] += 1

        # 추적 도메인 체크
        is_tracking = any(td in domain for td in self.tracking_domains)

        if is_tracking:
            self.requests.append({
                "timestamp": datetime.now().isoformat(),
                "domain": domain,
                "path": parsed.path,
                "url": url[:200],  # 길이 제한
                "method": request.get("method", "GET"),
            })
            print(f"  [TRACK] {domain}{parsed.path[:50]}")

    def get_summary(self) -> dict:
        """캡처 요약"""
        tracking_requests = [r for r in self.requests]
        return {
            "total_requests": sum(self.domain_stats.values()),
            "unique_domains": len(self.domain_stats),
            "tracking_requests": len(tracking_requests),
            "domain_stats": dict(self.domain_stats),
            "tracking_details": tracking_requests,
        }

    async def close(self):
        """연결 종료"""
        if self.ws:
            await self.ws.close()


async def run_test_with_network_capture(serial: str = "R3CW60BHSAT"):
    """네트워크 캡처와 함께 테스트 실행"""

    print("=" * 60)
    print("네이버 플로우 테스트 + 네트워크 캡처")
    print("=" * 60)

    # Chrome DevTools 연결 확인
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:9333/json") as response:
            tabs = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"ERROR: Chrome DevTools 연결 실패: {e}")
        print("  adb forward tcp:9333 localabstract:chrome_devtools_remote")
        return
    if not tabs:
        print("ERROR: Chrome 탭 없음")
        return

    # 첫 번째 탭의 WebSocket URL
    ws_url = tabs[0].get("webSocketDebuggerUrl")
    print(f"Chrome 탭: {tabs[0].get('title')}")
    print(f"WebSocket: {ws_url}")

    # 네트워크 캡처 시작
    capture = NetworkCapture(ws_url)
    await capture.connect()

    # EnhancedAdbTools 초기화
    config = AdbConfig(serial=serial, screen_width=1080, screen_height=2340)
    tools = EnhancedAdbTools(config)
    await tools.connect(serial)

    print("\n[테스트 시작] 네트워크 캡처 중...")
    print("-" * 60)

    # 캡처 태스크 시작
    capture_task = asyncio.create_task(capture.capture_loop(duration_sec=90))

    # 테스트 시나리오 실행
    await asyncio.sleep(1)

    # 1. 새로운 검색
    print("\n[1] 네이버 블로그 검색 (서울맛집)")
    await tools.open_url(
        "https://search.naver.com/search.naver?where=blog&query=서울맛집",
        package="com.android.chrome"
    )
    await asyncio.sleep(4)

    # 2. 스크롤 내리기
    print("\n[2] 스크롤 내리기 (3회)")
    for i in range(3):
        result = await tools.scroll_down(distance=600)
        print(f"  스크롤 {i+1}: {result.duration_ms}ms")
        await asyncio.sleep(2)

    # 3. 스크롤 올리기
    print("\n[3] 스크롤 올리기 (2회)")
    for i in range(2):
        result = await tools.scroll_up(distance=400)
        print(f"  스크롤업 {i+1}: {result.duration_ms}ms")
        await asyncio.sleep(1.5)

    # 4. 첫 번째 결과 클릭
    print("\n[4] 첫 번째 블로그 클릭")
    result = await tools.tap(540, 700)
    print(f"  탭: {result.message}")
    await asyncio.sleep(5)

    # 5. 블로그 콘텐츠 스크롤
    print("\n[5] 블로그 콘텐츠 읽기")
    for i in range(3):
        result = await tools.scroll_down(distance=500)
        print(f"  콘텐츠 스크롤 {i+1}: {result.duration_ms}ms")
        await asyncio.sleep(3)

    # 6. 뒤로가기
    print("\n[6] 뒤로가기")
    await tools.back()
    await asyncio.sleep(3)

    # 7. 두 번째 결과 클릭
    print("\n[7] 두 번째 블로그 클릭")
    result = await tools.tap(540, 1000)
    print(f"  탭: {result.message}")
    await asyncio.sleep(5)

    # 8. 콘텐츠 스크롤
    print("\n[8] 콘텐츠 읽기")
    for i in range(2):
        result = await tools.scroll_down(distance=400)
        await asyncio.sleep(2)

    print("\n[대기] 추가 네트워크 요청 캡처 중...")
    await asyncio.sleep(10)

    # 캡처 중지
    capture_task.cancel()
    try:
        await capture_task
    except asyncio.CancelledError:
        pass

    await capture.close()

    # 결과 출력
    print("\n" + "=" * 60)
    print("네트워크 캡처 결과")
    print("=" * 60)

    summary = capture.get_summary()
    print(f"\n총 요청 수: {summary['total_requests']}")
    print(f"고유 도메인: {summary['unique_domains']}")
    print(f"추적 요청 수: {summary['tracking_requests']}")

    print("\n[추적 도메인별 요청 수]")
    tracking_domains = {}
    for req in summary['tracking_details']:
        domain = req['domain']
        tracking_domains[domain] = tracking_domains.get(domain, 0) + 1

    for domain, count in sorted(tracking_domains.items(), key=lambda x: -x[1]):
        print(f"  {domain}: {count}회")

    print("\n[추적 요청 상세]")
    for req in summary['tracking_details'][:20]:
        print(f"  {req['domain']}{req['path'][:40]}")

    # 결과 저장
    output_path = "experiments/network_capture/capture_result.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {output_path}")

    return summary


async def main():
    try:
        await run_test_with_network_capture()
    except KeyboardInterrupt:
        print("\n중단됨")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
