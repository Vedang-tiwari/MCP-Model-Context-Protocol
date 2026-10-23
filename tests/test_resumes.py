"""Unit tests for multi-resume role mapping, uploads, and automated routing."""
import sys
import unittest
from pathlib import Path
import tempfile
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from starlette.testclient import TestClient

from core.models import JobListing, ApplicationStatus
from core.profile_manager import ProfileManager
from web.server import app


class TestMultiResumeRouting(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.profile_mgr = ProfileManager()

    def test_role_based_resume_selection(self):
        # AI job
        ai_job = JobListing(
            id="job_ai_1",
            platform="greenhouse",
            title="Senior Generative AI & LLM Engineer",
            company="Anthropic",
            location="Remote",
            url="https://boards.greenhouse.io/anthropic/jobs/1"
        )
        ai_resume = self.profile_mgr.get_resume_for_job(ai_job)
        self.assertIsNotNone(ai_resume)
        self.assertIn("ai", ai_resume.name.lower())

        # SWE job
        swe_job = JobListing(
            id="job_swe_1",
            platform="lever",
            title="Staff Software Development Engineer (SWE)",
            company="Stripe",
            location="Remote",
            url="https://jobs.lever.co/stripe/1"
        )
        swe_resume = self.profile_mgr.get_resume_for_job(swe_job)
        self.assertIsNotNone(swe_resume)
        self.assertIn("swe", swe_resume.name.lower())

        # FDE job
        fde_job = JobListing(
            id="job_fde_1",
            platform="greenhouse",
            title="Forward Deployed Engineer (FDE)",
            company="Palantir",
            location="Remote",
            url="https://boards.greenhouse.io/palantir/jobs/1"
        )
        fde_resume = self.profile_mgr.get_resume_for_job(fde_job)
        self.assertIsNotNone(fde_resume)
        self.assertIn("fde", fde_resume.name.lower())

        # Unmatched job -> default fallback
        unknown_job = JobListing(
            id="job_unk_1",
            platform="indeed",
            title="Senior Brand Marketing Manager",
            company="Target",
            location="Remote",
            url="https://indeed.com/viewjob?jk=1"
        )
        fallback_resume = self.profile_mgr.get_resume_for_job(unknown_job)
        self.assertIsNotNone(fallback_resume)

    def test_api_resumes_crud(self):
        # 1. List resumes
        r = self.client.get("/api/resumes")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("resumes", data)
        self.assertGreaterEqual(data["count"], 1)

        # 2. Upload new resume
        dummy_content = b"%PDF-1.4 Mock CV Content"
        up_resp = self.client.post(
            "/api/resumes/upload",
            files={"file": ("test_devops.pdf", dummy_content)},
            data={"role": "DevOps Engineer", "is_default": "false"}
        )
        self.assertEqual(up_resp.status_code, 200)
        up_data = up_resp.json()
        self.assertTrue(up_data["success"])
        new_id = up_data["resume"]["id"]
        self.assertEqual(up_data["resume"]["role_pattern"], "DevOps Engineer")

        # 3. Test routing with newly uploaded role
        self.profile_mgr.reload()
        devops_job = JobListing(
            id="job_devops_1",
            platform="ats_direct",
            title="Lead DevOps & Cloud Engineer",
            company="Cloudflare",
            location="Remote",
            url="https://cloudflare.com/jobs/1"
        )
        matched_resume = self.profile_mgr.get_resume_for_job(devops_job)
        self.assertIsNotNone(matched_resume)
        self.assertIn("devops", matched_resume.name.lower())

        # 4. Download resume
        dl_resp = self.client.get(f"/api/resumes/{new_id}/download")
        self.assertEqual(dl_resp.status_code, 200)
        self.assertEqual(dl_resp.content, dummy_content)

        # 5. Delete resume
        del_resp = self.client.delete(f"/api/resumes/{new_id}")
        self.assertEqual(del_resp.status_code, 200)
        self.assertTrue(del_resp.json()["success"])


if __name__ == "__main__":
    unittest.main()
