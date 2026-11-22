"""Unit tests for the Anti-Ghosting Requisition and Dead Job Detection Engine."""
import unittest
import os
import shutil
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from core.models import JobListing, ApplicationStatus, ApplicationRecord
from core.database import DatabaseManager
from core.ghost_job_detector import GhostJobDetector, DEAD_POSTING_PATTERNS


class TestGhostJobDetector(unittest.TestCase):
    def setUp(self):
        self.detector = GhostJobDetector(max_age_days=14, ats_max_age_days=30)
        self.test_db_path = "data/test_ghost_jobs.db"
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        self.db = DatabaseManager(self.test_db_path)

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_known_dummy_seed_companies_rejected(self):
        """Seed dummy companies historically used as fallbacks must be rejected immediately."""
        dummy_jobs = [
            JobListing(
                id="dummy-1",
                platform="sprout",
                title="Founding AI Engineer",
                company="Sprout Verified Partner",
                url="https://usesprout.com/jobs/ai-eng-101"
            ),
            JobListing(
                id="dummy-2",
                platform="hirist",
                title="Senior Backend Engineer",
                company="FinFlow Technologies",
                url="https://www.hirist.tech/j/backend-eng-102"
            ),
            JobListing(
                id="dummy-3",
                platform="beepai",
                title="Generative AI Specialist",
                company="Beep Intelligence Lab",
                url="https://beep.work/jobs/genai-103"
            )
        ]
        for job in dummy_jobs:
            verdict = self.detector.evaluate(job)
            self.assertTrue(verdict.is_ghost)
            self.assertEqual(verdict.risk_score, 1.0)
            self.assertTrue(any("dummy/seed" in r for r in verdict.reasons))

    def test_anonymous_and_stealth_staffing_rejected(self):
        """Anonymous, stealth, or undisclosed staffing harvesters must be flagged as ghost postings."""
        job = JobListing(
            id="anon-1",
            platform="indeed",
            title="Full Stack Software Engineer",
            company="Confidential Client",
            url="https://indeed.com/viewjob?jk=12345"
        )
        verdict = self.detector.evaluate(job)
        self.assertTrue(verdict.is_ghost)
        self.assertTrue(any("harvester" in r for r in verdict.reasons))

    def test_evergreen_and_talent_pool_rejected(self):
        """Evergreen postings and talent pools without active requisitions must be rejected."""
        evergreen_titles = [
            "Software Engineer - Talent Community",
            "Future Opportunities: Machine Learning Engineer",
            "General Application (Open Pipeline)",
            "Expression of Interest: Senior Fullstack Developer"
        ]
        for idx, title in enumerate(evergreen_titles):
            job = JobListing(
                id=f"evergreen-{idx}",
                platform="greenhouse",
                title=title,
                company="Acme Corp",
                url=f"https://boards.greenhouse.io/acme/jobs/{1000 + idx}"
            )
            verdict = self.detector.evaluate(job)
            self.assertTrue(verdict.is_ghost, f"Failed for title: {title}")
            self.assertTrue(any("evergreen" in r or "talent pool" in r for r in verdict.reasons))

    def test_malformed_and_generic_urls_rejected(self):
        """Generic career URLs lacking requisition IDs or placeholder slugs must be rejected."""
        bad_url_job = JobListing(
            id="bad-url-1",
            platform="ats_direct",
            title="Software Engineer",
            company="Stripe",
            url="https://lever.co/stripe/job"
        )
        verdict = self.detector.evaluate(bad_url_job)
        self.assertTrue(verdict.is_ghost)
        self.assertTrue(any("Malformed" in r or "Generic" in r for r in verdict.reasons))

        homepage_url_job = JobListing(
            id="bad-url-2",
            platform="company",
            title="Frontend Engineer",
            company="Acme",
            url="https://acme.com/careers"
        )
        verdict2 = self.detector.evaluate(homepage_url_job)
        self.assertTrue(verdict2.is_ghost)
        self.assertTrue(any("Generic career board URL" in r for r in verdict2.reasons))

    def test_stale_posting_age_rejected(self):
        """Postings older than the maximum freshness window must be rejected as stale."""
        now = datetime.now(timezone.utc)

        # Aggregator job older than 14 days
        stale_aggregator_job = JobListing(
            id="stale-1",
            platform="linkedin",
            title="Staff Python Engineer",
            company="Tech Corp",
            url="https://linkedin.com/jobs/view/999888",
            posted_at=now - timedelta(days=20)
        )
        verdict = self.detector.evaluate(stale_aggregator_job)
        self.assertTrue(verdict.is_ghost)
        self.assertTrue(any("Stale requisition" in r for r in verdict.reasons))

        # Fresh direct ATS job (e.g. 5 days old) should pass
        fresh_ats_job = JobListing(
            id="fresh-1",
            platform="ats_direct",
            title="Forward Deployed Engineer",
            company="Palantir Partner",
            url="https://boards.greenhouse.io/palantir/jobs/555123",
            posted_at=now - timedelta(days=5)
        )
        verdict_fresh = self.detector.evaluate(fresh_ats_job)
        self.assertFalse(verdict_fresh.is_ghost)

    def test_dead_posting_regex_patterns(self):
        """Dead requisition text patterns must correctly match closed ATS portal messages."""
        import re
        sample_messages = [
            "We are sorry, this job is no longer available.",
            "This position has been filled. Thank you for your interest.",
            "This posting has expired.",
            "The company is no longer accepting applications for this role.",
            "404 - Page Not Found"
        ]
        for msg in sample_messages:
            matched = any(re.search(pat, msg.lower()) for pat in DEAD_POSTING_PATTERNS)
            self.assertTrue(matched, f"Pattern failed to match: '{msg}'")

    def test_database_purge_ghost_jobs(self):
        """DatabaseManager.purge_ghost_jobs must correctly identify and delete ghost jobs."""
        now = datetime.now(timezone.utc)
        
        # Insert 1 valid job
        valid_job = JobListing(
            id="valid-1",
            platform="ats_direct",
            title="AI Systems Engineer",
            company="Anthropic Ecosystem",
            url="https://boards.greenhouse.io/anthropic/jobs/444321",
            posted_at=now - timedelta(days=2)
        )
        self.db.insert_job(valid_job)

        # Insert 1 dummy seed employer job
        dummy_job = JobListing(
            id="dummy-seed-1",
            platform="sprout",
            title="Staff AI Engineer",
            company="Sprout Verified Partner",
            url="https://usesprout.com/jobs/seed-123",
            posted_at=now - timedelta(days=1)
        )
        self.db.insert_job(dummy_job)

        # Insert 1 stale job (posted 45 days ago)
        stale_job = JobListing(
            id="stale-old-1",
            platform="linkedin",
            title="Software Developer",
            company="Global Tech",
            url="https://linkedin.com/jobs/view/123456",
            posted_at=now - timedelta(days=45)
        )
        self.db.insert_job(stale_job)

        # 1. Test dry run
        dry_summary = self.db.purge_ghost_jobs(hard_delete=True, dry_run=True)
        self.assertEqual(dry_summary["total_scanned"], 3)
        self.assertEqual(dry_summary["ghost_jobs_found"], 2)
        self.assertEqual(dry_summary["purged_count"], 0)
        self.assertEqual(len(self.db.list_jobs(limit=10)), 3)

        # 2. Test actual purge
        purge_summary = self.db.purge_ghost_jobs(hard_delete=True, dry_run=False)
        self.assertEqual(purge_summary["purged_count"], 2)
        remaining = self.db.list_jobs(limit=10)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].id, "valid-1")


if __name__ == "__main__":
    unittest.main()
