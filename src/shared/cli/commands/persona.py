"""
Persona Commands - 페르소나 관리

naver persona list
naver persona create N
naver persona delete ID
"""

import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer

console = Console()


def _get_persona_manager():
    """PersonaManager 인스턴스 반환"""
    project_root = Path(__file__).parent.parent.parent.parent.parent
    sys.path.insert(0, str(project_root / "src" / "shared"))

    from persona_manager import PersonaManager
    return PersonaManager()


def list_personas(limit: int = 20, status_filter: Optional[str] = None):
    """페르소나 목록 조회"""

    try:
        manager = _get_persona_manager()
        personas = manager.get_all_personas()

        if status_filter:
            personas = [p for p in personas if p.status.value == status_filter]

        if not personas:
            console.print(Panel.fit(
                "[yellow]등록된 페르소나가 없습니다.[/yellow]\n\n"
                "힌트: [cyan]naver persona create 10[/cyan] 으로 생성하세요",
                title="페르소나 목록"
            ))
            return

        # 테이블 생성
        table = Table(title=f"페르소나 목록 ({len(personas)}개)")
        table.add_column("이름", style="cyan")
        table.add_column("상태", style="white")
        table.add_column("세션", justify="right")
        table.add_column("페이지뷰", justify="right")
        table.add_column("마지막 활동", style="dim")
        table.add_column("ID", style="dim")

        for p in personas[:limit]:
            status_color = {
                "active": "green",
                "cooldown": "yellow",
                "inactive": "dim",
            }.get(p.status.value, "white")

            table.add_row(
                p.name,
                f"[{status_color}]{p.status.value}[/{status_color}]",
                str(p.total_sessions),
                str(p.total_pageviews),
                p.last_active.strftime("%Y-%m-%d %H:%M"),
                p.persona_id[:8] + "..."
            )

        console.print(table)

        if len(personas) > limit:
            console.print(f"\n[dim]... 외 {len(personas) - limit}개 더 있음 (--limit으로 조정)[/dim]")

    except ImportError as e:
        console.print(f"[red]모듈 로드 실패: {e}[/red]")
    except Exception as e:
        console.print(f"[red]오류: {e}[/red]")


def create_personas(count: int = 1, prefix: str = "Persona", tags: Optional[str] = None):
    """페르소나 생성"""

    console.print(Panel.fit(
        f"[bold]페르소나 생성[/bold]\n"
        f"개수: {count}\n"
        f"접두사: {prefix}\n"
        f"태그: {tags or '없음'}",
        title="[blue]Create Personas[/blue]"
    ))

    try:
        manager = _get_persona_manager()

        tag_list = tags.split(",") if tags else None

        personas = manager.create_personas_batch(
            count=count,
            name_prefix=prefix,
            tags=tag_list
        )

        # 결과 출력
        table = Table(title="생성된 페르소나")
        table.add_column("이름", style="cyan")
        table.add_column("ANDROID_ID", style="dim")

        for p in personas:
            table.add_row(p.name, p.android_id[:16] + "...")

        console.print(table)
        console.print(f"\n[green]✓[/green] {len(personas)}개 페르소나 생성 완료")

    except ImportError as e:
        console.print(f"[red]모듈 로드 실패: {e}[/red]")
    except Exception as e:
        console.print(f"[red]오류: {e}[/red]")


def delete_persona(persona_id: str, force: bool = False):
    """페르소나 삭제"""

    try:
        manager = _get_persona_manager()

        # 페르소나 존재 확인
        persona = manager.get_persona(persona_id)
        if not persona:
            console.print(f"[red]페르소나를 찾을 수 없습니다: {persona_id}[/red]")
            return

        if not force:
            console.print(Panel.fit(
                f"[bold]삭제 대상[/bold]\n"
                f"이름: {persona.name}\n"
                f"ID: {persona.persona_id}\n"
                f"세션: {persona.total_sessions}회\n"
                f"페이지뷰: {persona.total_pageviews}회",
                title="[yellow]삭제 확인[/yellow]"
            ))

            confirm = typer.confirm("정말 삭제하시겠습니까?")
            if not confirm:
                console.print("[dim]취소됨[/dim]")
                return

        manager.delete_persona(persona_id)
        console.print(f"[green]✓[/green] 페르소나 삭제 완료: {persona.name}")

    except ImportError as e:
        console.print(f"[red]모듈 로드 실패: {e}[/red]")
    except Exception as e:
        console.print(f"[red]오류: {e}[/red]")
