"""
Naver AI Evolution CLI

통합 명령줄 인터페이스

사용법:
    naver --help
    naver run session --keywords "맛집"
    naver status
    naver persona list

Author: Naver AI Evolution System
Created: 2026-01-08
"""

import typer
from rich.console import Console
from rich.panel import Panel
from typing import Optional

# CLI 앱 생성
app = typer.Typer(
    name="naver",
    help="Naver AI Evolution System CLI",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()

# 서브 커맨드 그룹
run_app = typer.Typer(help="세션/캠페인 실행")
persona_app = typer.Typer(help="페르소나 관리")
test_app = typer.Typer(help="테스트 실행")
debug_app = typer.Typer(help="디버깅 도구")

app.add_typer(run_app, name="run")
app.add_typer(persona_app, name="persona")
app.add_typer(test_app, name="test")
app.add_typer(debug_app, name="debug")


# =============================================================================
# Root Commands
# =============================================================================

@app.command()
def status(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="상세 정보 출력"),
):
    """시스템 상태 확인"""
    from .commands.status import show_status
    show_status(verbose=verbose)


@app.command()
def version():
    """버전 정보 출력"""
    console.print(Panel.fit(
        "[bold blue]Naver AI Evolution System[/bold blue]\n"
        "Version: [green]0.9.0[/green]\n"
        "Python CLI for Android automation",
        title="Version Info"
    ))


# =============================================================================
# Run Commands
# =============================================================================

@run_app.command("session")
def run_session(
    keywords: list[str] = typer.Option(None, "--keywords", "-k", help="검색 키워드 목록"),
    urls: list[str] = typer.Option(None, "--urls", "-u", help="직접 방문할 URL 목록"),
    pageviews: int = typer.Option(3, "--pageviews", "-p", help="세션당 페이지뷰 수"),
    search_type: str = typer.Option("blog", "--search-type", "-t", help="검색 타입 (blog/news/cafe)"),
    no_portal: bool = typer.Option(False, "--no-portal", help="Portal 없이 좌표 기반 실행"),
    dry_run: bool = typer.Option(False, "--dry-run", help="실제 실행 없이 계획만 출력"),
):
    """단일 세션 실행

    Examples:
        naver run session --keywords "맛집" "여행"
        naver run session --urls "https://blog.naver.com/..."
        naver run session -k "IT뉴스" -p 5
    """
    from .commands.run import execute_session
    execute_session(
        keywords=keywords,
        urls=urls,
        pageviews=pageviews,
        search_type=search_type,
        no_portal=no_portal,
        dry_run=dry_run,
    )


@run_app.command("campaign")
def run_campaign(
    config: str = typer.Option(None, "--config", "-c", help="캠페인 설정 파일 경로"),
    sessions: int = typer.Option(5, "--sessions", "-s", help="실행할 세션 수"),
    keywords: list[str] = typer.Option(None, "--keywords", "-k", help="검색 키워드 목록"),
    interval_min: int = typer.Option(5, "--interval-min", help="세션 간 최소 간격 (분)"),
    interval_max: int = typer.Option(15, "--interval-max", help="세션 간 최대 간격 (분)"),
):
    """다중 세션 캠페인 실행

    Examples:
        naver run campaign --sessions 10 --keywords "맛집"
        naver run campaign --config campaign.yaml
    """
    from .commands.run import execute_campaign
    execute_campaign(
        config=config,
        sessions=sessions,
        keywords=keywords,
        interval_min=interval_min,
        interval_max=interval_max,
    )


# =============================================================================
# Persona Commands
# =============================================================================

@persona_app.command("list")
def persona_list(
    limit: int = typer.Option(20, "--limit", "-l", help="출력할 최대 개수"),
    status_filter: str = typer.Option(None, "--status", "-s", help="상태로 필터 (active/cooldown/inactive)"),
):
    """페르소나 목록 조회

    Examples:
        naver persona list
        naver persona list --status active
    """
    from .commands.persona import list_personas
    list_personas(limit=limit, status_filter=status_filter)


@persona_app.command("create")
def persona_create(
    count: int = typer.Argument(1, help="생성할 페르소나 수"),
    prefix: str = typer.Option("Persona", "--prefix", "-p", help="이름 접두사"),
    tags: str = typer.Option(None, "--tags", "-t", help="태그 (쉼표 구분)"),
):
    """페르소나 생성

    Examples:
        naver persona create 10
        naver persona create 5 --prefix "TestUser"
    """
    from .commands.persona import create_personas
    create_personas(count=count, prefix=prefix, tags=tags)


@persona_app.command("delete")
def persona_delete(
    persona_id: str = typer.Argument(..., help="삭제할 페르소나 ID"),
    force: bool = typer.Option(False, "--force", "-f", help="확인 없이 삭제"),
):
    """페르소나 삭제

    Examples:
        naver persona delete abc123
        naver persona delete abc123 --force
    """
    from .commands.persona import delete_persona
    delete_persona(persona_id=persona_id, force=force)


# =============================================================================
# Test Commands
# =============================================================================

@test_app.command("smoke")
def test_smoke():
    """스모크 테스트 (빠른 검증)

    변경 후 기본 동작 확인용
    """
    from .commands.test import run_smoke_test
    run_smoke_test()


@test_app.command("unit")
def test_unit(
    module: str = typer.Option(None, "--module", "-m", help="특정 모듈만 테스트"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="상세 출력"),
):
    """단위 테스트 실행"""
    from .commands.test import run_unit_tests
    run_unit_tests(module=module, verbose=verbose)


@test_app.command("e2e")
def test_e2e(
    scenario: str = typer.Option(None, "--scenario", "-s", help="특정 시나리오만 실행"),
):
    """E2E 테스트 실행 (실제 디바이스 필요)"""
    from .commands.test import run_e2e_tests
    run_e2e_tests(scenario=scenario)


# =============================================================================
# Debug Commands
# =============================================================================

@debug_app.command("portal")
def debug_portal():
    """Portal 연결 상태 확인"""
    from .commands.debug import check_portal
    check_portal()


@debug_app.command("device")
def debug_device():
    """디바이스 연결 상태 확인"""
    from .commands.debug import check_device
    check_device()


@debug_app.command("tap")
def debug_tap(
    x: int = typer.Argument(..., help="X 좌표"),
    y: int = typer.Argument(..., help="Y 좌표"),
):
    """지정 좌표 탭 테스트

    Examples:
        naver debug tap 540 1200
    """
    from .commands.debug import test_tap
    test_tap(x=x, y=y)


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """CLI 진입점"""
    app()


if __name__ == "__main__":
    main()
