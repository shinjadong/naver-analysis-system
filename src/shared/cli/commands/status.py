"""
Status Command - 시스템 상태 확인

naver status
naver status --verbose
"""

import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def show_status(verbose: bool = False):
    """시스템 상태 확인"""

    console.print(Panel.fit(
        "[bold blue]Naver AI Evolution System[/bold blue]\n"
        "시스템 상태 확인 중...",
        title="Status"
    ))

    # 1. ADB 연결 상태
    _check_adb_status()

    # 2. Portal 상태
    _check_portal_status()

    # 3. 페르소나 통계
    _check_persona_stats()

    if verbose:
        # 4. 모듈 상태
        _check_module_status()


def _check_adb_status():
    """ADB 연결 상태 확인"""
    console.print("\n[bold cyan][ ADB 연결 ][/bold cyan]")

    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=5
        )

        lines = result.stdout.strip().split("\n")[1:]  # 첫 줄은 "List of devices attached"
        devices = [l.split("\t")[0] for l in lines if l.strip() and "device" in l]

        if devices:
            console.print(f"  [green]✓[/green] 연결된 디바이스: {len(devices)}개")
            for d in devices:
                console.print(f"    - {d}")
        else:
            console.print("  [yellow]![/yellow] 연결된 디바이스 없음")

    except FileNotFoundError:
        console.print("  [red]✗[/red] ADB를 찾을 수 없습니다")
    except subprocess.TimeoutExpired:
        console.print("  [red]✗[/red] ADB 응답 시간 초과")
    except Exception as e:
        console.print(f"  [red]✗[/red] 오류: {e}")


def _check_portal_status():
    """Portal 상태 확인"""
    console.print("\n[bold cyan][ DroidRun Portal ][/bold cyan]")

    try:
        # Portal APK 설치 확인
        result = subprocess.run(
            ["adb", "shell", "pm", "list", "packages", "com.droidrun.portal"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if "com.droidrun.portal" in result.stdout:
            console.print("  [green]✓[/green] Portal APK 설치됨")

            # Accessibility Service 확인
            acc_result = subprocess.run(
                ["adb", "shell", "settings", "get", "secure", "enabled_accessibility_services"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if "droidrun" in acc_result.stdout.lower():
                console.print("  [green]✓[/green] Accessibility Service 활성화")
            else:
                console.print("  [yellow]![/yellow] Accessibility Service 비활성화")
        else:
            console.print("  [yellow]![/yellow] Portal APK 미설치")

    except FileNotFoundError:
        console.print("  [red]✗[/red] ADB를 찾을 수 없습니다")
    except Exception as e:
        console.print(f"  [red]✗[/red] 확인 실패: {e}")


def _check_persona_stats():
    """페르소나 통계 확인"""
    console.print("\n[bold cyan][ 페르소나 통계 ][/bold cyan]")

    try:
        project_root = Path(__file__).parent.parent.parent.parent.parent
        sys.path.insert(0, str(project_root / "src" / "shared"))

        from persona_manager import PersonaManager

        manager = PersonaManager()
        personas = manager.get_all_personas()

        if personas:
            active = sum(1 for p in personas if p.status.value == "active")
            cooldown = sum(1 for p in personas if p.status.value == "cooldown")
            total_sessions = sum(p.total_sessions for p in personas)
            total_pageviews = sum(p.total_pageviews for p in personas)

            console.print(f"  총 페르소나: {len(personas)}개")
            console.print(f"  - Active: {active}")
            console.print(f"  - Cooldown: {cooldown}")
            console.print(f"  총 세션: {total_sessions}회")
            console.print(f"  총 페이지뷰: {total_pageviews}회")
        else:
            console.print("  [yellow]![/yellow] 등록된 페르소나 없음")
            console.print("  힌트: [cyan]naver persona create 10[/cyan]")

    except ImportError:
        console.print("  [yellow]![/yellow] PersonaManager 로드 실패")
    except Exception as e:
        console.print(f"  [red]✗[/red] 오류: {e}")


def _check_module_status():
    """모듈 상태 확인"""
    console.print("\n[bold cyan][ 모듈 상태 ][/bold cyan]")

    modules = [
        ("pipeline", "NaverSessionPipeline"),
        ("smart_executor.executor", "SmartExecutor"),
        ("portal_client", "PortalClient"),
        ("device_tools", "EnhancedAdbTools"),
        ("persona_manager", "PersonaManager"),
    ]

    project_root = Path(__file__).parent.parent.parent.parent.parent
    sys.path.insert(0, str(project_root / "src" / "shared"))

    for module_name, class_name in modules:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            console.print(f"  [green]✓[/green] {class_name}")
        except ImportError as e:
            console.print(f"  [red]✗[/red] {class_name}: {e}")
        except Exception as e:
            console.print(f"  [yellow]![/yellow] {class_name}: {e}")
