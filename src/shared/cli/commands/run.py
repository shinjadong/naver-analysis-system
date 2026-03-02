"""
Run Commands - 세션/캠페인 실행

naver run session
naver run campaign
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional, List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# 기본 키워드 목록
DEFAULT_KEYWORDS = [
    "맛집 추천",
    "여행 블로그",
    "IT 뉴스",
    "파이썬 강좌",
    "주식 투자",
    "부동산 정보",
    "건강 관리",
    "운동 루틴",
    "요리 레시피",
    "독서 추천",
]


def execute_session(
    keywords: Optional[List[str]] = None,
    urls: Optional[List[str]] = None,
    pageviews: int = 3,
    search_type: str = "blog",
    no_portal: bool = False,
    dry_run: bool = False,
):
    """단일 세션 실행"""

    # 설정 출력
    console.print(Panel.fit(
        f"[bold]세션 설정[/bold]\n"
        f"키워드: {keywords or DEFAULT_KEYWORDS[:pageviews]}\n"
        f"URL: {urls or '없음'}\n"
        f"페이지뷰: {pageviews}\n"
        f"검색 타입: {search_type}\n"
        f"Portal 사용: {'아니오' if no_portal else '예'}",
        title="[blue]Run Session[/blue]"
    ))

    if dry_run:
        console.print("\n[yellow]--dry-run: 실제 실행 없이 종료[/yellow]")
        return

    # 실제 실행
    try:
        # 프로젝트 루트 추가
        project_root = Path(__file__).parent.parent.parent.parent.parent
        sys.path.insert(0, str(project_root / "src" / "shared"))

        from pipeline import NaverSessionPipeline, PipelineConfig

        config = PipelineConfig(
            use_portal=not no_portal,
            max_pageviews_per_session=pageviews,
        )

        pipeline = NaverSessionPipeline(config=config)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("세션 실행 중...", total=None)

            if urls:
                result = asyncio.run(pipeline.run_session(urls=urls, pageviews=pageviews))
            else:
                kw = keywords if keywords else DEFAULT_KEYWORDS[:pageviews]
                result = asyncio.run(pipeline.run_session(
                    keywords=kw,
                    pageviews=pageviews,
                    search_type=search_type
                ))

        # 결과 출력
        _print_session_result(result)

    except ImportError as e:
        console.print(f"[red]모듈 import 실패: {e}[/red]")
        console.print("[yellow]힌트: pip install -e . 로 패키지를 설치하세요[/yellow]")
    except Exception as e:
        console.print(f"[red]오류 발생: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())


def execute_campaign(
    config: Optional[str] = None,
    sessions: int = 5,
    keywords: Optional[List[str]] = None,
    interval_min: int = 5,
    interval_max: int = 15,
):
    """다중 세션 캠페인 실행"""

    console.print(Panel.fit(
        f"[bold]캠페인 설정[/bold]\n"
        f"설정 파일: {config or '없음'}\n"
        f"세션 수: {sessions}\n"
        f"키워드: {keywords or DEFAULT_KEYWORDS}\n"
        f"세션 간격: {interval_min}~{interval_max}분",
        title="[blue]Run Campaign[/blue]"
    ))

    try:
        project_root = Path(__file__).parent.parent.parent.parent.parent
        sys.path.insert(0, str(project_root / "src" / "shared"))

        from pipeline import NaverSessionPipeline, PipelineConfig

        pipeline_config = PipelineConfig(use_portal=True)
        pipeline = NaverSessionPipeline(config=pipeline_config)

        kw = keywords if keywords else DEFAULT_KEYWORDS

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"캠페인 실행 중 (0/{sessions})...", total=sessions)

            results = asyncio.run(pipeline.run_multiple_sessions(
                keywords=kw,
                sessions=sessions,
                pageviews_per_session=3,
                session_interval_min=interval_min,
                session_interval_max=interval_max,
            ))

        # 결과 요약
        _print_campaign_result(results)

    except ImportError as e:
        console.print(f"[red]모듈 import 실패: {e}[/red]")
    except Exception as e:
        console.print(f"[red]오류 발생: {e}[/red]")


def _print_session_result(result):
    """세션 결과 출력"""
    status = "[green]성공[/green]" if result.success else "[red]실패[/red]"

    table = Table(title="세션 결과")
    table.add_column("항목", style="cyan")
    table.add_column("값", style="white")

    table.add_row("상태", status)
    table.add_row("페르소나", f"{result.persona_name} ({result.persona_id[:8]}...)")
    table.add_row("방문 수", str(len(result.visits)))
    table.add_row("총 체류시간", f"{result.total_dwell_time}초")
    table.add_row("총 스크롤", f"{result.total_scrolls}회")
    table.add_row("소요 시간", f"{result.duration_sec:.1f}초")

    console.print(table)

    if result.visits:
        console.print("\n[bold]방문 상세:[/bold]")
        for i, visit in enumerate(result.visits):
            icon = "[green]✓[/green]" if visit.success else "[red]✗[/red]"
            console.print(f"  {i+1}. {icon} {visit.content_type}: {visit.dwell_time}s, {visit.scroll_count} scrolls")


def _print_campaign_result(results):
    """캠페인 결과 출력"""
    successful = sum(1 for r in results if r.success)
    total_visits = sum(len(r.visits) for r in results)
    total_dwell = sum(r.total_dwell_time for r in results)

    table = Table(title="캠페인 결과 요약")
    table.add_column("항목", style="cyan")
    table.add_column("값", style="white")

    table.add_row("성공 세션", f"{successful}/{len(results)}")
    table.add_row("총 방문", str(total_visits))
    table.add_row("총 체류시간", f"{total_dwell}초 ({total_dwell/60:.1f}분)")

    console.print(table)

    console.print("\n[bold]세션별 결과:[/bold]")
    for i, result in enumerate(results):
        icon = "[green]✓[/green]" if result.success else "[red]✗[/red]"
        console.print(f"  {i+1}. {icon} {result.persona_name}: {len(result.visits)} visits, {result.total_dwell_time}s")
