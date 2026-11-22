"""Unit tests for the Refresh New Unseen Jobs Engine."""
import unittest
import tempfile
import os
from datetime import datetime, timezone, timedelta
from starlette.testclient import TestClient

from core.models import JobListing, ApplicationStatus
from core.database import DatabaseManager
from web.server import app, db as web_db


class TestRefreshUnseenJobs(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_unseen.db")
        self.db = DatabaseManager(self.db_path)
        self.client = TestClient(app)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_database_exclude_ids_and_count_unseen(self):
        now = datetime.now(timezone.utc)
        # Insert 5 test jobs
        for i in range(1, 6):
            job = JobListing(
                id=f"unseen_job_{i}",
                platform="sprout",
                title=f"AI Engineer {i}",
                company=f"Company {i}",
                url=f"https://example.com/job_{i}",
                posted_at=now - timedelta(hours=i),
                match_score=80 + i
            )
            self.db.insert_job(job)

        # 1. Total count matching
        self.assertEqual(self.db.count_jobs(), 5)

        # 2. Exclude seen jobs (unseen_job_1, unseen_job_2)
        seen = ["unseen_job_1", "unseen_job_2"]
        unseen_count = self.db.count_jobs(exclude_ids=seen)
        self.assertEqual(unseen_count, 3)

        # 3. List jobs excluding seen
        unseen_jobs = self.db.list_jobs(exclude_ids=seen, limit=10)
        self.assertEqual(len(unseen_jobs), 3)
        self.assertNotIn("unseen_job_1", [j.id for j in unseen_jobs])
        self.assertNotIn("unseen_job_2", [j.id for j in unseen_jobs])
        self.assertEqual([j.id for j in unseen_jobs], ["unseen_job_5", "unseen_job_4", "unseen_job_3"])

    def test_api_refresh_endpoint_returns_unseen_jobs(self):
        now = datetime.now(timezone.utc)
        test_ids = [f"test_refresh_job_{i}" for i in range(1, 6)]
        for i, jid in enumerate(test_ids, 1):
            j = JobListing(
                id=jid,
                platform="sprout",
                title=f"Staff AI Engineer {i}",
                company=f"Anthropic Ecosystem {i}",
                url=f"https://example.com/ref_{i}",
                posted_at=now - timedelta(hours=i),
                match_score=70 + i
            )
            web_db.insert_job(j)

        try:
            # First request: get 2 jobs
            resp1 = self.client.post("/api/jobs/refresh", json={
                "exclude_ids": [],
                "limit": 2,
                "platform": "sprout"
            })
            self.assertEqual(resp1.status_code, 200)
            data1 = resp1.json()
            self.assertEqual(data1["count"], 2)
            first_seen_ids = [j["id"] for j in data1["jobs"]]

            # Second request: click "Refresh" passing first_seen_ids to get NEW unseen jobs
            resp2 = self.client.post("/api/jobs/refresh", json={
                "exclude_ids": first_seen_ids,
                "limit": 2,
                "platform": "sprout"
            })
            self.assertEqual(resp2.status_code, 200)
            data2 = resp2.json()
            second_seen_ids = [j["id"] for j in data2["jobs"]]

            # Verify that none of the second batch were in the first batch
            for jid in second_seen_ids:
                self.assertNotIn(jid, first_seen_ids)

            # Check that total_unseen_remaining was reported
            self.assertIn("total_unseen_remaining", data2)
            self.assertIn("has_more", data2)

        finally:
            for jid in test_ids:
                web_db.delete_job(jid)


if __name__ == "__main__":
    unittest.main()
