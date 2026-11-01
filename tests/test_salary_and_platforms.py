"""Tests for salary normalization engine and multi-platform coverage."""
import sys
import os
import unittest
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.salary_parser import normalize_salary, extract_salary_from_text
from core.models import JobListing, ApplicationStatus, JobPlatform
from core.database import DatabaseManager
from discovery.registry import PlatformRegistry


class TestSalaryAndPlatforms(unittest.TestCase):
    def setUp(self):
        self.test_db_path = "data/test_salary.db"
        self.db = DatabaseManager(self.test_db_path)

    def tearDown(self):
        p = Path(self.test_db_path)
        if p.exists():
            p.unlink()

    def test_salary_parser_lpa(self):
        # Explicit LPA string
        res = normalize_salary("15 - 25 LPA")
        self.assertEqual(res, "15 - 25 LPA")

        # Extracted LPA
        text = "Backend Engineer required. Package offered: 12 - 18 LPA depending on interview."
        extracted = extract_salary_from_text(text)
        self.assertIsNotNone(extracted)
        self.assertIn("LPA", extracted)

    def test_salary_parser_usd_and_monthly(self):
        # Monthly stipend
        monthly_text = "Junior Python Intern stipend ₹35,000 / month"
        monthly = extract_salary_from_text(monthly_text)
        self.assertIsNotNone(monthly)
        self.assertIn("month", monthly)

        # USD annual
        usd_sal = normalize_salary(min_sal=130000, max_sal=175000)
        self.assertEqual(usd_sal, "$130k - $175k / yr")

    def test_all_28_platforms_registered(self):
        registry = PlatformRegistry()
        available_platforms = set(registry.providers.keys())

        required_28 = [
            "monster",
            "foundit",
            "hack2skills",
            "cuvette",
            "flexjobs",
            "remoteok",
            "remotive",
            "justremote",
            "weworkremotely",
            "workingnomads",
            "4dayweek",
            "jobspresso",
            "crossover",
            "upwork",
            "devto",
            "simplify",
            "handshake",
            "glassdoor",
            "dice",
            "ripplematch",
            "unstop",
            "deep",
            "ginia",
            "forage",
            "cutshort",
            "ycombinator",
            "interninsider",
            "snaphunt"
        ]

        for p in required_28:
            self.assertIn(
                p,
                available_platforms,
                f"Platform '{p}' should be registered in PlatformRegistry"
            )

    def test_database_salary_persistence(self):
        job = JobListing(
            id="test_sal_job_1",
            platform="foundit",
            title="Senior GenAI Engineer",
            company="Tech Corp",
            location="Bengaluru",
            url="https://example.com/job1",
            salary="₹25 - ₹35 LPA",
            status=ApplicationStatus.DISCOVERED
        )
        self.db.insert_job(job)
        retrieved = self.db.get_job("test_sal_job_1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.salary, "₹25 - ₹35 LPA")


if __name__ == "__main__":
    unittest.main()

