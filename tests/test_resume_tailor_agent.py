"""Unit tests for the Autonomous Resume Tailoring Agent and Fabrication Audit.
Verifies Blueprint §4.3, §7, and §8 requirements.
"""
import sys
import os
import asyncio
from pathlib import Path
import unittest

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from starlette.testclient import TestClient

from core.models import JobListing, ApplicationStatus
from core.profile_manager import ProfileManager
from core.database import DatabaseManager
from core.resume_tailor_agent import ResumeTailorAgent
from web.server import app


class TestResumeTailorAgent(unittest.TestCase):
    def setUp(self):
        self.profile_mgr = ProfileManager()
        self.db = DatabaseManager()
        self.agent = ResumeTailorAgent(profile_mgr=self.profile_mgr)
        self.client = TestClient(app)

    def test_requirement_extraction_ai_role(self):
        analysis = self.agent._analyze_requirements(
            title="Senior Generative AI & Machine Learning Engineer",
            description="We are looking for a Senior AI Engineer skilled in Python, FastAPI, Docker, and LangChain to build agentic pipelines.",
            profile=self.profile_mgr.get_profile_yaml()
        )
        self.assertEqual(analysis["seniority"], "Senior")
        self.assertEqual(analysis["domain"], "AI & Machine Learning")
        self.assertIn("Python", analysis["matched_strong_skills"])
        self.assertIn("FastAPI", analysis["matched_strong_skills"])
        self.assertIn("LangChain", analysis["matched_familiar_skills"])

    def test_requirement_extraction_devops_role(self):
        analysis = self.agent._analyze_requirements(
            title="DevOps & Infrastructure Engineer",
            description="Seeking a DevOps engineer with strong Kubernetes, Docker, AWS, and CI/CD automation experience.",
            profile=self.profile_mgr.get_profile_yaml()
        )
        self.assertEqual(analysis["domain"], "DevOps & Cloud Infrastructure")
        self.assertIn("Docker", analysis["matched_strong_skills"])
        self.assertIn("Kubernetes", analysis["matched_familiar_skills"])
        self.assertIn("AWS", analysis["matched_familiar_skills"])

    def test_zero_fabrication_audit_pass(self):
        job = JobListing(
            id="job_test_ai_1",
            platform="greenhouse",
            title="Senior AI Engineer",
            company="Anthropic",
            location="Remote",
            url="https://boards.greenhouse.io/anthropic/jobs/1",
            description="Build agent systems with Python, FastAPI, and Playwright."
        )

        artifacts = asyncio.run(self.agent.tailor_for_job(job, generate_pdf=False))
        self.assertTrue(artifacts.audit_passed)
        self.assertEqual(len(artifacts.audit_violations), 0)
        self.assertIn("VEDANG TIWARI", artifacts.ats_text)
        self.assertIn("TechNova Solutions", artifacts.ats_text)
        self.assertIn("St. Andrews Institute of Technology & Management", artifacts.ats_text)
        self.assertIn("OBJECTIVE", artifacts.ats_text)
        self.assertIn("EDUCATION", artifacts.ats_text)
        self.assertIn("SKILL SUMMARY", artifacts.ats_text)

    def test_zero_fabrication_audit_catches_hallucinations(self):
        p_yaml = self.profile_mgr.get_profile_yaml()

        # Injected fake claim in tailored content
        fake_tailored = {
            "summary": "PhD in Computer Science from Stanford University and Google Fellow.",
            "ordered_skills": {
                "Languages & Core": ["Python", "Rust", "Haskell", "Fortran"],  # Rust, Haskell, Fortran not in profile
            },
            "experience": [
                {"company": "FakeCorp Inc", "bullets": ["Invented quantum computer."]}
            ],
            "claims_diff": []
        }

        audit_passed, violations, _ = self.agent._audit_fabrication(fake_tailored, p_yaml)
        self.assertFalse(audit_passed)
        self.assertTrue(any("FakeCorp Inc" in v for v in violations))
        self.assertTrue(any("phd in computer science" in v.lower() or "stanford" in v.lower() for v in violations))
        self.assertTrue(any("Rust" in v or "Haskell" in v for v in violations))

    def test_cover_letter_length_and_content(self):
        job = JobListing(
            id="job_test_cov_1",
            platform="lever",
            title="Senior Full Stack Engineer",
            company="Stripe",
            location="Remote",
            url="https://jobs.lever.co/stripe/1",
            description="Full stack role using Python, React, and PostgreSQL."
        )
        artifacts = asyncio.run(self.agent.tailor_for_job(job, generate_pdf=False))
        words = artifacts.cover_letter.split()
        self.assertLessEqual(len(words), 200)
        self.assertIn("Stripe", artifacts.cover_letter)
        self.assertIn("Vedang Tiwari", artifacts.cover_letter)

    def test_api_tailor_job_resume(self):
        # Insert a job in database
        job = JobListing(
            id="job_tailor_api_test",
            platform="greenhouse",
            title="Backend Systems Architect",
            company="Databricks",
            location="Remote",
            url="https://boards.greenhouse.io/databricks/jobs/1",
            description="Distributed systems, Python, Redis, and high-throughput data processing."
        )
        self.db.insert_job(job)

        resp = self.client.post("/api/jobs/job_tailor_api_test/tailor", json={"generate_pdf": False})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("artifacts", data)
        self.assertEqual(data["artifacts"]["role_title"], "Backend Systems Architect")
        self.assertEqual(data["artifacts"]["company"], "Databricks")
        self.assertTrue(data["artifacts"]["audit_passed"])

        # Check that job status updated to TAILORED in DB
        db_job = self.db.get_job("job_tailor_api_test")
        self.assertEqual(db_job.status, ApplicationStatus.TAILORED)
        self.assertIn("tailored_summary", db_job.metadata)

    def test_api_tailor_custom_resume(self):
        payload = {
            "role": "Staff Platform Engineer",
            "company": "Cloudflare",
            "description": "Kubernetes, Docker, Go, microservices, and distributed observability.",
            "generate_pdf": False
        }
        resp = self.client.post("/api/resume/tailor", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("artifacts", data)
        self.assertEqual(data["artifacts"]["role_title"], "Staff Platform Engineer")
        self.assertEqual(data["artifacts"]["company"], "Cloudflare")
        self.assertTrue(data["artifacts"]["audit_passed"])


if __name__ == "__main__":
    unittest.main()
