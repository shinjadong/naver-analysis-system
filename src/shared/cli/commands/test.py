"""
Test Commands - 테스트 실행

naver test smoke
naver test unit
naver test e2e
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel

console = Console()

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent


def run_smoke_test():
    """스모크 테스트 - 기본 동작 빠른 검증"""

    console.print(Panel.fit(
        "[bold]스모크 테스트[/bold]\n"
        "기본 모듈 로드 및 연결 상태 확인",
        title="[blue]Smoke Test[/blue]"
    ))

    results = []

    # 1. 모듈 import 테스트
    console.print("\n[cyan]1. 모듈 로드 테스트[/cyan]")
    modules = [
        ("device_tools", "EnhancedAdbTools"),
        ("portal_client", "PortalClient"),
        ("pipeline", "NaverSessionPipeline"),
        ("smart_executor.executor", "SmartExecutor"),
        ("persona_manager", "PersonaManager"),
    ]

    sys.path.insert(0, str(PROJECT_ROOT / "src" / "shared"))

    for module_name, class_name in modules:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            console.print(f"   [green]✓[/green] {class_name}")
            results.append(True)
        except Exception as e:
            console.print(f"   [red]✗[/red] {class_name}: {e}")
            results.append(False)

    # 2. ADB 연결 테스트
    console.print("\n[cyan]2. ADB 연결 테스트[/cyan]")
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "device" in result.stdout and "List" in result.stdout:
            console.print("   [green]✓[/green] ADB 연결 정상")
            results.append(True)
        else:
            console.print("   [yellow]![/yellow] ADB 연결 없음 (디바이스 미연결)")
            results.append(True)  # ADB 자체는 작동함
    except FileNotFoundError:
        console.print("   [red]✗[/red] ADB를 찾을 수 없음")
        results.append(False)
    except Exception as e:
        console.print(f"   [red]✗[/red] ADB 오류: {e}")
        results.append(False)

    # 3. 설정 파일 확인
    console.print("\n[cyan]3. 설정 파일 확인[/cyan]")
    config_files = [
        ("pyproject.toml", PROJECT_ROOT / "pyproject.toml"),
        ("config/default.yaml", PROJECT_ROOT / "config" / "default.yaml"),
    ]

    for name, path in config_files:
        if path.exists():
            console.print(f"   [green]✓[/green] {name}")
            results.append(True)
        else:
            console.print(f"   [yellow]![/yellow] {name} (없음)")
            results.append(True)  # 선택적 파일

    # 결과 요약
    passed = sum(results)
    total = len(results)

    console.print(Panel.fit(
        f"통과: {passed}/{total}\n"
        f"{'[green]모든 테스트 통과[/green]' if passed == total else '[yellow]일부 테스트 실패[/yellow]'}",
        title="스모크 테스트 결과"
    ))


def run_unit_tests(module: Optional[str] = None, verbose: bool = False):
    """단위 테스트 실행"""

    console.print(Panel.fit(
        f"[bold]단위 테스트[/bold]\n"
        f"모듈: {module or '전체'}\n"
        f"상세 출력: {'예' if verbose else '아니오'}",
        title="[blue]Unit Tests[/blue]"
    ))

    # pytest 실행
    cmd = ["python", "-m", "pytest", str(PROJECT_ROOT / "tests")]

    if module:
        cmd.extend(["-k", module])

    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=not verbose,
            text=True
        )

        if result.returncode == 0:
            console.print("\n[green]✓ 모든 테스트 통과[/green]")
        else:
            console.print("\n[red]✗ 테스트 실패[/red]")
            if not verbose and result.stdout:
                console.print(result.stdout)
            if not verbose and result.stderr:
                console.print(result.stderr)

    except FileNotFoundError:
        console.print("[red]pytest를 찾을 수 없습니다[/red]")
        console.print("힌트: [cyan]pip install pytest[/cyan]")
    except Exception as e:
        console.print(f"[red]오류: {e}[/red]")


def run_e2e_tests(scenario: Optional[str] = None):
    """E2E 테스트 실행"""

    console.print(Panel.fit(
        f"[bold]E2E 테스트[/bold]\n"
        f"시나리오: {scenario or '전체'}\n"
        "[yellow]주의: 실제 디바이스 연결 필요[/yellow]",
        title="[blue]E2E Tests[/blue]"
    ))

    # ADB 연결 확인
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=5
        )

        lines = result.stdout.strip().split("\n")[1:]
        devices = [l for l in lines if l.strip() and "device" in l]

        if not devices:
            console.print("[red]✗ 연결된 디바이스가 없습니다[/red]")
            console.print("E2E 테스트에는 실제 디바이스 연결이 필요합니다.")
            return

        console.print(f"[green]✓[/green] 디바이스 연결됨: {len(devices)}개")

    except Exception as e:
        console.print(f"[red]ADB 확인 실패: {e}[/red]")
        return

    # E2E 테스트 실행
    e2e_dir = PROJECT_ROOT / "tests" / "e2e"

    if not e2e_dir.exists():
        console.print(f"[yellow]E2E 테스트 디렉토리가 없습니다: {e2e_dir}[/yellow]")
        console.print("힌트: tests/e2e/ 디렉토리에 테스트를 추가하세요")
        return

    cmd = ["python", "-m", "pytest", str(e2e_dir), "-v"]

    if scenario:
        cmd.extend(["-k", scenario])

    try:
        subprocess.run(cmd, cwd=PROJECT_ROOT)
    except Exception as e:
        console.print(f"[red]오류: {e}[/red]")
