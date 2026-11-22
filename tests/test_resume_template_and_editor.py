"""Unit tests for the Official Resume Template and Job-Specific Custom Resume Editor."""
import unittest
import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from starlette.testclient import TestClient

from core.models import JobListing, ApplicationStatus
from core.database import DatabaseManager
from core.profile_manager import ProfileManager
from core.resume_docx_renderer import ResumeDocxRenderer
from web.server import app


class TestResumeTemplateAndEditor(unittest.TestCase):
    def setUp(self):
        self.renderer = ResumeDocxRenderer()
        self.test_output = Path("data/artifacts/test_custom_resume.docx")
        self.client = TestClient(app)
        self.db = DatabaseManager()

        # Seed a test job for custom editing
        self.test_job = JobListing(
            id="test_edit_job_999",
            platform="ats_direct",
            title="Senior AI Systems Engineer",
            company="Anthropic Ecosystem",
            url="https://boards.greenhouse.io/anthropic/jobs/999123",
            metadata={
                "tailored_summary": "Initial AI Systems Architect objective.",
                "tailored_cover_letter": "Initial cover letter text."
            }
        )
        self.db.insert_job(self.test_job)

    def tearDown(self):
        if self.test_output.exists():
            self.test_output.unlink()
        self.db.delete_job("test_edit_job_999")

    def test_default_template_data(self):
        """Default template data must contain Vedang Tiwari's ground truth credentials."""
        data = self.renderer.get_default_template_data()
        self.assertIn("VEDANG TIWARI", data["full_name"].upper())
        self.assertIn("vedangt027@gmail.com", data["contact_line"])
        self.assertIn("8527157603", data["contact_line"])
        self.assertTrue(len(data["objective"]) > 30)
        self.assertTrue(len(data["experiences"]) >= 2)
        self.assertTrue(len(data["projects"]) >= 2)
        self.assertIn("Python", data["skills"]["languages"])

    def test_render_docx_validity(self):
        """Rendering to docx must produce a valid OpenXML package containing updated text."""
        custom_data = self.renderer.get_default_template_data()
        custom_data["objective"] = "Targeted AI Systems Architect specializing in autonomous agent workflows."

        out_path = self.renderer.render(custom_data, str(self.test_output))
        self.assertTrue(os.path.exists(out_path))
        self.assertGreater(os.path.getsize(out_path), 5000)

        # Inspect generated docx XML
        with zipfile.ZipFile(out_path, "r") as zin:
            self.assertIn("word/document.xml", zin.namelist())
            tree = ET.fromstring(zin.read("word/document.xml"))
            full_text = "".join(tree.itertext())
            self.assertIn("Targeted AI Systems Architect", full_text)
            self.assertIn("VEDANG TIWARI", full_text)

    def test_api_template_resume_endpoints(self):
        """Web API must provide the template JSON and downloadable .docx file."""
        res_json = self.client.get("/api/template/resume")
        self.assertEqual(res_json.status_code, 200)
        data = res_json.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["template_name"], "mcp-resume-template.docx")
        self.assertIn("VEDANG TIWARI", data["candidate_name"].upper())

        res_dl = self.client.get("/api/template/resume/download")
        self.assertEqual(res_dl.status_code, 200)
        self.assertIn("wordprocessingml.document", res_dl.headers.get("content-type", ""))
        self.assertGreater(len(res_dl.content), 5000)

    def test_job_custom_resume_flow(self):
        """User must be able to GET a draft custom resume, POST manual edits, and download the resulting .docx."""
        # 1. GET initial draft
        res_get = self.client.get(f"/api/jobs/{self.test_job.id}/custom-resume")
        self.assertEqual(res_get.status_code, 200)
        get_data = res_get.json()
        self.assertEqual(get_data["job_id"], self.test_job.id)
        self.assertIn("resume_data", get_data)

        # 2. POST manual customized edits
        customized_payload = get_data["resume_data"]
        customized_payload["objective"] = "Tailored for Senior AI Systems Engineer at Anthropic Ecosystem with focus on agent eval."
        customized_payload["experiences"][0]["bullets"][0] = "Spearheaded custom LLM tool integration cutting evaluation latency by 60%."

        res_post = self.client.post(
            f"/api/jobs/{self.test_job.id}/custom-resume",
            json={"resume_data": customized_payload, "cover_letter": "I am excited to apply for this specific role."}
        )
        self.assertEqual(res_post.status_code, 200)
        post_data = res_post.json()
        self.assertTrue(post_data["success"])
        self.assertTrue(os.path.exists(post_data["docx_path"]))

        # 3. Verify Job in DB was updated to TAILORED status and has custom resume metadata
        updated_job = self.db.get_job(self.test_job.id)
        self.assertEqual(updated_job.status, ApplicationStatus.TAILORED)
        self.assertIn("custom_resume", updated_job.metadata)
        self.assertEqual(updated_job.metadata["custom_resume"]["objective"], customized_payload["objective"])

        # 4. ProfileManager.get_resume_for_job must pick the job-specific custom resume
        prof_mgr = ProfileManager()
        selected_resume = prof_mgr.get_resume_for_job(updated_job)
        self.assertIsNotNone(selected_resume)
        self.assertTrue(str(selected_resume).endswith(".docx"))
        self.assertIn(self.test_job.id[:8], str(selected_resume))


if __name__ == "__main__":
    unittest.main()
