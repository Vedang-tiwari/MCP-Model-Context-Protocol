"""Unit tests for targeted job platform discovery sweeps.
Verifies:
1. Targeted discovery sweeps execute strictly for the selected platform.
2. Related tech/engineering jobs on that platform are ingested and retained.
3. API /api/scout with platform parameter runs targeted cycle.
4. Database filtering by platform handles aliases and case-insensitivity.
"""
import sys
import os
import asyncio
import unittest

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from starlette.testclient import TestClient

from core.database import DatabaseManager
from core.profile_manager import ProfileManager
from discovery.aggregator import JobAggregator
from core.models import JobListing, ApplicationStatus
from web.server import app


class TestTargetedPlatformScout(unittest.TestCase):
    def setUp(self):
        self.db = DatabaseManager()
        self.profile_mgr = ProfileManager()
        self.aggregator = JobAggregator(self.db, self.profile_mgr)
        self.client = TestClient(app)

    def test_targeted_discovery_sprout(self):
        summary = asyncio.run(self.aggregator.run_discovery_cycle(
            roles=["Software Engineer", "AI Engineer", "Full Stack Engineer"],
            platform="sprout",
            max_age_hours=24
        ))
        self.assertEqual(summary["target_platform"], "sprout")
        # Only sprout provider should have executed
        self.assertIn("sprout", summary["executed_providers"])
        self.assertNotIn("linkedin", summary["executed_providers"])
        self.assertNotIn("indeed", summary["executed_providers"])
        self.assertGreaterEqual(summary["total_fetched"], 1)

        # Check that sprout jobs exist in DB
        sprout_jobs = self.db.list_jobs(platform="sprout", limit=20)
        self.assertGreaterEqual(len(sprout_jobs), 1)
        for job in sprout_jobs:
            self.assertEqual(job.platform, "sprout")

    def test_targeted_discovery_hirist(self):
        summary = asyncio.run(self.aggregator.run_discovery_cycle(
            roles=["Software Engineer", "AI Engineer"],
            platform="hirist",
            max_age_hours=24
        ))
        self.assertEqual(summary["target_platform"], "hirist")
        self.assertIn("hirist", summary["executed_providers"])
        self.assertNotIn("linkedin", summary["executed_providers"])
        self.assertGreaterEqual(summary["total_fetched"], 1)

        hirist_jobs = self.db.list_jobs(platform="hirist", limit=20)
        self.assertGreaterEqual(len(hirist_jobs), 1)

    def test_targeted_discovery_ats_direct(self):
        # Override with 1 company to keep test blazing fast
        ats_provider = self.aggregator.providers.get("ats_direct")
        orig_companies = ats_provider.companies
        ats_provider.companies = ["stripe"]
        try:
            summary = asyncio.run(self.aggregator.run_discovery_cycle(
                roles=["Software Engineer", "AI Engineer"],
                platform="ats_direct",
                max_age_hours=24
            ))
            self.assertEqual(summary["target_platform"], "ats_direct")
            self.assertTrue(any("ats_direct" in p for p in summary["executed_providers"]))
            self.assertNotIn("linkedin", summary["executed_providers"])
        finally:
            ats_provider.companies = orig_companies

    def test_api_scout_with_platform(self):
        resp = self.client.post("/api/scout", json={
            "platform": "devfolio",
            "roles": ["Full Stack Engineer", "Software Engineer"]
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["selected_platform"], "devfolio")
        self.assertIn("summary", data)
        self.assertEqual(data["summary"]["target_platform"], "devfolio")

    def test_database_platform_filtering_aliases(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        job1 = JobListing(
            id=f"job_alias_sprout_{int(now.timestamp())}",
            platform="sprout",
            title="Senior AI Platform Engineer",
            company="Sprout Partner",
            location="Remote",
            url="https://usesprout.com/jobs/senior-ai",
            discovered_at=now,
            status=ApplicationStatus.DISCOVERED
        )
        job2 = JobListing(
            id=f"job_alias_ats_{int(now.timestamp())}",
            platform="ats_direct",
            title="Senior Infrastructure Engineer",
            company="Stripe",
            location="Remote",
            url="https://lever.co/stripe/job",
            discovered_at=now,
            status=ApplicationStatus.DISCOVERED,
            metadata={"ats_type": "lever"}
        )
        self.db.insert_job(job1)
        self.db.insert_job(job2)

        # Test case-insensitive matching
        sprout_res = self.db.list_jobs(platform="Sprout", limit=100)
        self.assertTrue(any(j.id == job1.id for j in sprout_res))

        # Test ats_direct alias matching
        lever_res = self.db.list_jobs(platform="lever", limit=100)
        self.assertTrue(any(j.id == job2.id for j in lever_res))


if __name__ == "__main__":
    unittest.main()
