"""
Project Manager Module

프로젝트 기반 캠페인 관리 시스템:
- 프로젝트별 미션 관리
- 디바이스/페르소나 할당
- 실행 통계 및 전광판
- 일별/주별 리포트

Usage:
    from src.shared.project_manager import ProjectManager, Project

    pm = ProjectManager()

    # 프로젝트 생성
    project = pm.create_project(
        name="서울맛집 캠페인",
        targets=[
            {"keyword": "서울맛집", "title": "강남 숨은 맛집", "url": "..."},
            {"keyword": "홍대맛집", "title": "홍대 데이트 코스", "url": "..."},
        ],
        daily_quota=10,
        duration_days=7
    )

    # 미션 실행
    result = await pm.execute_next_mission(project.project_id)

    # 전광판 데이터
    dashboard = pm.get_dashboard(project.project_id)
"""

from .schema import (
    Project,
    ProjectStatus,
    ProjectTarget,
    ProjectStats,
    ExecutionRecord,
    DailyStats,
)
from .manager import ProjectManager
from .dashboard import DashboardData, ProjectDashboard

__all__ = [
    "Project",
    "ProjectStatus",
    "ProjectTarget",
    "ProjectStats",
    "ExecutionRecord",
    "DailyStats",
    "ProjectManager",
    "DashboardData",
    "ProjectDashboard",
]

__version__ = "0.1.0"
