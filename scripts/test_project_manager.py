#!/usr/bin/env python3
"""
Project Manager 테스트 스크립트

Usage:
    python scripts/test_project_manager.py
    python scripts/test_project_manager.py --dashboard
    python scripts/test_project_manager.py --import missions.csv
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.shared.project_manager import (
    ProjectManager,
    Project,
    ProjectStatus,
    ProjectDashboard,
)
from src.shared.project_manager.dashboard import GlobalDashboard


def test_create_project():
    """프로젝트 생성 테스트"""
    print("\n" + "=" * 60)
    print("1. Project Creation Test")
    print("=" * 60)

    pm = ProjectManager(db_path="data/test_projects.db")

    # 프로젝트 생성
    project = pm.create_project(
        name="서울맛집 캠페인",
        description="서울 맛집 블로그 인게이지먼트 캠페인",
        targets=[
            {"keyword": "강남맛집", "title": "강남 숨은 맛집 베스트10", "url": "https://blog.naver.com/xxx/111"},
            {"keyword": "홍대맛집", "title": "홍대 데이트 코스 추천", "url": "https://blog.naver.com/yyy/222"},
            {"keyword": "이태원맛집", "title": "이태원 브런치 카페", "url": "https://blog.naver.com/zzz/333"},
            {"keyword": "명동맛집", "title": "명동 점심 맛집", "target_clicks": 15},
            {"keyword": "잠실맛집", "title": "잠실 저녁 맛집", "target_clicks": 20},
        ],
        daily_quota=10,
        duration_days=7
    )

    print(f"  Created project: {project.project_id}")
    print(f"  Name: {project.name}")
    print(f"  Targets: {len(project.targets)}")
    print(f"  Daily quota: {project.daily_quota}")

    # 페르소나/디바이스 할당
    project.assign_persona("persona_01")
    project.assign_persona("persona_02")
    project.assign_persona("persona_03")
    project.assign_device("R3CT3001XXX")

    pm.update_project(project)

    print(f"  Assigned personas: {project.assigned_personas}")
    print(f"  Assigned devices: {project.assigned_devices}")

    return project


def test_execution_recording(pm: ProjectManager, project: Project):
    """실행 기록 테스트"""
    print("\n" + "=" * 60)
    print("2. Execution Recording Test")
    print("=" * 60)

    # 프로젝트 시작
    pm.start_project(project.project_id)
    print(f"  Project started: {project.status.value}")

    # 시뮬레이션: 여러 날에 걸친 실행
    personas = ["persona_01", "persona_02", "persona_03"]
    ips = ["121.134.xxx.1", "121.134.xxx.2", "175.xxx.xxx.3"]

    for target in project.targets[:3]:
        for i in range(random.randint(3, 7)):
            persona = random.choice(personas)
            ip = random.choice(ips)
            success = random.random() > 0.2  # 80% 성공률

            pm.record_execution(
                project_id=project.project_id,
                target_id=target.target_id,
                persona_id=persona,
                success=success,
                duration_sec=random.randint(60, 180) if success else 0,
                scroll_depth=random.uniform(0.6, 0.95) if success else 0,
                interactions=random.randint(2, 5) if success else 0,
                device_serial="R3CT3001XXX",
                ip_address=ip,
                ip_provider="residential"
            )

    # 새로고침
    project = pm.get_project(project.project_id)

    print(f"  Total executions: {len(project.execution_records)}")
    print(f"  Project progress: {project.progress:.1f}%")

    for target in project.targets:
        print(f"    - {target.keyword}: {target.total_clicks}/{target.target_clicks} ({target.progress:.0f}%)")

    return project


def test_dashboard(pm: ProjectManager, project: Project):
    """대시보드 테스트"""
    print("\n" + "=" * 60)
    print("3. Dashboard Test")
    print("=" * 60)

    dashboard = ProjectDashboard(project)
    data = dashboard.generate()

    # ASCII 대시보드 출력
    print(data.to_ascii())

    # JSON 데이터 샘플
    print("\n  Dashboard JSON keys:")
    for key in data.to_dict().keys():
        print(f"    - {key}")


def test_global_dashboard(pm: ProjectManager):
    """글로벌 대시보드 테스트"""
    print("\n" + "=" * 60)
    print("4. Global Dashboard Test")
    print("=" * 60)

    projects = pm.list_projects()
    global_dash = GlobalDashboard(projects)
    data = global_dash.generate()

    print(data.to_ascii())


def test_stats(pm: ProjectManager, project: Project):
    """통계 테스트"""
    print("\n" + "=" * 60)
    print("5. Statistics Test")
    print("=" * 60)

    stats = pm.get_project_stats(project.project_id)

    print(f"  Total executions: {stats.total_executions}")
    print(f"  Success rate: {stats.success_rate:.1f}%")
    print(f"  Avg dwell time: {stats.avg_dwell_time:.0f}s")
    print(f"  Avg scroll depth: {stats.avg_scroll_depth * 100:.0f}%")
    print(f"  Personas used: {stats.total_personas_used}")
    print(f"  IPs used: {stats.total_ips_used}")
    print(f"  Active days: {stats.active_days}")

    # 일별 통계
    if stats.daily_stats:
        print("\n  Daily breakdown:")
        for daily in stats.daily_stats[-3:]:
            print(f"    {daily.date}: {daily.total_executions} exec, {daily.success_rate:.0f}% success")


def test_csv_import():
    """CSV 임포트 테스트"""
    print("\n" + "=" * 60)
    print("6. CSV Import Test")
    print("=" * 60)

    # 샘플 CSV 생성
    csv_content = """# keyword,blog_title,url
서울맛집,강남역 맛집 추천 베스트10,https://blog.naver.com/test1/111
홍대맛집,홍대 데이트 코스 맛집,https://blog.naver.com/test2/222
이태원맛집,이태원 브런치 카페,https://blog.naver.com/test3/333
강남카페,강남역 카공 카페,https://blog.naver.com/test4/444
"""

    csv_path = Path("data/sample_missions.csv")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(csv_content, encoding='utf-8')

    pm = ProjectManager(db_path="data/test_projects.db")
    project = pm.import_from_csv(str(csv_path), "CSV Import 테스트")

    print(f"  Imported project: {project.project_id}")
    print(f"  Targets: {len(project.targets)}")
    for t in project.targets:
        print(f"    - {t.keyword}: {t.blog_title}")


def main():
    parser = argparse.ArgumentParser(description="Project Manager Test")
    parser.add_argument("--dashboard", action="store_true", help="Show dashboard only")
    parser.add_argument("--import", dest="import_csv", help="Import from CSV")

    args = parser.parse_args()

    pm = ProjectManager(db_path="data/test_projects.db")

    if args.import_csv:
        project = pm.import_from_csv(args.import_csv, Path(args.import_csv).stem)
        print(f"Imported: {project.project_id} - {project.name}")
        return

    if args.dashboard:
        projects = pm.list_projects()
        if projects:
            for p in projects:
                dashboard = ProjectDashboard(p)
                print(dashboard.generate().to_ascii())
        else:
            print("No projects found")
        return

    # 전체 테스트
    print("=" * 60)
    print("  PROJECT MANAGER TEST SUITE")
    print("=" * 60)

    project = test_create_project()
    project = test_execution_recording(pm, project)
    test_dashboard(pm, project)
    test_stats(pm, project)
    test_csv_import()
    test_global_dashboard(pm)

    print("\n" + "=" * 60)
    print("  ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
