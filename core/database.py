import sqlite3
import json
import os
from contextlib import contextmanager
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from .models import JobListing, ApplicationRecord, ApplicationStatus


class DatabaseManager:
    def __init__(self, db_path: str = "data/mcp_jobs.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                url TEXT NOT NULL,
                apply_url TEXT,
                is_easy_apply INTEGER DEFAULT 0,
                description TEXT,
                posted_at TEXT,
                discovered_at TEXT NOT NULL,
                match_score INTEGER,
                match_reasons TEXT,
                status TEXT NOT NULL,
                metadata TEXT
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                status TEXT NOT NULL,
                applied_at TEXT,
                attempts INTEGER DEFAULT 0,
                answers_submitted TEXT,
                error_message TEXT,
                screenshot_path TEXT,
                notes TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs (id)
            )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_discovered_at ON jobs(discovered_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_platform ON jobs(platform)")
            conn.commit()

    def is_job_seen(self, job_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,))
            return cursor.fetchone() is not None

    def insert_job(self, job: JobListing) -> bool:
        if self.is_job_seen(job.id):
            return False

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO jobs (
                id, platform, title, company, location, url, apply_url,
                is_easy_apply, description, posted_at, discovered_at,
                match_score, match_reasons, status, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id,
                job.platform,
                job.title,
                job.company,
                job.location,
                job.url,
                job.apply_url,
                1 if job.is_easy_apply else 0,
                job.description or "",
                job.posted_at.isoformat() if job.posted_at else None,
                job.discovered_at.isoformat(),
                job.match_score,
                json.dumps(job.match_reasons or []),
                job.status.value,
                json.dumps(job.metadata or {})
            ))
            conn.commit()
            return True

    def get_job(self, job_id: str) -> Optional[JobListing]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE id = ? OR id LIKE ? LIMIT 1", (job_id, f"{job_id}%"))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_job(row)

    def update_job_status(
        self,
        job_id: str,
        status: ApplicationStatus,
        match_score: Optional[int] = None,
        match_reasons: Optional[List[str]] = None
    ):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            updates = ["status = ?"]
            params = [status.value]

            if match_score is not None:
                updates.append("match_score = ?")
                params.append(match_score)

            if match_reasons is not None:
                updates.append("match_reasons = ?")
                params.append(json.dumps(match_reasons))

            params.append(job_id)
            query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()

    def list_jobs(
        self,
        status: Optional[ApplicationStatus] = None,
        platform: Optional[str] = None,
        limit: int = 50,
        min_match_score: Optional[int] = None
    ) -> List[JobListing]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            conditions = []
            params = []

            if status:
                conditions.append("status = ?")
                params.append(status.value)
            if platform:
                conditions.append("platform = ?")
                params.append(platform)
            if min_match_score is not None:
                conditions.append("match_score >= ?")
                params.append(min_match_score)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            query = f"SELECT * FROM jobs {where_clause} ORDER BY discovered_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_job(row) for row in rows]

    def record_application(self, record: ApplicationRecord) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO applications (
                job_id, status, applied_at, attempts,
                answers_submitted, error_message, screenshot_path, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.job_id,
                record.status.value,
                record.applied_at.isoformat() if record.applied_at else None,
                record.attempts,
                json.dumps(record.answers_submitted or {}),
                record.error_message,
                record.screenshot_path,
                record.notes
            ))
            conn.commit()
            return cursor.lastrowid

    def get_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) as count FROM jobs GROUP BY status")
            job_counts = {row["status"]: row["count"] for row in cursor.fetchall()}

            cursor.execute("SELECT platform, COUNT(*) as count FROM jobs GROUP BY platform")
            platform_counts = {row["platform"]: row["count"] for row in cursor.fetchall()}

            cursor.execute("SELECT COUNT(*) as total FROM applications WHERE status = 'APPLIED'")
            total_applied = cursor.fetchone()["total"]

            return {
                "total_discovered": sum(job_counts.values()),
                "status_breakdown": job_counts,
                "platform_breakdown": platform_counts,
                "total_applied": total_applied
            }

    def _row_to_job(self, row: sqlite3.Row) -> JobListing:
        posted_at = datetime.fromisoformat(row["posted_at"]) if row["posted_at"] else None
        discovered_at = datetime.fromisoformat(row["discovered_at"]) if row["discovered_at"] else datetime.now(timezone.utc)
        match_reasons = json.loads(row["match_reasons"]) if row["match_reasons"] else []
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}

        return JobListing(
            id=row["id"],
            platform=row["platform"],
            title=row["title"],
            company=row["company"],
            location=row["location"] or "Remote",
            url=row["url"],
            apply_url=row["apply_url"],
            is_easy_apply=bool(row["is_easy_apply"]),
            description=row["description"],
            posted_at=posted_at,
            discovered_at=discovered_at,
            match_score=row["match_score"],
            match_reasons=match_reasons,
            status=ApplicationStatus(row["status"]),
            metadata=metadata
        )
