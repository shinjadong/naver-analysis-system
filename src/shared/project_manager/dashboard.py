"""
Project Dashboard (전광판)

프로젝트 상태 시각화 및 모니터링
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timedelta
from enum import Enum

from .schema import Project, ProjectStatus, ProjectStats, DailyStats


class TrendDirection(Enum):
    """트렌드 방향"""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


@dataclass
class MetricCard:
    """메트릭 카드"""
    name: str
    value: Any
    unit: str = ""
    trend: TrendDirection = TrendDirection.STABLE
    trend_value: float = 0.0
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "trend": self.trend.value,
            "trend_value": self.trend_value,
            "description": self.description,
        }


@dataclass
class TargetProgress:
    """타겟 진행 상황"""
    target_id: str
    keyword: str
    blog_title: str
    current: int
    target: int
    progress: float
    last_executed: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed

    def to_dict(self) -> dict:
        return {
            "target_id": self.target_id,
            "keyword": self.keyword,
            "blog_title": self.blog_title,
            "current": self.current,
            "target": self.target,
            "progress": self.progress,
            "last_executed": self.last_executed,
            "status": self.status,
        }


@dataclass
class PersonaStats:
    """페르소나 통계"""
    persona_id: str
    executions: int
    success_rate: float
    avg_dwell_time: float
    last_active: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "persona_id": self.persona_id,
            "executions": self.executions,
            "success_rate": self.success_rate,
            "avg_dwell_time": self.avg_dwell_time,
            "last_active": self.last_active,
        }


@dataclass
class DashboardData:
    """전광판 데이터"""
    project_id: str
    project_name: str
    status: str
    generated_at: datetime = field(default_factory=datetime.now)

    # 요약 메트릭
    metrics: List[MetricCard] = field(default_factory=list)

    # 타겟 진행 상황
    target_progress: List[TargetProgress] = field(default_factory=list)

    # 페르소나 통계
    persona_stats: List[PersonaStats] = field(default_factory=list)

    # 일별 차트 데이터
    daily_chart: List[Dict[str, Any]] = field(default_factory=list)

    # 최근 실행 기록
    recent_executions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "status": self.status,
            "generated_at": self.generated_at.isoformat(),
            "metrics": [m.to_dict() for m in self.metrics],
            "target_progress": [t.to_dict() for t in self.target_progress],
            "persona_stats": [p.to_dict() for p in self.persona_stats],
            "daily_chart": self.daily_chart,
            "recent_executions": self.recent_executions,
        }

    def to_ascii(self) -> str:
        """ASCII 전광판 출력"""
        lines = []
        width = 70

        # 헤더
        lines.append("=" * width)
        lines.append(f"  📊 {self.project_name}")
        lines.append(f"  Status: {self.status.upper()} | Generated: {self.generated_at.strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * width)

        # 메트릭 카드
        lines.append("\n📈 Key Metrics")
        lines.append("-" * width)
        for m in self.metrics[:4]:
            trend_icon = {"up": "↑", "down": "↓", "stable": "→"}[m.trend.value]
            lines.append(f"  {m.name}: {m.value}{m.unit} {trend_icon}")

        # 타겟 진행률
        lines.append("\n🎯 Target Progress")
        lines.append("-" * width)
        for t in self.target_progress[:5]:
            bar_width = 30
            filled = int(t.progress / 100 * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)
            status_icon = {"completed": "✅", "in_progress": "🔄", "pending": "⏳"}[t.status]
            lines.append(f"  {status_icon} [{bar}] {t.progress:.0f}%")
            lines.append(f"     {t.keyword[:15]} → {t.blog_title[:25]}")
            lines.append(f"     {t.current}/{t.target} clicks")

        # 페르소나 통계
        if self.persona_stats:
            lines.append("\n👤 Persona Stats")
            lines.append("-" * width)
            for p in self.persona_stats[:5]:
                lines.append(f"  {p.persona_id}: {p.executions} exec, {p.success_rate:.0f}% success")

        # 일별 트렌드
        if self.daily_chart:
            lines.append("\n📅 Daily Trend (Last 7 days)")
            lines.append("-" * width)
            max_val = max(d.get("executions", 0) for d in self.daily_chart) or 1
            for d in self.daily_chart[-7:]:
                bar_len = int(d.get("executions", 0) / max_val * 20)
                bar = "▓" * bar_len
                lines.append(f"  {d['date'][-5:]}: {bar} {d.get('executions', 0)}")

        lines.append("\n" + "=" * width)

        return "\n".join(lines)


class ProjectDashboard:
    """프로젝트 대시보드 생성기"""

    def __init__(self, project: Project):
        self.project = project

    def generate(self) -> DashboardData:
        """대시보드 데이터 생성"""
        stats = self.project.get_stats()

        dashboard = DashboardData(
            project_id=self.project.project_id,
            project_name=self.project.name,
            status=self.project.status.value,
        )

        # 메트릭 생성
        dashboard.metrics = self._generate_metrics(stats)

        # 타겟 진행 상황
        dashboard.target_progress = self._generate_target_progress()

        # 페르소나 통계
        dashboard.persona_stats = self._generate_persona_stats()

        # 일별 차트
        dashboard.daily_chart = self._generate_daily_chart(stats)

        # 최근 실행
        dashboard.recent_executions = self._generate_recent_executions()

        return dashboard

    def _generate_metrics(self, stats: ProjectStats) -> List[MetricCard]:
        """핵심 메트릭 생성"""
        metrics = []

        # 전체 진행률
        metrics.append(MetricCard(
            name="Overall Progress",
            value=f"{self.project.progress:.1f}",
            unit="%",
            description=f"{stats.completed_targets}/{stats.total_targets} targets completed"
        ))

        # 총 실행 수
        metrics.append(MetricCard(
            name="Total Executions",
            value=stats.total_executions,
            description=f"Success: {stats.successful_executions}, Failed: {stats.failed_executions}"
        ))

        # 성공률
        trend = TrendDirection.STABLE
        if stats.daily_stats and len(stats.daily_stats) >= 2:
            recent = stats.daily_stats[-1].success_rate
            prev = stats.daily_stats[-2].success_rate
            if recent > prev:
                trend = TrendDirection.UP
            elif recent < prev:
                trend = TrendDirection.DOWN

        metrics.append(MetricCard(
            name="Success Rate",
            value=f"{stats.success_rate:.1f}",
            unit="%",
            trend=trend
        ))

        # 평균 체류 시간
        metrics.append(MetricCard(
            name="Avg Dwell Time",
            value=f"{stats.avg_dwell_time:.0f}",
            unit="sec"
        ))

        # 오늘 실행
        metrics.append(MetricCard(
            name="Today's Progress",
            value=f"{self.project.today_executions}/{self.project.daily_quota}",
            description=f"{self.project.remaining_today} remaining"
        ))

        # 사용된 리소스
        metrics.append(MetricCard(
            name="Resources Used",
            value=f"{stats.total_personas_used}P / {stats.total_devices_used}D / {stats.total_ips_used}IP",
            description="Personas / Devices / IPs"
        ))

        # 활동 일수
        metrics.append(MetricCard(
            name="Active Days",
            value=stats.active_days,
            unit="days"
        ))

        # 평균 스크롤 깊이
        metrics.append(MetricCard(
            name="Avg Scroll Depth",
            value=f"{stats.avg_scroll_depth * 100:.0f}",
            unit="%"
        ))

        return metrics

    def _generate_target_progress(self) -> List[TargetProgress]:
        """타겟별 진행 상황"""
        progress_list = []

        for target in self.project.targets:
            status = "pending"
            if target.is_completed:
                status = "completed"
            elif target.total_clicks > 0:
                status = "in_progress"

            progress_list.append(TargetProgress(
                target_id=target.target_id,
                keyword=target.keyword,
                blog_title=target.blog_title,
                current=target.total_clicks,
                target=target.target_clicks,
                progress=target.progress,
                last_executed=target.last_executed_at.isoformat() if target.last_executed_at else None,
                status=status
            ))

        # 진행률 낮은 순 정렬
        progress_list.sort(key=lambda x: x.progress)

        return progress_list

    def _generate_persona_stats(self) -> List[PersonaStats]:
        """페르소나별 통계"""
        persona_data: Dict[str, Dict] = {}

        for record in self.project.execution_records:
            pid = record.persona_id
            if pid not in persona_data:
                persona_data[pid] = {
                    "executions": 0,
                    "successes": 0,
                    "total_dwell": 0,
                    "last_active": None
                }

            persona_data[pid]["executions"] += 1
            if record.success:
                persona_data[pid]["successes"] += 1
                persona_data[pid]["total_dwell"] += record.duration_sec

            if not persona_data[pid]["last_active"] or record.executed_at > datetime.fromisoformat(persona_data[pid]["last_active"]):
                persona_data[pid]["last_active"] = record.executed_at.isoformat()

        stats_list = []
        for pid, data in persona_data.items():
            success_rate = (data["successes"] / data["executions"] * 100) if data["executions"] > 0 else 0
            avg_dwell = (data["total_dwell"] / data["successes"]) if data["successes"] > 0 else 0

            stats_list.append(PersonaStats(
                persona_id=pid,
                executions=data["executions"],
                success_rate=success_rate,
                avg_dwell_time=avg_dwell,
                last_active=data["last_active"]
            ))

        # 실행 횟수 순 정렬
        stats_list.sort(key=lambda x: x.executions, reverse=True)

        return stats_list

    def _generate_daily_chart(self, stats: ProjectStats) -> List[Dict[str, Any]]:
        """일별 차트 데이터"""
        chart_data = []

        for daily in stats.daily_stats:
            chart_data.append({
                "date": daily.date.isoformat(),
                "executions": daily.total_executions,
                "successes": daily.successful_executions,
                "failures": daily.failed_executions,
                "success_rate": daily.success_rate,
                "avg_dwell_time": daily.avg_dwell_time,
                "unique_personas": daily.unique_personas,
                "unique_ips": daily.unique_ips,
            })

        return chart_data

    def _generate_recent_executions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 실행 기록"""
        recent = sorted(
            self.project.execution_records,
            key=lambda r: r.executed_at,
            reverse=True
        )[:limit]

        return [r.to_dict() for r in recent]


# ============================================================
# 멀티 프로젝트 대시보드
# ============================================================

@dataclass
class GlobalDashboardData:
    """전체 시스템 대시보드"""
    generated_at: datetime = field(default_factory=datetime.now)

    # 프로젝트 요약
    total_projects: int = 0
    active_projects: int = 0
    completed_projects: int = 0

    # 오늘 통계
    today_executions: int = 0
    today_successes: int = 0
    today_failures: int = 0

    # 리소스 현황
    active_personas: int = 0
    active_devices: int = 0
    active_ips: int = 0

    # 프로젝트별 요약
    project_summaries: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at.isoformat(),
            "total_projects": self.total_projects,
            "active_projects": self.active_projects,
            "completed_projects": self.completed_projects,
            "today_executions": self.today_executions,
            "today_successes": self.today_successes,
            "today_failures": self.today_failures,
            "today_success_rate": self.today_success_rate,
            "active_personas": self.active_personas,
            "active_devices": self.active_devices,
            "active_ips": self.active_ips,
            "project_summaries": self.project_summaries,
        }

    @property
    def today_success_rate(self) -> float:
        if self.today_executions == 0:
            return 0.0
        return (self.today_successes / self.today_executions) * 100

    def to_ascii(self) -> str:
        """ASCII 전광판"""
        lines = []
        width = 80

        lines.append("╔" + "═" * (width - 2) + "╗")
        lines.append("║" + "  🌐 NAVER AI EVOLUTION - GLOBAL DASHBOARD  ".center(width - 2) + "║")
        lines.append("║" + f"  Generated: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}  ".center(width - 2) + "║")
        lines.append("╠" + "═" * (width - 2) + "╣")

        # 프로젝트 현황
        lines.append("║" + "  📁 PROJECTS".ljust(width - 2) + "║")
        lines.append("║" + f"     Active: {self.active_projects}  |  Completed: {self.completed_projects}  |  Total: {self.total_projects}".ljust(width - 2) + "║")
        lines.append("╠" + "─" * (width - 2) + "╣")

        # 오늘 통계
        lines.append("║" + "  📊 TODAY'S STATS".ljust(width - 2) + "║")
        lines.append("║" + f"     Executions: {self.today_executions}  |  Success: {self.today_successes}  |  Rate: {self.today_success_rate:.1f}%".ljust(width - 2) + "║")
        lines.append("╠" + "─" * (width - 2) + "╣")

        # 리소스
        lines.append("║" + "  🔧 RESOURCES".ljust(width - 2) + "║")
        lines.append("║" + f"     Personas: {self.active_personas}  |  Devices: {self.active_devices}  |  IPs: {self.active_ips}".ljust(width - 2) + "║")
        lines.append("╠" + "─" * (width - 2) + "╣")

        # 프로젝트별 요약
        lines.append("║" + "  📋 PROJECT STATUS".ljust(width - 2) + "║")
        for ps in self.project_summaries[:5]:
            status_icon = {"active": "🟢", "paused": "🟡", "completed": "✅", "draft": "⚪"}
            icon = status_icon.get(ps.get("status", "draft"), "⚪")
            progress = ps.get("progress", 0)
            bar_len = int(progress / 100 * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            name = ps.get("name", "Unknown")[:25]
            line = f"     {icon} {name.ljust(25)} [{bar}] {progress:.0f}%"
            lines.append("║" + line.ljust(width - 2) + "║")

        lines.append("╚" + "═" * (width - 2) + "╝")

        return "\n".join(lines)


class GlobalDashboard:
    """전체 시스템 대시보드 생성기"""

    def __init__(self, projects: List[Project]):
        self.projects = projects

    def generate(self) -> GlobalDashboardData:
        """글로벌 대시보드 생성"""
        dashboard = GlobalDashboardData()

        today = date.today()
        personas = set()
        devices = set()
        ips = set()

        for project in self.projects:
            dashboard.total_projects += 1

            if project.status == ProjectStatus.ACTIVE:
                dashboard.active_projects += 1
            elif project.status == ProjectStatus.COMPLETED:
                dashboard.completed_projects += 1

            # 오늘 통계
            for record in project.execution_records:
                if record.executed_at.date() == today:
                    dashboard.today_executions += 1
                    if record.success:
                        dashboard.today_successes += 1
                    else:
                        dashboard.today_failures += 1

                    personas.add(record.persona_id)
                    if record.device_serial:
                        devices.add(record.device_serial)
                    if record.ip_address:
                        ips.add(record.ip_address)

            # 프로젝트 요약
            dashboard.project_summaries.append({
                "project_id": project.project_id,
                "name": project.name,
                "status": project.status.value,
                "progress": project.progress,
                "today_executions": project.today_executions,
                "remaining_today": project.remaining_today,
            })

        dashboard.active_personas = len(personas)
        dashboard.active_devices = len(devices)
        dashboard.active_ips = len(ips)

        # 진행률 순 정렬
        dashboard.project_summaries.sort(
            key=lambda x: (x["status"] != "active", -x["progress"])
        )

        return dashboard
