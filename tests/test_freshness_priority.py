import unittest
from datetime import datetime, timezone, timedelta
import tempfile
import os

from core.models import JobListing, ApplicationStatus
from core.database import DatabaseManager
from core.scoring import JobFitScorer
from core.profile_manager import ProfileManager


class TestFreshnessPriority(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_fresh.db")
        self.db = DatabaseManager(self.db_path)
        self.profile_mgr = ProfileManager()
        self.scorer = JobFitScorer(self.profile_mgr)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_job_listing_freshness_properties(self):
        now = datetime.now(timezone.utc)
        
        # Fresh job: 2 hours ago
        fresh_job = JobListing(
            id="job_fresh",
            platform="sprout",
            title="Senior AI Engineer",
            company="Tech Corp",
            url="https://example.com/fresh",
            posted_at=now - timedelta(hours=2)
        )
        self.assertTrue(fresh_job.is_fresh_24h)
        self.assertAlmostEqual(fresh_job.age_hours, 2.0, delta=0.1)
        self.assertIn("2h ago", fresh_job.age_display)

        # Non-fresh job: 28 hours ago (> 24 hours)
        older_job = JobListing(
            id="job_older",
            platform="linkedin",
            title="Senior Python Developer",
            company="Legacy Corp",
            url="https://example.com/older",
            posted_at=now - timedelta(hours=28)
        )
        self.assertFalse(older_job.is_fresh_24h)
        self.assertAlmostEqual(older_job.age_hours, 28.0, delta=0.1)
        self.assertIn("Yesterday", older_job.age_display)

        # Very fresh: 20 minutes ago
        ultra_fresh = JobListing(
            id="job_ultra",
            platform="hirist",
            title="Backend Architect",
            company="Fast Track",
            url="https://example.com/ultra",
            posted_at=now - timedelta(minutes=20)
        )
        self.assertTrue(ultra_fresh.is_fresh_24h)
        self.assertIn("m ago", ultra_fresh.age_display)

    def test_database_prioritizes_fresh_jobs_on_first_place(self):
        now = datetime.now(timezone.utc)
        
        # 1. Old job (posted 5 days ago) with high match score (95)
        old_job = JobListing(
            id="old_95",
            platform="ats_direct",
            title="Senior Staff Engineer",
            company="Giant Tech",
            url="https://example.com/old",
            posted_at=now - timedelta(days=5),
            discovered_at=now - timedelta(days=5),
            match_score=95
        )
        self.db.insert_job(old_job)

        # 2. Fresh job (posted 2 hours ago) with lower match score (75)
        fresh_job = JobListing(
            id="fresh_75",
            platform="sprout",
            title="AI Systems Engineer",
            company="Sprout Partner",
            url="https://example.com/fresh",
            posted_at=now - timedelta(hours=2),
            discovered_at=now - timedelta(hours=2),
            match_score=75
        )
        self.db.insert_job(fresh_job)

        # 3. Another fresh job (posted 6 hours ago) with 85 match score
        fresh_job_2 = JobListing(
            id="fresh_85",
            platform="hirist",
            title="Lead ML Engineer",
            company="Hirist Tech",
            url="https://example.com/fresh2",
            posted_at=now - timedelta(hours=6),
            discovered_at=now - timedelta(hours=6),
            match_score=85
        )
        self.db.insert_job(fresh_job_2)

        # Default list_jobs prioritizes fresh jobs (<= 24h) in first place!
        jobs = self.db.list_jobs(limit=10, prioritize_fresh=True)
        self.assertEqual(len(jobs), 3)

        # Fresh jobs must come before older jobs
        self.assertEqual(jobs[0].id, "fresh_85")  # Fresh (6h) with score 85
        self.assertEqual(jobs[1].id, "fresh_75")  # Fresh (2h) with score 75
        self.assertEqual(jobs[2].id, "old_95")    # Older (5d) follows after fresh jobs

        # Test fresh_only filter: only jobs <= 24 hours
        fresh_only = self.db.list_jobs(fresh_only=True)
        self.assertEqual(len(fresh_only), 2)
        self.assertEqual([j.id for j in fresh_only], ["fresh_85", "fresh_75"])

        # Test get_stats returns fresh_jobs_count = 2
        stats = self.db.get_stats()
        self.assertEqual(stats["fresh_jobs_count"], 2)
        self.assertEqual(stats["total_discovered"], 3)

    def test_scoring_freshness_factor(self):
        now = datetime.now(timezone.utc)
        
        fresh_job = JobListing(
            id="fresh_eval",
            platform="ats_direct",
            title="Senior Python Engineer",
            company="TechNova",
            description="Looking for Senior Python, FastAPI, Docker, and Kubernetes engineer.",
            url="https://example.com/fresh_eval",
            posted_at=now - timedelta(hours=5)
        )
        score_fresh, reasons_fresh, _ = self.scorer.calculate_soft_score(fresh_job)
        self.assertTrue(any("Fresh posting" in r or "Ultra-fresh" in r for r in reasons_fresh))

        older_job = JobListing(
            id="older_eval",
            platform="ats_direct",
            title="Senior Python Engineer",
            company="TechNova",
            description="Looking for Senior Python, FastAPI, Docker, and Kubernetes engineer.",
            url="https://example.com/older_eval",
            posted_at=now - timedelta(days=4)
        )
        score_older, reasons_older, _ = self.scorer.calculate_soft_score(older_job)
        self.assertFalse(any("Fresh posting" in r or "Ultra-fresh" in r for r in reasons_older))
        self.assertGreater(score_fresh, score_older)

    def test_api_freshness_endpoint_and_filtering(self):
        from starlette.testclient import TestClient
        from web.server import app, db as web_db
        
        now = datetime.now(timezone.utc)
        j_fresh = JobListing(
            id="test_api_fresh_1",
            platform="sprout",
            title="Senior GenAI Engineer",
            company="Sprout Partner Corp",
            url="https://usesprout.com/jobs/1",
            posted_at=now - timedelta(hours=3),
            match_score=80
        )
        j_stale = JobListing(
            id="test_api_stale_1",
            platform="sprout",
            title="Senior GenAI Engineer",
            company="Sprout Partner Corp",
            url="https://usesprout.com/jobs/2",
            posted_at=now - timedelta(hours=40),
            match_score=90
        )
        web_db.insert_job(j_fresh)
        web_db.insert_job(j_stale)
        try:
            client = TestClient(app)
            
            # 1. GET /api/jobs with default sort (fresh_first)
            resp = client.get("/api/jobs?platform=sprout")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            jobs = data["jobs"]
            self.assertGreaterEqual(len(jobs), 2)
            
            # The fresh job must be in first place before the stale job, despite lower match score
            found_fresh_idx = next(i for i, j in enumerate(jobs) if j["id"] == "test_api_fresh_1")
            found_stale_idx = next(i for i, j in enumerate(jobs) if j["id"] == "test_api_stale_1")
            self.assertLess(found_fresh_idx, found_stale_idx)
            self.assertTrue(jobs[found_fresh_idx]["is_fresh"])
            self.assertFalse(jobs[found_stale_idx]["is_fresh"])
            self.assertIn("h ago", jobs[found_fresh_idx]["age_display"])

            # 2. GET /api/jobs?fresh_only=true
            resp_fresh_only = client.get("/api/jobs?platform=sprout&fresh_only=true")
            self.assertEqual(resp_fresh_only.status_code, 200)
            fresh_only_data = resp_fresh_only.json()
            for j in fresh_only_data["jobs"]:
                self.assertTrue(j["is_fresh"])
            self.assertTrue(any(j["id"] == "test_api_fresh_1" for j in fresh_only_data["jobs"]))
            self.assertFalse(any(j["id"] == "test_api_stale_1" for j in fresh_only_data["jobs"]))

            # 3. GET /api/stats returns fresh_jobs_count
            resp_stats = client.get("/api/stats")
            self.assertEqual(resp_stats.status_code, 200)
            stats_data = resp_stats.json()
            self.assertIn("fresh_jobs_count", stats_data)
            self.assertGreaterEqual(stats_data["fresh_jobs_count"], 1)

        finally:
            web_db.delete_job("test_api_fresh_1")
            web_db.delete_job("test_api_stale_1")


if __name__ == "__main__":
    unittest.main()
