"""
Project Manager

프로젝트 CRUD 및 실행 관리
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, date
import uuid

from .schema import (
    Project,
    ProjectStatus,
    ProjectTarget,
    ProjectStats,
    ExecutionRecord,
)

logger = logging.getLogger(__name__)


class ProjectManager:
    """프로젝트 관리자"""

    def __init__(self, db_path: str = "data/projects.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # 메모리 캐시
        self._projects: Dict[str, Project] = {}
        self._load_all_projects()

    def _init_db(self) -> None:
        """데이터베이스 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'draft',
                    config_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS targets (
                    target_id TEXT PRIMARY KEY,
                    project_id TEXT,
                    keyword TEXT,
                    blog_title TEXT,
                    url TEXT,
                    target_clicks INTEGER DEFAULT 10,
                    total_clicks INTEGER DEFAULT 0,
                    total_dwell_time INTEGER DEFAULT 0,
                    avg_scroll_depth REAL DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    fail_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_executed_at TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                );

                CREATE TABLE IF NOT EXISTS execution_records (
                    record_id TEXT PRIMARY KEY,
                    project_id TEXT,
                    target_id TEXT,
                    persona_id TEXT,
                    device_serial TEXT,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    duration_sec INTEGER DEFAULT 0,
                    scroll_depth REAL DEFAULT 0,
                    interactions INTEGER DEFAULT 0,
                    success INTEGER DEFAULT 0,
                    error_message TEXT,
                    ip_address TEXT,
                    ip_provider TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(project_id),
                    FOREIGN KEY (target_id) REFERENCES targets(target_id)
                );

                CREATE INDEX IF NOT EXISTS idx_records_project ON execution_records(project_id);
                CREATE INDEX IF NOT EXISTS idx_records_date ON execution_records(executed_at);
                CREATE INDEX IF NOT EXISTS idx_targets_project ON targets(project_id);
            """)

    def _load_all_projects(self) -> None:
        """모든 프로젝트 로드"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # 프로젝트 로드
            for row in conn.execute("SELECT * FROM projects"):
                project = self._row_to_project(conn, row)
                self._projects[project.project_id] = project

    def _row_to_project(self, conn: sqlite3.Connection, row: sqlite3.Row) -> Project:
        """DB 행을 Project로 변환"""
        config = json.loads(row["config_json"] or "{}")

        project = Project(
            project_id=row["project_id"],
            name=row["name"],
            description=row["description"] or "",
            status=ProjectStatus(row["status"]),
            daily_quota=config.get("daily_quota", 10),
            duration_days=config.get("duration_days", 7),
            cooldown_minutes=config.get("cooldown_minutes", 30),
            ip_rotation=config.get("ip_rotation", True),
            require_korea_ip=config.get("require_korea_ip", True),
            assigned_personas=config.get("assigned_personas", []),
            assigned_devices=config.get("assigned_devices", []),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        )

        # 타겟 로드
        for target_row in conn.execute(
            "SELECT * FROM targets WHERE project_id = ?",
            (project.project_id,)
        ):
            target = ProjectTarget(
                target_id=target_row["target_id"],
                keyword=target_row["keyword"],
                blog_title=target_row["blog_title"],
                url=target_row["url"],
                target_clicks=target_row["target_clicks"],
                total_clicks=target_row["total_clicks"],
                total_dwell_time=target_row["total_dwell_time"],
                avg_scroll_depth=target_row["avg_scroll_depth"],
                success_count=target_row["success_count"],
                fail_count=target_row["fail_count"],
                last_executed_at=datetime.fromisoformat(target_row["last_executed_at"]) if target_row["last_executed_at"] else None,
            )
            project.targets.append(target)

        # 실행 기록 로드 (최근 100개만)
        for record_row in conn.execute(
            """SELECT * FROM execution_records
               WHERE project_id = ?
               ORDER BY executed_at DESC LIMIT 100""",
            (project.project_id,)
        ):
            record = ExecutionRecord(
                record_id=record_row["record_id"],
                project_id=record_row["project_id"],
                target_id=record_row["target_id"],
                persona_id=record_row["persona_id"],
                device_serial=record_row["device_serial"],
                executed_at=datetime.fromisoformat(record_row["executed_at"]),
                duration_sec=record_row["duration_sec"],
                scroll_depth=record_row["scroll_depth"],
                interactions=record_row["interactions"],
                success=bool(record_row["success"]),
                error_message=record_row["error_message"],
                ip_address=record_row["ip_address"],
                ip_provider=record_row["ip_provider"],
            )
            project.execution_records.append(record)

        return project

    # ==================== CRUD ====================

    def create_project(
        self,
        name: str,
        targets: List[Dict[str, Any]] = None,
        description: str = "",
        daily_quota: int = 10,
        duration_days: int = 7,
        **kwargs
    ) -> Project:
        """프로젝트 생성"""
        project_id = str(uuid.uuid4())[:8]

        project = Project(
            project_id=project_id,
            name=name,
            description=description,
            daily_quota=daily_quota,
            duration_days=duration_days,
            cooldown_minutes=kwargs.get("cooldown_minutes", 30),
            ip_rotation=kwargs.get("ip_rotation", True),
            require_korea_ip=kwargs.get("require_korea_ip", True),
        )

        # 타겟 추가
        if targets:
            project.add_targets_from_list(targets)

        # DB 저장
        self._save_project(project)
        self._projects[project.project_id] = project

        logger.info(f"Project created: {project.project_id} - {name}")
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        """프로젝트 조회"""
        return self._projects.get(project_id)

    def list_projects(
        self,
        status: Optional[ProjectStatus] = None,
        limit: int = 50
    ) -> List[Project]:
        """프로젝트 목록 조회"""
        projects = list(self._projects.values())

        if status:
            projects = [p for p in projects if p.status == status]

        # 최신순 정렬
        projects.sort(key=lambda p: p.created_at, reverse=True)

        return projects[:limit]

    def update_project(self, project: Project) -> None:
        """프로젝트 업데이트"""
        self._save_project(project)
        self._projects[project.project_id] = project

    def delete_project(self, project_id: str) -> bool:
        """프로젝트 삭제"""
        if project_id not in self._projects:
            return False

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM execution_records WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM targets WHERE project_id = ?", (project_id,))
            conn.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))

        del self._projects[project_id]
        logger.info(f"Project deleted: {project_id}")
        return True

    def _save_project(self, project: Project) -> None:
        """프로젝트 DB 저장"""
        config = {
            "daily_quota": project.daily_quota,
            "duration_days": project.duration_days,
            "cooldown_minutes": project.cooldown_minutes,
            "ip_rotation": project.ip_rotation,
            "require_korea_ip": project.require_korea_ip,
            "assigned_personas": project.assigned_personas,
            "assigned_devices": project.assigned_devices,
        }

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO projects
                (project_id, name, description, status, config_json, created_at, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project.project_id,
                project.name,
                project.description,
                project.status.value,
                json.dumps(config),
                project.created_at.isoformat(),
                project.started_at.isoformat() if project.started_at else None,
                project.completed_at.isoformat() if project.completed_at else None,
            ))

            # 타겟 저장
            for target in project.targets:
                conn.execute("""
                    INSERT OR REPLACE INTO targets
                    (target_id, project_id, keyword, blog_title, url, target_clicks,
                     total_clicks, total_dwell_time, avg_scroll_depth, success_count, fail_count,
                     created_at, last_executed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    target.target_id,
                    project.project_id,
                    target.keyword,
                    target.blog_title,
                    target.url,
                    target.target_clicks,
                    target.total_clicks,
                    target.total_dwell_time,
                    target.avg_scroll_depth,
                    target.success_count,
                    target.fail_count,
                    target.created_at.isoformat(),
                    target.last_executed_at.isoformat() if target.last_executed_at else None,
                ))

    # ==================== 실행 관리 ====================

    def start_project(self, project_id: str) -> Optional[Project]:
        """프로젝트 시작"""
        project = self.get_project(project_id)
        if not project:
            return None

        project.start()
        self._save_project(project)

        logger.info(f"Project started: {project_id}")
        return project

    def pause_project(self, project_id: str) -> Optional[Project]:
        """프로젝트 일시 정지"""
        project = self.get_project(project_id)
        if not project:
            return None

        project.pause()
        self._save_project(project)

        logger.info(f"Project paused: {project_id}")
        return project

    def complete_project(self, project_id: str) -> Optional[Project]:
        """프로젝트 완료"""
        project = self.get_project(project_id)
        if not project:
            return None

        project.complete()
        self._save_project(project)

        logger.info(f"Project completed: {project_id}")
        return project

    def record_execution(
        self,
        project_id: str,
        target_id: str,
        persona_id: str,
        success: bool,
        duration_sec: int = 0,
        scroll_depth: float = 0.0,
        interactions: int = 0,
        device_serial: Optional[str] = None,
        ip_address: Optional[str] = None,
        ip_provider: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Optional[ExecutionRecord]:
        """실행 기록"""
        project = self.get_project(project_id)
        if not project:
            return None

        record = project.record_execution(
            target_id=target_id,
            persona_id=persona_id,
            success=success,
            duration_sec=duration_sec,
            scroll_depth=scroll_depth,
            interactions=interactions,
            device_serial=device_serial,
            ip_address=ip_address,
            ip_provider=ip_provider,
            error_message=error_message
        )

        # DB 저장
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO execution_records
                (record_id, project_id, target_id, persona_id, device_serial,
                 executed_at, duration_sec, scroll_depth, interactions,
                 success, error_message, ip_address, ip_provider)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.record_id,
                record.project_id,
                record.target_id,
                record.persona_id,
                record.device_serial,
                record.executed_at.isoformat(),
                record.duration_sec,
                record.scroll_depth,
                record.interactions,
                1 if record.success else 0,
                record.error_message,
                record.ip_address,
                record.ip_provider,
            ))

        # 타겟 업데이트
        self._save_project(project)

        # 프로젝트 완료 확인
        if project.is_completed:
            self.complete_project(project_id)

        return record

    # ==================== 통계 ====================

    def get_project_stats(self, project_id: str) -> Optional[ProjectStats]:
        """프로젝트 통계"""
        project = self.get_project(project_id)
        if not project:
            return None
        return project.get_stats()

    def get_today_summary(self) -> Dict[str, Any]:
        """오늘 전체 요약"""
        today = date.today()
        summary = {
            "date": today.isoformat(),
            "active_projects": 0,
            "total_executions": 0,
            "successful_executions": 0,
            "unique_personas": set(),
            "unique_devices": set(),
            "unique_ips": set(),
        }

        for project in self._projects.values():
            if project.status == ProjectStatus.ACTIVE:
                summary["active_projects"] += 1

            for record in project.execution_records:
                if record.executed_at.date() == today:
                    summary["total_executions"] += 1
                    if record.success:
                        summary["successful_executions"] += 1
                    summary["unique_personas"].add(record.persona_id)
                    if record.device_serial:
                        summary["unique_devices"].add(record.device_serial)
                    if record.ip_address:
                        summary["unique_ips"].add(record.ip_address)

        summary["unique_personas"] = len(summary["unique_personas"])
        summary["unique_devices"] = len(summary["unique_devices"])
        summary["unique_ips"] = len(summary["unique_ips"])

        return summary

    # ==================== 유틸리티 ====================

    def import_from_csv(self, csv_path: str, project_name: str) -> Project:
        """CSV에서 프로젝트 임포트"""
        targets = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if i == 0 and "keyword" in line.lower():
                    continue

                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    targets.append({
                        "keyword": parts[0],
                        "title": parts[1],
                        "url": parts[2] if len(parts) > 2 else None,
                    })

        return self.create_project(
            name=project_name,
            targets=targets,
            description=f"Imported from {csv_path}"
        )

    def export_to_json(self, project_id: str, output_path: str) -> bool:
        """프로젝트 JSON 내보내기"""
        project = self.get_project(project_id)
        if not project:
            return False

        data = {
            "project": project.to_dict(),
            "stats": project.get_stats().to_dict(),
            "execution_records": [r.to_dict() for r in project.execution_records],
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True
