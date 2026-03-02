"""
Debug Commands - 디버깅 도구

naver debug portal
naver debug device
naver debug tap X Y
"""

import asyncio
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent


def check_portal():
    """Portal 연결 상태 확인"""

    console.print(Panel.fit(
        "[bold]DroidRun Portal 상태[/bold]",
        title="[blue]Debug Portal[/blue]"
    ))

    # 1. APK 설치 확인
    console.print("\n[cyan]1. APK 설치 확인[/cyan]")
    try:
        result = subprocess.run(
            ["adb", "shell", "pm", "list", "packages", "-3"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if "com.droidrun.portal" in result.stdout:
            console.print("   [green]✓[/green] Portal APK 설치됨")

            # 버전 확인
            version_result = subprocess.run(
                ["adb", "shell", "dumpsys", "package", "com.droidrun.portal", "|", "grep", "versionName"],
                capture_output=True,
                text=True,
                timeout=10,
                shell=True
            )
            console.print(f"   버전: {version_result.stdout.strip() or 'Unknown'}")
        else:
            console.print("   [red]✗[/red] Portal APK 미설치")
            return

    except Exception as e:
        console.print(f"   [red]✗[/red] 확인 실패: {e}")
        return

    # 2. Accessibility Service 확인
    console.print("\n[cyan]2. Accessibility Service 확인[/cyan]")
    try:
        result = subprocess.run(
            ["adb", "shell", "settings", "get", "secure", "enabled_accessibility_services"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if "droidrun" in result.stdout.lower():
            console.print("   [green]✓[/green] Accessibility Service 활성화")
        else:
            console.print("   [yellow]![/yellow] Accessibility Service 비활성화")
            console.print("   설정 > 접근성 > Portal에서 활성화하세요")

    except Exception as e:
        console.print(f"   [red]✗[/red] 확인 실패: {e}")

    # 3. Content Provider 테스트
    console.print("\n[cyan]3. Content Provider 테스트[/cyan]")
    try:
        result = subprocess.run(
            ["adb", "shell", "content", "query", "--uri", "content://com.droidrun.portal/state"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if "result=" in result.stdout and "error" not in result.stdout.lower():
            console.print("   [green]✓[/green] Content Provider 응답 정상")

            # UI 트리 크기
            import json
            try:
                # 응답 파싱
                if "data=" in result.stdout:
                    data_start = result.stdout.find("data=") + 5
                    data_json = result.stdout[data_start:].strip()
                    if data_json:
                        parsed = json.loads(data_json)
                        if "a11y_tree" in parsed:
                            tree_size = len(parsed.get("a11y_tree", []))
                            console.print(f"   UI 트리 노드 수: {tree_size}")
            except:
                pass
        else:
            console.print("   [yellow]![/yellow] Content Provider 응답 없음")
            console.print(f"   응답: {result.stdout[:200]}...")

    except Exception as e:
        console.print(f"   [red]✗[/red] 테스트 실패: {e}")


def check_device():
    """디바이스 연결 상태 확인"""

    console.print(Panel.fit(
        "[bold]디바이스 연결 상태[/bold]",
        title="[blue]Debug Device[/blue]"
    ))

    # 1. ADB 연결
    console.print("\n[cyan]1. ADB 연결[/cyan]")
    try:
        result = subprocess.run(
            ["adb", "devices", "-l"],
            capture_output=True,
            text=True,
            timeout=5
        )

        lines = result.stdout.strip().split("\n")[1:]
        devices = [l for l in lines if l.strip()]

        if devices:
            console.print(f"   [green]✓[/green] 연결된 디바이스: {len(devices)}개")
            for d in devices:
                console.print(f"   {d}")
        else:
            console.print("   [yellow]![/yellow] 연결된 디바이스 없음")
            return

    except FileNotFoundError:
        console.print("   [red]✗[/red] ADB를 찾을 수 없습니다")
        return
    except Exception as e:
        console.print(f"   [red]✗[/red] 오류: {e}")
        return

    # 2. 화면 크기
    console.print("\n[cyan]2. 화면 정보[/cyan]")
    try:
        result = subprocess.run(
            ["adb", "shell", "wm", "size"],
            capture_output=True,
            text=True,
            timeout=5
        )
        console.print(f"   {result.stdout.strip()}")

        density = subprocess.run(
            ["adb", "shell", "wm", "density"],
            capture_output=True,
            text=True,
            timeout=5
        )
        console.print(f"   {density.stdout.strip()}")

    except Exception as e:
        console.print(f"   [red]✗[/red] 오류: {e}")

    # 3. 루팅 상태
    console.print("\n[cyan]3. 루팅 상태[/cyan]")
    try:
        result = subprocess.run(
            ["adb", "shell", "su", "-c", "id"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if "uid=0" in result.stdout:
            console.print("   [green]✓[/green] 루팅됨 (root 접근 가능)")
        else:
            console.print("   [yellow]![/yellow] 루팅 안됨 또는 root 접근 불가")

    except Exception as e:
        console.print(f"   [yellow]![/yellow] 루팅 확인 실패: {e}")

    # 4. ANDROID_ID
    console.print("\n[cyan]4. ANDROID_ID[/cyan]")
    try:
        result = subprocess.run(
            ["adb", "shell", "settings", "get", "secure", "android_id"],
            capture_output=True,
            text=True,
            timeout=5
        )
        console.print(f"   {result.stdout.strip()}")

    except Exception as e:
        console.print(f"   [red]✗[/red] 오류: {e}")


def test_tap(x: int, y: int):
    """지정 좌표 탭 테스트"""

    console.print(Panel.fit(
        f"[bold]탭 테스트[/bold]\n"
        f"좌표: ({x}, {y})\n"
        "[yellow]휴먼라이크 동작으로 실행[/yellow]",
        title="[blue]Debug Tap[/blue]"
    ))

    try:
        sys.path.insert(0, str(PROJECT_ROOT / "src" / "shared"))

        from device_tools import EnhancedAdbTools, AdbConfig

        # 화면 크기 확인
        size_result = subprocess.run(
            ["adb", "shell", "wm", "size"],
            capture_output=True,
            text=True,
            timeout=5
        )

        width, height = 1080, 2400
        if "Physical size:" in size_result.stdout:
            size_str = size_result.stdout.split("Physical size:")[1].strip()
            w, h = size_str.split("x")
            width, height = int(w), int(h)

        config = AdbConfig(
            serial=None,
            screen_width=width,
            screen_height=height,
        )

        tools = EnhancedAdbTools(config)

        console.print(f"\n탭 실행 중... ({x}, {y})")

        result = asyncio.run(tools.tap(x, y))

        if result.success:
            details = result.details or {}
            actual_x = details.get("actual_x", x)
            actual_y = details.get("actual_y", y)
            offset_x = details.get("offset_x", 0)
            offset_y = details.get("offset_y", 0)

            console.print(f"\n[green]✓ 탭 성공[/green]")
            console.print(f"  원래 좌표: ({x}, {y})")
            console.print(f"  실제 좌표: ({actual_x}, {actual_y})")
            console.print(f"  오프셋: ({offset_x:+d}, {offset_y:+d})")
        else:
            console.print(f"\n[red]✗ 탭 실패: {result.message}[/red]")

    except ImportError as e:
        console.print(f"[red]모듈 로드 실패: {e}[/red]")

        # fallback: 직접 ADB 실행
        console.print("\n[yellow]Fallback: 직접 ADB 탭 실행[/yellow]")
        try:
            subprocess.run(
                ["adb", "shell", "input", "tap", str(x), str(y)],
                timeout=5
            )
            console.print(f"[green]✓ ADB 탭 실행 완료[/green]")
        except Exception as e2:
            console.print(f"[red]✗ 실패: {e2}[/red]")

    except Exception as e:
        console.print(f"[red]오류: {e}[/red]")
