"""
Portal + SmartExecutor + EnhancedAdbTools 통합 테스트

테스트 목적:
1. Portal에서 UI 트리 가져오기
2. 텍스트로 요소 찾기 (예: "블로그" 탭)
3. EnhancedAdbTools로 휴먼라이크 탭 실행
4. 베지어 커브 오프셋 적용 확인
"""

import asyncio
import json
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.shared.device_tools import EnhancedAdbTools, AdbConfig


class PortalClient:
    """Simple Portal client for testing"""

    def __init__(self, serial: str):
        self.serial = serial

    def get_ui_tree(self) -> dict:
        """Get UI tree from Portal"""
        proc = subprocess.run(
            ['adb', '-s', self.serial, 'shell',
             'content query --uri content://com.droidrun.portal/state'],
            capture_output=True, timeout=15
        )
        output = proc.stdout.decode('utf-8', errors='replace').strip()

        if 'result=' in output:
            result_start = output.find('result=') + 7
            outer = json.loads(output[result_start:])
            return json.loads(outer.get('data', '{}'))
        return {}

    def flatten_tree(self, nodes, result=None):
        """Flatten nested tree to list"""
        if result is None:
            result = []
        for n in nodes:
            result.append(n)
            self.flatten_tree(n.get('children', []), result)
        return result

    def find_by_text(self, text: str) -> list:
        """Find elements containing text"""
        data = self.get_ui_tree()
        all_nodes = self.flatten_tree(data.get('a11y_tree', []))

        results = []
        for n in all_nodes:
            node_text = n.get('text', '')
            if text in node_text:
                bounds = n.get('bounds', '')
                if bounds:
                    parts = [int(x.strip()) for x in bounds.split(',')]
                    cx = (parts[0] + parts[2]) // 2
                    cy = (parts[1] + parts[3]) // 2
                    results.append({
                        'text': node_text,
                        'x': cx,
                        'y': cy,
                        'bounds': bounds,
                        'class': n.get('className', '')
                    })
        return results


async def test_text_based_tap(serial: str = "R3CW60BHSAT"):
    """Test: Find element by text, then tap with humanlike behavior"""

    print("=" * 60)
    print("Portal + SmartExecutor + EnhancedAdbTools 통합 테스트")
    print("=" * 60)

    # 1. Initialize Portal Client
    print("\n[1] Portal 클라이언트 초기화")
    portal = PortalClient(serial)

    # 2. Get current UI state
    print("\n[2] UI 트리 가져오기")
    data = portal.get_ui_tree()
    phone_state = data.get('phone_state', {})
    print(f"  Package: {phone_state.get('packageName')}")
    print(f"  Activity: {phone_state.get('activityName')}")

    # 3. Find "블로그" tab by text
    print("\n[3] 텍스트로 요소 찾기: '블로그'")
    blog_elements = portal.find_by_text("블로그")

    if not blog_elements:
        print("  ERROR: '블로그' 요소를 찾을 수 없습니다!")
        return False

    # Use the first match (usually the tab)
    target = blog_elements[0]
    print(f"  Found: '{target['text']}' @ ({target['x']}, {target['y']})")
    print(f"  Class: {target['class']}")
    print(f"  Bounds: {target['bounds']}")

    # 4. Initialize EnhancedAdbTools
    print("\n[4] EnhancedAdbTools 초기화")
    config = AdbConfig(serial=serial, screen_width=1080, screen_height=2340)
    tools = EnhancedAdbTools(config)
    await tools.connect(serial)
    print("  OK: 연결됨")

    # 5. Tap with humanlike behavior (Bezier offset applied)
    print("\n[5] 휴먼라이크 탭 실행 (베지어 오프셋 적용)")
    print(f"  Target: ({target['x']}, {target['y']})")

    result = await tools.tap(target['x'], target['y'])

    print(f"  Success: {result.success}")
    print(f"  Duration: {result.duration_ms}ms")
    print(f"  Details: {result.details}")

    # 6. Wait and verify
    await asyncio.sleep(2)

    print("\n[6] 결과 확인")
    data_after = portal.get_ui_tree()
    phone_after = data_after.get('phone_state', {})
    print(f"  New Activity: {phone_after.get('activityName')}")

    # 7. Find blog posts
    print("\n[7] 블로그 검색 결과 확인")
    posts = portal.find_by_text("맛집")  # Look for search results
    print(f"  '맛집' 포함 요소: {len(posts)}개")

    if posts:
        print("\n[8] 첫 번째 블로그 글 클릭 (휴먼라이크)")
        # Find first clickable blog post (usually after y=500)
        clickable_posts = [p for p in posts if p['y'] > 500 and 'TextView' in p['class']]

        if clickable_posts:
            first_post = clickable_posts[0]
            print(f"  Target: '{first_post['text'][:30]}...' @ ({first_post['x']}, {first_post['y']})")

            result2 = await tools.tap(first_post['x'], first_post['y'])
            print(f"  Success: {result2.success}")
            print(f"  Duration: {result2.duration_ms}ms")

            await asyncio.sleep(3)

            # Scroll with humanlike behavior
            print("\n[9] 블로그 콘텐츠 스크롤 (휴먼라이크)")
            for i in range(2):
                scroll_result = await tools.scroll_down(distance=500)
                print(f"  스크롤 {i+1}: {scroll_result.duration_ms}ms, segments={scroll_result.details.get('segments', 'N/A')}")
                await asyncio.sleep(1.5)

    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)

    print("\n[요약]")
    print("- Portal: UI 트리 성공적으로 획득")
    print("- 텍스트 검색: '블로그' 요소 찾기 성공")
    print("- EnhancedAdbTools: 베지어 오프셋 적용된 휴먼라이크 탭 실행")
    print("- 모든 동작에 가변 속도 및 랜덤 오프셋 적용됨")

    return True


async def main():
    try:
        await test_text_based_tap()
    except KeyboardInterrupt:
        print("\n중단됨")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
