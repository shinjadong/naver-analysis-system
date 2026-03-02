"""
PersonaStore - SQLite 기반 페르소나 저장소

Author: Naver AI Evolution System
Created: 2025-12-15
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from .persona import Persona, BehaviorProfile, PersonaStatus

logger = logging.getLogger("naver_evolution.persona_store")


class PersonaStore:
    """
    SQLite 기반 페르소나 저장소

    사용 예시:
        store = PersonaStore("data/personas.db")

        # 새 페르소나 생성
        persona = store.create_persona("직장인_30대_남성", tags=["tech"])

        # 페르소나 선택
        persona = store.select_persona(strategy="least_recent")

        # 업데이트
        store.update(persona)
    """

    def __init__(self, db_path: str = "data/personas.db"):
        """
        Args:
            db_path: SQLite DB 파일 경로
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._round_robin_index = 0

    def _init_db(self):
        """데이터베이스 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 페르소나 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS personas (
                    persona_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    android_id TEXT NOT NULL UNIQUE,
                    advertising_id TEXT,
                    chrome_data_path TEXT,
                    nnb_cookie TEXT,
                    behavior_profile TEXT,
                    status TEXT DEFAULT 'active',
                    last_active TEXT,
                    cooldown_until TEXT,
                    total_sessions INTEGER DEFAULT 0,
                    total_pageviews INTEGER DEFAULT 0,
                    total_dwell_time INTEGER DEFAULT 0,
                    created_at TEXT,
                    tags TEXT,
                    notes TEXT,
                    data_json TEXT
                )
            """)

            # 방문 기록 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS visit_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    persona_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    domain TEXT,
                    content_type TEXT,
                    timestamp TEXT,
                    dwell_time INTEGER DEFAULT 0,
                    scroll_depth REAL DEFAULT 0.0,
                    actions TEXT,
                    FOREIGN KEY (persona_id) REFERENCES personas(persona_id)
                )
            """)

            # 인덱스
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_personas_status ON personas(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_personas_last_active ON personas(last_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_visit_persona ON visit_history(persona_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_visit_timestamp ON visit_history(timestamp)")

            conn.commit()

        logger.info(f"PersonaStore initialized: {self.db_path}")

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def create_persona(
        self,
        name: str,
        tags: List[str] = None,
        behavior_profile: BehaviorProfile = None
    ) -> Persona:
        """
        새 페르소나 생성

        Args:
            name: 페르소나 이름
            tags: 태그 목록
            behavior_profile: 행동 프로필 (None이면 랜덤 생성)

        Returns:
            생성된 Persona
        """
        persona = Persona.create_new(
            name=name,
            tags=tags,
            behavior_profile=behavior_profile
        )

        self._save(persona)
        logger.info(f"Created persona: {persona.name} ({persona.persona_id[:8]}...)")

        return persona

    def _save(self, persona: Persona):
        """페르소나 저장 (내부용)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            data = persona.to_dict()

            cursor.execute("""
                INSERT OR REPLACE INTO personas (
                    persona_id, name, android_id, advertising_id,
                    chrome_data_path, nnb_cookie, behavior_profile,
                    status, last_active, cooldown_until,
                    total_sessions, total_pageviews, total_dwell_time,
                    created_at, tags, notes, data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                persona.persona_id,
                persona.name,
                persona.android_id,
                persona.advertising_id,
                persona.chrome_data_path,
                persona.nnb_cookie,
                json.dumps(data.get("behavior_profile", {})),
                persona.status.value,
                data.get("last_active"),
                data.get("cooldown_until"),
                persona.total_sessions,
                persona.total_pageviews,
                persona.total_dwell_time,
                data.get("created_at"),
                json.dumps(persona.tags),
                persona.notes,
                json.dumps(data)
            ))

            conn.commit()

    def update(self, persona: Persona):
        """페르소나 업데이트"""
        self._save(persona)
        logger.debug(f"Updated persona: {persona.persona_id[:8]}...")

    def get(self, persona_id: str) -> Optional[Persona]:
        """ID로 페르소나 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT data_json FROM personas WHERE persona_id = ?",
                (persona_id,)
            )
            row = cursor.fetchone()

            if row:
                data = json.loads(row[0])
                return Persona.from_dict(data)

        return None

    def get_by_android_id(self, android_id: str) -> Optional[Persona]:
        """ANDROID_ID로 페르소나 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT data_json FROM personas WHERE android_id = ?",
                (android_id,)
            )
            row = cursor.fetchone()

            if row:
                data = json.loads(row[0])
                return Persona.from_dict(data)

        return None

    def get_all(self, include_retired: bool = False) -> List[Persona]:
        """모든 페르소나 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if include_retired:
                cursor.execute("SELECT data_json FROM personas")
            else:
                cursor.execute(
                    "SELECT data_json FROM personas WHERE status != ?",
                    (PersonaStatus.RETIRED.value,)
                )

            rows = cursor.fetchall()

            return [Persona.from_dict(json.loads(row[0])) for row in rows]

    def delete(self, persona_id: str) -> bool:
        """페르소나 삭제"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM visit_history WHERE persona_id = ?",
                (persona_id,)
            )
            cursor.execute(
                "DELETE FROM personas WHERE persona_id = ?",
                (persona_id,)
            )

            conn.commit()

            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted persona: {persona_id[:8]}...")

            return deleted

    def retire(self, persona_id: str) -> bool:
        """페르소나 은퇴 (소프트 삭제)"""
        persona = self.get(persona_id)
        if persona:
            persona.status = PersonaStatus.RETIRED
            self.update(persona)
            logger.info(f"Retired persona: {persona_id[:8]}...")
            return True
        return False

    # =========================================================================
    # Selection Strategies
    # =========================================================================

    def select_persona(self, strategy: str = "least_recent") -> Optional[Persona]:
        """
        페르소나 선택 전략

        Args:
            strategy:
                - least_recent: 가장 오래 활동 안 한 페르소나
                - round_robin: 순차 선택
                - random: 랜덤 선택
                - needs_revisit: 재방문이 필요한 페르소나
                - lowest_sessions: 세션 수가 가장 적은 페르소나

        Returns:
            선택된 Persona (없으면 None)
        """
        available = self._get_available_personas()

        if not available:
            logger.warning("No available personas")
            return None

        if strategy == "least_recent":
            return self._select_least_recent(available)
        elif strategy == "round_robin":
            return self._select_round_robin(available)
        elif strategy == "random":
            return self._select_random(available)
        elif strategy == "needs_revisit":
            return self._select_needs_revisit(available)
        elif strategy == "lowest_sessions":
            return self._select_lowest_sessions(available)
        else:
            logger.warning(f"Unknown strategy: {strategy}, using least_recent")
            return self._select_least_recent(available)

    def _get_available_personas(self) -> List[Persona]:
        """사용 가능한 페르소나 목록"""
        now = datetime.now()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # ACTIVE 상태이거나, COOLING_DOWN이지만 쿨다운이 끝난 페르소나
            cursor.execute("""
                SELECT data_json FROM personas
                WHERE status = 'active'
                   OR (status = 'cooling' AND (cooldown_until IS NULL OR cooldown_until <= ?))
            """, (now.isoformat(),))

            rows = cursor.fetchall()

            personas = []
            for row in rows:
                persona = Persona.from_dict(json.loads(row[0]))

                # 쿨다운 상태 갱신
                if persona.status == PersonaStatus.COOLING_DOWN:
                    if not persona.cooldown_until or persona.cooldown_until <= now:
                        persona.finish_cooldown()
                        self.update(persona)

                if persona.is_available:
                    personas.append(persona)

            return personas

    def _select_least_recent(self, personas: List[Persona]) -> Optional[Persona]:
        """가장 오래 활동 안 한 페르소나 선택"""
        if not personas:
            return None

        return min(personas, key=lambda p: p.last_active)

    def _select_round_robin(self, personas: List[Persona]) -> Optional[Persona]:
        """순차 선택"""
        if not personas:
            return None

        # 인덱스 순환
        self._round_robin_index = self._round_robin_index % len(personas)
        persona = personas[self._round_robin_index]
        self._round_robin_index += 1

        return persona

    def _select_random(self, personas: List[Persona]) -> Optional[Persona]:
        """랜덤 선택"""
        import random

        if not personas:
            return None

        return random.choice(personas)

    def _select_needs_revisit(self, personas: List[Persona]) -> Optional[Persona]:
        """
        재방문이 필요한 페르소나 선택

        기준: 마지막 방문 후 1~7일 경과한 페르소나 우선
        (너무 짧으면 의심스럽고, 너무 길면 재방문 효과 없음)
        """
        if not personas:
            return None

        now = datetime.now()
        ideal_gap_min = timedelta(days=1)
        ideal_gap_max = timedelta(days=7)

        # 이상적인 재방문 기간에 있는 페르소나
        ideal = [
            p for p in personas
            if ideal_gap_min <= (now - p.last_active) <= ideal_gap_max
        ]

        if ideal:
            # 이상적인 범위 중 가장 오래된 것
            return min(ideal, key=lambda p: p.last_active)

        # 없으면 그냥 가장 오래된 것
        return self._select_least_recent(personas)

    def _select_lowest_sessions(self, personas: List[Persona]) -> Optional[Persona]:
        """세션 수가 가장 적은 페르소나 선택"""
        if not personas:
            return None

        return min(personas, key=lambda p: p.total_sessions)

    # =========================================================================
    # Visit History
    # =========================================================================

    def add_visit_record(self, persona_id: str, url: str, domain: str = "",
                         content_type: str = "unknown", dwell_time: int = 0,
                         scroll_depth: float = 0.0, actions: List[str] = None):
        """방문 기록 추가"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO visit_history
                (persona_id, url, domain, content_type, timestamp, dwell_time, scroll_depth, actions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                persona_id,
                url,
                domain,
                content_type,
                datetime.now().isoformat(),
                dwell_time,
                scroll_depth,
                json.dumps(actions or [])
            ))

            conn.commit()

    def get_visit_history(self, persona_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """방문 기록 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT url, domain, content_type, timestamp, dwell_time, scroll_depth, actions
                FROM visit_history
                WHERE persona_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (persona_id, limit))

            rows = cursor.fetchall()

            return [
                {
                    "url": row[0],
                    "domain": row[1],
                    "content_type": row[2],
                    "timestamp": row[3],
                    "dwell_time": row[4],
                    "scroll_depth": row[5],
                    "actions": json.loads(row[6]) if row[6] else []
                }
                for row in rows
            ]

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """전체 통계"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 페르소나 수
            cursor.execute("SELECT COUNT(*) FROM personas")
            total_personas = cursor.fetchone()[0]

            # 상태별 수
            cursor.execute("""
                SELECT status, COUNT(*) FROM personas GROUP BY status
            """)
            status_counts = dict(cursor.fetchall())

            # 총 세션/페이지뷰
            cursor.execute("""
                SELECT SUM(total_sessions), SUM(total_pageviews), SUM(total_dwell_time)
                FROM personas
            """)
            row = cursor.fetchone()
            total_sessions = row[0] or 0
            total_pageviews = row[1] or 0
            total_dwell_time = row[2] or 0

            # 오늘 활동한 페르소나 수
            today = datetime.now().date().isoformat()
            cursor.execute("""
                SELECT COUNT(*) FROM personas WHERE last_active LIKE ?
            """, (f"{today}%",))
            active_today = cursor.fetchone()[0]

            return {
                "total_personas": total_personas,
                "status_counts": status_counts,
                "total_sessions": total_sessions,
                "total_pageviews": total_pageviews,
                "total_dwell_time_hours": total_dwell_time / 3600,
                "active_today": active_today,
            }

    def count(self, status: PersonaStatus = None) -> int:
        """페르소나 수"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if status:
                cursor.execute(
                    "SELECT COUNT(*) FROM personas WHERE status = ?",
                    (status.value,)
                )
            else:
                cursor.execute("SELECT COUNT(*) FROM personas")

            return cursor.fetchone()[0]
