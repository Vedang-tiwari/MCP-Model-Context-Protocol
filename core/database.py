import sqlite3
import json
import os
from contextlib import contextmanager
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from .models import JobListing, ApplicationRecord, ApplicationStatus


class DatabaseManager:
    def __init__(self, db_path: str = "data/mcp_jobs.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            try:
                conn.execute("PRAGMA journal_mode=WAL")
            except Exception:
                pass
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
                salary TEXT,
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

            # Ensure salary and rejection_reason columns exist if upgrading database
            try:
                cursor.execute("ALTER TABLE jobs ADD COLUMN salary TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE jobs ADD COLUMN rejection_reason TEXT")
            except sqlite3.OperationalError:
                pass

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS state_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                from_state TEXT,
                to_state TEXT NOT NULL,
                actor TEXT NOT NULL DEFAULT 'agent',
                timestamp TEXT NOT NULL,
                evidence TEXT,
                notes TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs (id)
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
                salary, is_easy_apply, description, posted_at, discovered_at,
                match_score, match_reasons, status, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.id,
                job.platform,
                job.title,
                job.company,
                job.location,
                job.url,
                job.apply_url,
                job.salary,
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
        match_reasons: Optional[List[str]] = None,
        actor: str = "agent",
        evidence: Optional[str] = None,
        notes: Optional[str] = None,
        rejection_reason: Optional[str] = None
    ):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Fetch current status for transition audit log
            cursor.execute("SELECT status FROM jobs WHERE id = ?", (job_id,))
            prev_row = cursor.fetchone()
            from_state = prev_row["status"] if prev_row else None

            updates = ["status = ?"]
            params = [status.value]

            if match_score is not None:
                updates.append("match_score = ?")
                params.append(match_score)

            if match_reasons is not None:
                updates.append("match_reasons = ?")
                params.append(json.dumps(match_reasons))

            if rejection_reason is not None:
                updates.append("rejection_reason = ?")
                params.append(rejection_reason)

            params.append(job_id)
            query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)

            # Record state transition into state_history
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
            INSERT INTO state_history (
                job_id, from_state, to_state, actor, timestamp, evidence, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                from_state,
                status.value,
                actor,
                now_iso,
                evidence,
                notes or rejection_reason
            ))

            conn.commit()

    def update_job_metadata(self, job_id: str, metadata_updates: Dict[str, Any]):
        """Merge updates into a job's JSON metadata column."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT metadata FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            current_meta = json.loads(row["metadata"]) if (row and row["metadata"]) else {}
            current_meta.update(metadata_updates)
            cursor.execute("UPDATE jobs SET metadata = ? WHERE id = ?", (json.dumps(current_meta), job_id))
            conn.commit()

    def get_state_history(self, job_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM state_history WHERE job_id = ? ORDER BY id ASC",
                (job_id,)
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def list_jobs(
        self,
        status: Optional[ApplicationStatus] = None,
        platform: Optional[str] = None,
        limit: int = 50,
        min_match_score: Optional[int] = None,
        fresh_only: bool = False,
        prioritize_fresh: bool = True
    ) -> List[JobListing]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            conditions = []
            params = []
            cutoff_24h_iso = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

            if status:
                conditions.append("status = ?")
                params.append(status.value)
            if platform:
                clean_p = platform.lower().strip()
                if clean_p in ["greenhouse", "lever", "ashby"]:
                    conditions.append("(LOWER(platform) = ? OR (LOWER(platform) = 'ats_direct' AND metadata LIKE ?))")
                    params.extend([clean_p, f"%{clean_p}%"])
                elif clean_p in ["ats_direct", "direct_ats", "ats"]:
                    conditions.append("LOWER(platform) IN ('ats_direct', 'greenhouse', 'lever', 'ashby')")
                elif clean_p in ["ai-job.net", "aijobnet"]:
                    conditions.append("LOWER(platform) IN ('ai-job.net', 'aijobnet')")
                elif clean_p in ["beep", "beep_ai"]:
                    conditions.append("LOWER(platform) IN ('beep', 'beep_ai')")
                elif clean_p in ["mljobsinfo", "ml-jobs.info"]:
                    conditions.append("LOWER(platform) IN ('mljobsinfo', 'ml-jobs.info')")
                elif clean_p in ["aijobsai", "aijobs.ai"]:
                    conditions.append("LOWER(platform) IN ('aijobsai', 'aijobs.ai')")
                else:
                    conditions.append("LOWER(platform) = ?")
                    params.append(clean_p)
            if min_match_score is not None:
                conditions.append("match_score >= ?")
                params.append(min_match_score)
            if fresh_only:
                conditions.append("COALESCE(posted_at, discovered_at) >= ?")
                params.append(cutoff_24h_iso)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            if prioritize_fresh:
                query = f"""
                SELECT *,
                       CASE WHEN COALESCE(posted_at, discovered_at) >= ? THEN 1 ELSE 0 END as _is_fresh_tier
                FROM jobs
                {where_clause}
                ORDER BY
                    _is_fresh_tier DESC,
                    match_score DESC,
                    COALESCE(posted_at, discovered_at) DESC
                LIMIT ?
                """
                exec_params = [cutoff_24h_iso] + params + [limit]
            else:
                query = f"SELECT * FROM jobs {where_clause} ORDER BY discovered_at DESC LIMIT ?"
                exec_params = params + [limit]

            cursor.execute(query, exec_params)
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

    def delete_job(self, job_id: str) -> bool:
        """Permanently delete a single job and its associated application & history records."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM applications WHERE job_id = ?", (job_id,))
            cursor.execute("DELETE FROM state_history WHERE job_id = ?", (job_id,))
            cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            conn.commit()
            return cursor.rowcount > 0

    def purge_ghost_jobs(
        self,
        hard_delete: bool = True,
        dry_run: bool = False,
        purge_stale: bool = True,
        detector: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Scans existing database records, detects ghost / fake / stale / evergreen requisitions,
        and either permanently purges them (hard_delete=True) or marks them EXPIRED / FILTERED_OUT.
        """
        from .ghost_job_detector import GhostJobDetector
        detector = detector or GhostJobDetector()

        all_jobs = self.list_jobs(limit=50000)

        ghost_ids_to_purge = []
        breakdown = {
            "dummy_companies": 0,
            "placeholder_urls": 0,
            "evergreen_or_pipeline": 0,
            "stale_postings": 0,
            "total_ghosts": 0
        }

        for job in all_jobs:
            # Skip applied / submitted / interview / offer unless it's an outright dummy seed employer or malformed URL
            is_active_candidate_flow = job.status in (
                ApplicationStatus.APPLIED,
                ApplicationStatus.SUBMITTED,
                ApplicationStatus.INTERVIEW,
                ApplicationStatus.RESPONSE_RECEIVED
            )

            verdict = detector.evaluate(job)
            if not verdict.is_ghost:
                continue

            # Check primary reason category
            is_dummy = any("dummy/seed" in r for r in verdict.reasons)
            is_bad_url = any("URL" in r or "slug" in r for r in verdict.reasons)
            is_evergreen = any("evergreen" in r or "talent pool" in r or "pipeline" in r for r in verdict.reasons)
            is_stale = any("Stale" in r for r in verdict.reasons)

            # If user wants to keep stale postings, skip stale-only ghost reasons
            if not purge_stale and is_stale and not (is_dummy or is_bad_url or is_evergreen):
                continue

            # Don't delete real applied applications if it was just stale
            if is_active_candidate_flow and not (is_dummy or is_bad_url):
                continue

            if is_dummy:
                breakdown["dummy_companies"] += 1
            elif is_bad_url:
                breakdown["placeholder_urls"] += 1
            elif is_evergreen:
                breakdown["evergreen_or_pipeline"] += 1
            elif is_stale:
                breakdown["stale_postings"] += 1

            ghost_ids_to_purge.append((job.id, verdict.reasons))

        breakdown["total_ghosts"] = len(ghost_ids_to_purge)

        if not dry_run and ghost_ids_to_purge:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                chunk_size = 500
                ids_only = [item[0] for item in ghost_ids_to_purge]
                for i in range(0, len(ids_only), chunk_size):
                    chunk = ids_only[i:i + chunk_size]
                    placeholders = ",".join("?" for _ in chunk)
                    if hard_delete:
                        cursor.execute(f"DELETE FROM applications WHERE job_id IN ({placeholders})", chunk)
                        cursor.execute(f"DELETE FROM state_history WHERE job_id IN ({placeholders})", chunk)
                        cursor.execute(f"DELETE FROM jobs WHERE id IN ({placeholders})", chunk)
                    else:
                        cursor.execute(
                            f"UPDATE jobs SET status = ?, rejection_reason = ? WHERE id IN ({placeholders})",
                            [ApplicationStatus.EXPIRED.value, "Purged: Ghost or stale requisition", *chunk]
                        )
                conn.commit()

        return {
            "total_scanned": len(all_jobs),
            "ghost_jobs_found": len(ghost_ids_to_purge),
            "purged_count": len(ghost_ids_to_purge) if not dry_run else 0,
            "dry_run": dry_run,
            "hard_delete": hard_delete,
            "breakdown": breakdown
        }

    def get_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) as count FROM jobs GROUP BY status")
            job_counts = {row["status"]: row["count"] for row in cursor.fetchall()}

            cursor.execute("SELECT platform, COUNT(*) as count FROM jobs GROUP BY platform")
            platform_counts = {row["platform"]: row["count"] for row in cursor.fetchall()}

            cursor.execute("SELECT COUNT(*) as total FROM applications WHERE status = 'APPLIED'")
            total_applied = cursor.fetchone()["total"]

            cutoff_24h_iso = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            cursor.execute(
                "SELECT COUNT(*) as fresh_count FROM jobs WHERE COALESCE(posted_at, discovered_at) >= ?",
                (cutoff_24h_iso,)
            )
            fresh_count = cursor.fetchone()["fresh_count"]

            return {
                "total_discovered": sum(job_counts.values()),
                "fresh_jobs_count": fresh_count,
                "status_breakdown": job_counts,
                "platform_breakdown": platform_counts,
                "total_applied": total_applied
            }

    def _row_to_job(self, row: sqlite3.Row) -> JobListing:
        posted_at = datetime.fromisoformat(row["posted_at"]) if row["posted_at"] else None
        discovered_at = datetime.fromisoformat(row["discovered_at"]) if row["discovered_at"] else datetime.now(timezone.utc)
        match_reasons = json.loads(row["match_reasons"]) if row["match_reasons"] else []
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}

        # Resolve salary from column or metadata
        salary = None
        if "salary" in row.keys() and row["salary"]:
            salary = str(row["salary"])
        elif metadata.get("salary"):
            salary = str(metadata["salary"])
        elif metadata.get("compensation"):
            salary = str(metadata["compensation"])
        elif metadata.get("package"):
            salary = str(metadata["package"])
        elif metadata.get("salary_min") and metadata.get("salary_max"):
            salary = f"${metadata['salary_min']:,} - ${metadata['salary_max']:,} / yr"

        return JobListing(
            id=row["id"],
            platform=row["platform"],
            title=row["title"],
            company=row["company"],
            location=row["location"] or "Remote",
            url=row["url"],
            apply_url=row["apply_url"],
            salary=salary,
            is_easy_apply=bool(row["is_easy_apply"]),
            description=row["description"],
            posted_at=posted_at,
            discovered_at=discovered_at,
            match_score=row["match_score"],
            match_reasons=match_reasons,
            status=ApplicationStatus(row["status"]),
            metadata=metadata
        )
