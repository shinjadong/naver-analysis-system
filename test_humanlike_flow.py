"""
Humanlike Action Full Flow Test

Test all basic actions via EnhancedAdbTools:
1. Tap (with bezier offset)
2. Scroll (variable speed)
3. Portal integration
4. URL open
"""

import asyncio
import sys
import os

# Add project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.shared.device_tools import EnhancedAdbTools, AdbConfig, create_tools


async def test_device_connection():
    """1. Device connection test"""
    print("\n" + "="*50)
    print("1. Device Connection Test")
    print("="*50)

    tools = create_tools(serial="R3CW60BHSAT")
    connected = await tools.connect()

    if connected:
        print(f"[OK] Device connected: {tools._serial}")
        return tools
    else:
        print("[FAIL] Device connection failed")
        return None


async def test_humanlike_tap(tools: EnhancedAdbTools):
    """2. Humanlike tap test"""
    print("\n" + "="*50)
    print("2. Humanlike Tap Test")
    print("="*50)

    # Tap center of screen
    x, y = 540, 1200
    print(f"Original coords: ({x}, {y})")

    result = await tools.tap(x, y)

    if result.success:
        actual_x = result.details.get("actual_x", x)
        actual_y = result.details.get("actual_y", y)
        offset_x = result.details.get("offset_x", 0)
        offset_y = result.details.get("offset_y", 0)
        print(f"[OK] Tap success")
        print(f"  Actual coords: ({actual_x}, {actual_y})")
        print(f"  Offset: ({offset_x}, {offset_y})")
        return True
    else:
        print(f"[FAIL] Tap failed: {result.message}")
        return False


async def test_humanlike_scroll(tools: EnhancedAdbTools):
    """3. Humanlike scroll test"""
    print("\n" + "="*50)
    print("3. Humanlike Scroll Test")
    print("="*50)

    # Scroll down
    print("Scrolling down...")
    result = await tools.scroll_down(distance=600)

    if result.success:
        segments = result.details.get("segments", 0)
        print(f"[OK] Scroll down success")
        print(f"  Segments: {segments}")
        print(f"  Duration: {result.duration_ms}ms")
    else:
        print(f"[FAIL] Scroll failed: {result.message}")
        return False

    await asyncio.sleep(1)

    # Scroll up
    print("Scrolling up...")
    result = await tools.scroll_up(distance=400)

    if result.success:
        print(f"[OK] Scroll up success")
        return True
    else:
        print(f"[FAIL] Scroll up failed: {result.message}")
        return False


async def test_open_url(tools: EnhancedAdbTools):
    """4. URL open test"""
    print("\n" + "="*50)
    print("4. URL Open Test")
    print("="*50)

    url = "https://m.naver.com"
    print(f"Opening URL: {url}")

    result = await tools.open_url(url, package="com.android.chrome")

    if result.success:
        print(f"[OK] URL opened successfully")
        return True
    else:
        print(f"[FAIL] URL open failed: {result.message}")
        return False


async def test_portal_connection():
    """5. Portal connection test"""
    print("\n" + "="*50)
    print("5. Portal Connection Test")
    print("="*50)

    try:
        from src.shared.portal_client import PortalClient, PortalConfig

        config = PortalConfig(device_serial="R3CW60BHSAT")
        portal = PortalClient(config)

        # ping test
        status = await portal.ping()

        if status:
            print("[OK] Portal connected")

            # Get UI tree
            tree = await portal.get_ui_tree()
            if tree:
                print(f"  Total elements: {len(tree.all_elements)}")
                print(f"  Clickable: {len(tree.clickable_elements)}")
            return True
        else:
            print("[FAIL] Portal connection failed (check if app is running)")
            return False

    except Exception as e:
        print(f"[FAIL] Portal test error: {e}")
        return False


async def test_back_key(tools: EnhancedAdbTools):
    """6. Back key test"""
    print("\n" + "="*50)
    print("6. Back Key Test")
    print("="*50)

    result = await tools.back()

    if result.success:
        print("[OK] Back key success")
        return True
    else:
        print(f"[FAIL] Back key failed: {result.message}")
        return False


async def main():
    print("\n" + "="*60)
    print("   Humanlike Action Full Flow Test")
    print("   EnhancedAdbTools (straight input removed)")
    print("="*60)

    results = {}

    # 1. Device connection
    tools = await test_device_connection()
    results["device_connection"] = tools is not None

    if not tools:
        print("\nDevice connection failed, stopping test")
        return

    await asyncio.sleep(1)

    # 2. Humanlike tap
    results["humanlike_tap"] = await test_humanlike_tap(tools)
    await asyncio.sleep(1)

    # 3. Humanlike scroll
    results["humanlike_scroll"] = await test_humanlike_scroll(tools)
    await asyncio.sleep(1)

    # 4. URL open
    results["open_url"] = await test_open_url(tools)
    await asyncio.sleep(3)  # Wait for page load

    # 5. Portal connection
    results["portal"] = await test_portal_connection()
    await asyncio.sleep(1)

    # 6. Back key
    results["back_key"] = await test_back_key(tools)

    # Summary
    print("\n" + "="*60)
    print("   Test Results Summary")
    print("="*60)

    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {test_name}: {status}")

    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    print(f"\n  Total: {passed_count}/{total_count} passed")

    if passed_count == total_count:
        print("\n  All tests passed! Humanlike actions working correctly")
    else:
        print("\n  Some tests failed. Check logs")


if __name__ == "__main__":
    asyncio.run(main())
