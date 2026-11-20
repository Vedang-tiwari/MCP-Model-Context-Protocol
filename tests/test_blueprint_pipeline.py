"""Unit tests for Autonomous Pipeline components (Blueprint §0 through §7)."""
import unittest
from datetime import datetime, timezone, timedelta
from core.models import JobListing, ApplicationStatus
from core.database import DatabaseManager
from core.profile_manager import ProfileManager
from core.scoring import JobFitScorer
from core.tailoring import ApplicationTailorer


class TestBlueprintPipeline(unittest.TestCase):
    def setUp(self):
        self.profile_mgr = ProfileManager()
        self.scorer = JobFitScorer(self.profile_mgr, shortlist_threshold=0.60)
        self.tailorer = ApplicationTailorer(self.profile_mgr)

    def test_hard_filters_company_blocklist(self):
        job = JobListing(
            id="test_blocked_comp",
            platform="indeed",
            title="Senior Python Engineer",
            company="Revature",  # In blocklist
            location="Remote",
            url="https://example.com/job1"
        )
        passed, rej = self.scorer.check_hard_filters(job)
        self.assertFalse(passed)
        self.assertIn("blocklist", rej)

    def test_hard_filters_keyword_blocklist(self):
        job = JobListing(
            id="test_blocked_kw",
            platform="indeed",
            title="AI Engineer",
            company="Acme Corp",
            location="Remote",
            url="https://example.com/job2",
            description="Great opportunity. This is an unpaid internship with high growth potential."
        )
        passed, rej = self.scorer.check_hard_filters(job)
        self.assertFalse(passed)
        self.assertIn("unpaid", rej)

    def test_5_factor_soft_fit_scoring(self):
        job = JobListing(
            id="test_match",
            platform="greenhouse",
            title="Senior Software Engineer - Python & FastAPI",
            company="Anthropic",
            location="Remote",
            url="https://example.com/job3",
            description="We are seeking an engineer skilled in Python, FastAPI, Docker, and PostgreSQL to build scalable systems."
        )
        score, reasons, flags = self.scorer.calculate_soft_score(job)
        self.assertGreaterEqual(score, 0.60)
        self.assertTrue(any("skill" in r.lower() or "tech" in r.lower() for r in reasons))

    def test_qa_bank_confidence_guardrail(self):
        # High confidence authorized question
        ans, conf = self.profile_mgr.query_qa_bank("Are you legally authorized to work in the United States?")
        self.assertEqual(ans, "Yes")
        self.assertEqual(conf, "high")

        # never_auto fields must NEVER return an automated answer
        ans_sal, conf_sal = self.profile_mgr.query_qa_bank("What is your expected CTC / desired salary?")
        self.assertIsNone(ans_sal)
        self.assertEqual(conf_sal, "never_auto")

        ans_crim, conf_crim = self.profile_mgr.query_qa_bank("Have you ever been convicted of a felony or criminal history?")
        self.assertIsNone(ans_crim)
        self.assertEqual(conf_crim, "never_auto")

    def test_tailoring_and_fabrication_audit(self):
        job = JobListing(
            id="test_tailor",
            platform="lever",
            title="Full Stack Engineer",
            company="Stripe",
            location="Remote",
            url="https://example.com/job4",
            description="Looking for an engineer experienced in Python, React, and Redis."
        )
        result = self.tailorer.tailor(job)
        self.assertTrue(result.audit_passed)
        self.assertEqual(len(result.audit_violations), 0)

        # Assert cover letter word count <= 200 words
        word_count = len(result.cover_letter.split())
        self.assertLessEqual(word_count, 200)

        # Assert fabrication audit fails if hallucinated claims are injected
        fake_profile = self.profile_mgr.get_profile_yaml()
        fake_resume_text = "Alex Mercer\nPhD in Computer Science from Stanford University\nTuring Award winner"
        passed, violations = self.tailorer.audit_tailored_resume(fake_resume_text, fake_profile)
        self.assertFalse(passed)
        self.assertGreater(len(violations), 0)


if __name__ == "__main__":
    unittest.main()
