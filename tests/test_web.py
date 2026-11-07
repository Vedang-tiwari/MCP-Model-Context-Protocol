"""Unit tests for the MCP Web Dashboard and REST API endpoints."""
import sys
import unittest

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from starlette.testclient import TestClient
from web.server import app


class TestWebDashboard(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_index_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("MCP — Autonomous Job Scout", response.text)

    def test_api_stats(self):
        response = self.client.get("/api/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_discovered", data)
        self.assertIn("status_breakdown", data)
        self.assertIn("platform_breakdown", data)

    def test_api_jobs_listing(self):
        response = self.client.get("/api/jobs?limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("count", data)
        self.assertIn("jobs", data)
        self.assertIsInstance(data["jobs"], list)

    def test_api_profile(self):
        response = self.client.get("/api/profile")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("profile", data)
        self.assertIn("preferences", data)

    def test_api_platforms(self):
        response = self.client.get("/api/platforms")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("platforms", data)
        self.assertIsInstance(data["platforms"], list)

    def test_api_system(self):
        response = self.client.get("/api/system")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("llm_model", data)
        self.assertIn("active_platforms_count", data)

    def test_api_target_roles_crud(self):
        # 1. GET target roles
        get_resp = self.client.get("/api/target-roles")
        self.assertEqual(get_resp.status_code, 200)
        roles = get_resp.json()["target_roles"]
        self.assertIsInstance(roles, list)

        # 2. POST new target role
        test_role = "Test Specialty AI Engineer"
        add_resp = self.client.post("/api/target-roles", json={"role": test_role})
        self.assertEqual(add_resp.status_code, 200)
        self.assertIn(test_role, add_resp.json()["target_roles"])

        # 3. DELETE target role
        import urllib.parse
        del_resp = self.client.delete(f"/api/target-roles/{urllib.parse.quote(test_role)}")
        self.assertEqual(del_resp.status_code, 200)
        self.assertNotIn(test_role, del_resp.json()["target_roles"])

    def test_static_assets(self):
        css_resp = self.client.get("/static/styles.css")
        self.assertEqual(css_resp.status_code, 200)
        self.assertIn("--color-canvas: #101010;", css_resp.text)

        js_resp = self.client.get("/static/app.js")
        self.assertEqual(js_resp.status_code, 200)
        self.assertIn("initApp", js_resp.text)

    def test_api_batch_apply_validation(self):
        # Test batch apply with empty/non-existent IDs
        resp = self.client.post("/api/jobs/batch-apply", json={"job_ids": ["non_existent_id_999"]})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.json())

    def test_api_batch_apply_mocked_success(self):
        from unittest.mock import AsyncMock, patch
        from core.models import ApplicationRecord, ApplicationStatus, JobListing

        mock_rec = ApplicationRecord(
            job_id="mock_job_1",
            status=ApplicationStatus.APPLIED,
            notes="Submitted successfully"
        )
        with patch("web.server.agent.batch_apply", new_callable=AsyncMock) as mock_batch:
            mock_batch.return_value = [mock_rec]
            with patch("web.server.db.get_job") as mock_get_job:
                mock_get_job.return_value = JobListing(
                    id="mock_job_1", platform="lever", title="SWE", company="Acme", url="https://jobs.lever.co/acme/1"
                )
                resp = self.client.post("/api/jobs/batch-apply", json={"job_ids": ["mock_job_1"], "auto_submit": True})
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertTrue(data["success"])
                self.assertEqual(data["total"], 1)
                self.assertEqual(data["applied"], 1)
                self.assertEqual(data["results"][0]["status"], "APPLIED")


if __name__ == "__main__":
    unittest.main()
