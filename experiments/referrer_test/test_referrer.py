#!/usr/bin/env python3
"""
네이버 Referrer 검증 실험
========================
목적: CDP(Chrome DevTools Protocol)를 통해 검색 페이지에서 블로그로
네비게이션할 때 document.referrer가 어떻게 설정되는지 검증

실험 시나리오:
  A) 직접 URL 입력 (Direct) → document.referrer = ?
  B) 검색 페이지에서 CDP JS 네비게이션 → document.referrer = ?
  C) 검색 페이지에서 CDP 링크 클릭 시뮬레이션 → document.referrer = ?
"""

import asyncio
import json
import subprocess
import time
import sys

try:
    import websockets
except ImportError:
    print("websockets 패키지 설치 중...")
    subprocess.run([sys.executable, "-m", "pip", "install", "websockets"], check=True)
    import websockets

import urllib.request


# 설정
ADB_DEVICE = "localhost:5555"
CHROME_PACKAGE = "com.android.chrome"
CDP_LOCAL_PORT = 9222

# 테스트용 블로그 URL (아무 공개 블로그)
TEST_BLOG_URL = "https://m.blog.naver.com/naver_search/223718498498"
SEARCH_QUERY = "네이버 검색 알고리즘"
SEARCH_URL = f"https://search.naver.com/search.naver?where=blog&query={SEARCH_QUERY}"


def adb(cmd: str) -> str:
    """ADB 명령어 실행"""
    result = subprocess.run(
        ["adb", "-s", ADB_DEVICE, "shell", cmd],
        capture_output=True, text=True, timeout=15
    )
    return result.stdout.strip()


def adb_root(cmd: str) -> str:
    """root 권한 ADB 명령어"""
    result = subprocess.run(
        ["adb", "-s", ADB_DEVICE, "shell", "su", "-c", cmd],
        capture_output=True, text=True, timeout=15
    )
    return result.stdout.strip()


def open_chrome_url(url: str):
    """Chrome에서 URL 열기"""
    adb(f"am start -a android.intent.action.VIEW -d '{url}' {CHROME_PACKAGE}")


def setup_cdp_forward():
    """CDP 포트 포워딩 설정"""
    subprocess.run(
        ["adb", "-s", ADB_DEVICE, "forward", f"tcp:{CDP_LOCAL_PORT}",
         "localabstract:chrome_devtools_remote"],
        capture_output=True, timeout=10
    )


def get_cdp_targets() -> list:
    """CDP 타겟(탭) 목록 가져오기"""
    try:
        url = f"http://localhost:{CDP_LOCAL_PORT}/json"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  CDP 타겟 조회 실패: {e}")
        return []


def find_page_target(targets: list, url_contains: str = "") -> dict | None:
    """특정 URL을 포함하는 페이지 타겟 찾기"""
    for t in targets:
        if t.get("type") == "page":
            if not url_contains or url_contains in t.get("url", ""):
                return t
    # url_contains가 있는데 못 찾으면 첫번째 page 반환
    for t in targets:
        if t.get("type") == "page":
            return t
    return None


async def cdp_evaluate(ws_url: str, expression: str, timeout: float = 10) -> dict:
    """CDP Runtime.evaluate 실행"""
    async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
        msg = json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {"expression": expression, "returnByValue": True}
        })
        await ws.send(msg)

        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(resp)
                if data.get("id") == 1:
                    return data
            except asyncio.TimeoutError:
                break
    return {}


async def cdp_navigate(ws_url: str, url: str, timeout: float = 10) -> dict:
    """CDP Page.navigate 실행"""
    async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
        # Page.navigate
        msg = json.dumps({
            "id": 1,
            "method": "Page.navigate",
            "params": {"url": url}
        })
        await ws.send(msg)

        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(resp)
                if data.get("id") == 1:
                    return data
            except asyncio.TimeoutError:
                break
    return {}


async def get_referrer(ws_url: str) -> str:
    """현재 페이지의 document.referrer 값 가져오기"""
    result = await cdp_evaluate(ws_url, "document.referrer")
    try:
        return result["result"]["result"]["value"]
    except (KeyError, TypeError):
        return f"ERROR: {json.dumps(result, ensure_ascii=False)}"


async def get_current_url(ws_url: str) -> str:
    """현재 페이지 URL 가져오기"""
    result = await cdp_evaluate(ws_url, "window.location.href")
    try:
        return result["result"]["result"]["value"]
    except (KeyError, TypeError):
        return "ERROR"


def print_separator():
    print("=" * 70)


async def experiment_a():
    """실험 A: 직접 URL 입력 (Direct Navigation)"""
    print_separator()
    print("[실험 A] 직접 URL 입력 → document.referrer 확인")
    print_separator()

    print(f"  1. Chrome에서 블로그 URL 직접 열기: {TEST_BLOG_URL}")
    open_chrome_url(TEST_BLOG_URL)
    print("  2. 페이지 로드 대기 (6초)...")
    await asyncio.sleep(6)

    print("  3. CDP 연결 및 referrer 확인...")
    setup_cdp_forward()
    await asyncio.sleep(1)

    targets = get_cdp_targets()
    target = find_page_target(targets, "blog.naver")
    if not target:
        target = find_page_target(targets)

    if not target or "webSocketDebuggerUrl" not in target:
        print("  ❌ CDP 타겟을 찾을 수 없음")
        print(f"  타겟 목록: {json.dumps(targets, indent=2, ensure_ascii=False)[:500]}")
        return None

    ws_url = target["webSocketDebuggerUrl"]
    # localhost로 변환 (Android는 127.0.0.1로 반환할 수 있음)
    ws_url = ws_url.replace("127.0.0.1", "localhost")

    current_url = await get_current_url(ws_url)
    referrer = await get_referrer(ws_url)

    print(f"\n  결과:")
    print(f"    현재 URL:          {current_url}")
    print(f"    document.referrer: '{referrer}'")
    print(f"    판정: {'Direct (비어있음)' if not referrer else f'Referrer 존재: {referrer}'}")

    return {"experiment": "A_direct", "url": current_url, "referrer": referrer}


async def experiment_b():
    """실험 B: 검색 페이지 로딩 → CDP window.location.href로 네비게이션"""
    print_separator()
    print("[실험 B] 검색 페이지 → CDP JS 네비게이션 → document.referrer 확인")
    print_separator()

    print(f"  1. Chrome에서 검색 페이지 열기: {SEARCH_URL[:80]}...")
    open_chrome_url(SEARCH_URL)
    print("  2. 검색 페이지 로드 대기 (7초)...")
    await asyncio.sleep(7)

    print("  3. CDP 연결...")
    setup_cdp_forward()
    await asyncio.sleep(1)

    targets = get_cdp_targets()
    target = find_page_target(targets, "search.naver")
    if not target:
        target = find_page_target(targets)

    if not target or "webSocketDebuggerUrl" not in target:
        print("  ❌ CDP 타겟을 찾을 수 없음")
        return None

    ws_url = target["webSocketDebuggerUrl"]
    ws_url = ws_url.replace("127.0.0.1", "localhost")

    # 현재 검색 페이지 확인
    search_page_url = await get_current_url(ws_url)
    print(f"  4. 현재 페이지 확인: {search_page_url[:80]}...")

    # window.location.href로 블로그 이동
    print(f"  5. CDP로 블로그 이동 (window.location.href)...")
    navigate_js = f"window.location.href = '{TEST_BLOG_URL}'"
    await cdp_evaluate(ws_url, navigate_js)

    print("  6. 블로그 페이지 로드 대기 (7초)...")
    await asyncio.sleep(7)

    # 새 타겟 정보 가져오기 (페이지가 변경되었으므로)
    targets = get_cdp_targets()
    target = find_page_target(targets, "blog.naver")
    if not target:
        target = find_page_target(targets)

    if not target or "webSocketDebuggerUrl" not in target:
        print("  ❌ 블로그 페이지 CDP 타겟을 찾을 수 없음")
        return None

    ws_url = target["webSocketDebuggerUrl"]
    ws_url = ws_url.replace("127.0.0.1", "localhost")

    current_url = await get_current_url(ws_url)
    referrer = await get_referrer(ws_url)

    print(f"\n  결과:")
    print(f"    검색 페이지:       {search_page_url[:80]}...")
    print(f"    현재 URL:          {current_url[:80]}...")
    print(f"    document.referrer: '{referrer}'")

    if "search.naver.com" in referrer:
        print(f"    판정: ✅ 검색 유입으로 인식! referrer에 search.naver.com 포함")
    elif referrer:
        print(f"    판정: ⚠️ Referrer 있으나 검색이 아님: {referrer}")
    else:
        print(f"    판정: ❌ Referrer 비어있음 (Direct로 인식)")

    return {"experiment": "B_cdp_location", "url": current_url, "referrer": referrer,
            "search_page": search_page_url}


async def experiment_c():
    """실험 C: 검색 페이지 로딩 → CDP 링크 삽입+클릭으로 네비게이션"""
    print_separator()
    print("[실험 C] 검색 페이지 → CDP 링크 클릭 시뮬레이션 → document.referrer 확인")
    print_separator()

    print(f"  1. Chrome에서 검색 페이지 열기: {SEARCH_URL[:80]}...")
    open_chrome_url(SEARCH_URL)
    print("  2. 검색 페이지 로드 대기 (7초)...")
    await asyncio.sleep(7)

    print("  3. CDP 연결...")
    setup_cdp_forward()
    await asyncio.sleep(1)

    targets = get_cdp_targets()
    target = find_page_target(targets, "search.naver")
    if not target:
        target = find_page_target(targets)

    if not target or "webSocketDebuggerUrl" not in target:
        print("  ❌ CDP 타겟을 찾을 수 없음")
        return None

    ws_url = target["webSocketDebuggerUrl"]
    ws_url = ws_url.replace("127.0.0.1", "localhost")

    search_page_url = await get_current_url(ws_url)
    print(f"  4. 현재 페이지 확인: {search_page_url[:80]}...")

    # 링크 삽입 + 클릭으로 이동
    print(f"  5. CDP로 링크 삽입 후 클릭...")
    click_js = f"""
    (function() {{
        var a = document.createElement('a');
        a.href = '{TEST_BLOG_URL}';
        a.id = '_test_referrer_link';
        document.body.appendChild(a);
        a.click();
        return 'clicked';
    }})()
    """
    await cdp_evaluate(ws_url, click_js)

    print("  6. 블로그 페이지 로드 대기 (7초)...")
    await asyncio.sleep(7)

    targets = get_cdp_targets()
    target = find_page_target(targets, "blog.naver")
    if not target:
        target = find_page_target(targets)

    if not target or "webSocketDebuggerUrl" not in target:
        print("  ❌ 블로그 페이지 CDP 타겟을 찾을 수 없음")
        return None

    ws_url = target["webSocketDebuggerUrl"]
    ws_url = ws_url.replace("127.0.0.1", "localhost")

    current_url = await get_current_url(ws_url)
    referrer = await get_referrer(ws_url)

    print(f"\n  결과:")
    print(f"    검색 페이지:       {search_page_url[:80]}...")
    print(f"    현재 URL:          {current_url[:80]}...")
    print(f"    document.referrer: '{referrer}'")

    if "search.naver.com" in referrer:
        print(f"    판정: ✅ 검색 유입으로 인식! referrer에 search.naver.com 포함")
    elif referrer:
        print(f"    판정: ⚠️ Referrer 있으나 검색이 아님: {referrer}")
    else:
        print(f"    판정: ❌ Referrer 비어있음 (Direct로 인식)")

    return {"experiment": "C_cdp_link_click", "url": current_url, "referrer": referrer,
            "search_page": search_page_url}


async def experiment_d():
    """실험 D: CDP Page.navigate (referrer 파라미터 직접 설정)"""
    print_separator()
    print("[실험 D] CDP Page.navigate + referrer 파라미터 → document.referrer 확인")
    print_separator()

    # 먼저 빈 페이지로 이동
    print("  1. about:blank으로 초기화...")
    open_chrome_url("about:blank")
    await asyncio.sleep(3)

    setup_cdp_forward()
    await asyncio.sleep(1)

    targets = get_cdp_targets()
    target = find_page_target(targets)

    if not target or "webSocketDebuggerUrl" not in target:
        print("  ❌ CDP 타겟을 찾을 수 없음")
        return None

    ws_url = target["webSocketDebuggerUrl"]
    ws_url = ws_url.replace("127.0.0.1", "localhost")

    # Page.navigate with referrer parameter
    fake_referrer = f"https://search.naver.com/search.naver?where=blog&query={SEARCH_QUERY}"
    print(f"  2. CDP Page.navigate with referrer={fake_referrer[:60]}...")

    async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
        msg = json.dumps({
            "id": 1,
            "method": "Page.navigate",
            "params": {
                "url": TEST_BLOG_URL,
                "referrer": fake_referrer
            }
        })
        await ws.send(msg)

        start = time.time()
        while time.time() - start < 10:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(resp)
                if data.get("id") == 1:
                    break
            except asyncio.TimeoutError:
                break

    print("  3. 블로그 페이지 로드 대기 (7초)...")
    await asyncio.sleep(7)

    targets = get_cdp_targets()
    target = find_page_target(targets, "blog.naver")
    if not target:
        target = find_page_target(targets)

    if not target or "webSocketDebuggerUrl" not in target:
        print("  ❌ CDP 타겟을 찾을 수 없음")
        return None

    ws_url = target["webSocketDebuggerUrl"]
    ws_url = ws_url.replace("127.0.0.1", "localhost")

    current_url = await get_current_url(ws_url)
    referrer = await get_referrer(ws_url)

    print(f"\n  결과:")
    print(f"    설정한 referrer:   {fake_referrer[:80]}...")
    print(f"    현재 URL:          {current_url[:80]}...")
    print(f"    document.referrer: '{referrer}'")

    if "search.naver.com" in referrer:
        print(f"    판정: ✅ 검색 유입으로 인식! Page.navigate referrer 파라미터 유효")
    elif referrer:
        print(f"    판정: ⚠️ Referrer 있으나 검색이 아님: {referrer}")
    else:
        print(f"    판정: ❌ Referrer 비어있음")

    return {"experiment": "D_cdp_page_navigate_referrer", "url": current_url,
            "referrer": referrer, "fake_referrer": fake_referrer}


async def main():
    print("\n" + "=" * 70)
    print("  네이버 Referrer 검증 실험")
    print("  디바이스: SM-X826N | ADB: localhost:5555")
    print("  테스트 블로그: " + TEST_BLOG_URL[:50] + "...")
    print("=" * 70 + "\n")

    results = []

    # 실험 A
    try:
        r = await experiment_a()
        if r:
            results.append(r)
    except Exception as e:
        print(f"  실험 A 에러: {e}")

    await asyncio.sleep(3)

    # 실험 B
    try:
        r = await experiment_b()
        if r:
            results.append(r)
    except Exception as e:
        print(f"  실험 B 에러: {e}")

    await asyncio.sleep(3)

    # 실험 C
    try:
        r = await experiment_c()
        if r:
            results.append(r)
    except Exception as e:
        print(f"  실험 C 에러: {e}")

    await asyncio.sleep(3)

    # 실험 D
    try:
        r = await experiment_d()
        if r:
            results.append(r)
    except Exception as e:
        print(f"  실험 D 에러: {e}")

    # 결과 요약
    print_separator()
    print("\n📊 실험 결과 요약\n")
    print_separator()

    for r in results:
        exp = r["experiment"]
        ref = r["referrer"]
        has_search = "search.naver.com" in ref if ref else False

        status = "✅ 검색유입" if has_search else ("⚠️ 기타 referrer" if ref else "❌ Direct")
        print(f"  {exp:35s} | referrer: {ref[:50] if ref else '(empty)':50s} | {status}")

    print()

    # 결과 JSON 저장
    output_path = "/data/data/com.termux/files/home/ai-project/experiments/referrer_test/results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  결과 저장: {output_path}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
