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

    def test_static_assets(self):
        css_resp = self.client.get("/static/styles.css")
        self.assertEqual(css_resp.status_code, 200)
        self.assertIn("--color-canvas: #101010;", css_resp.text)

        js_resp = self.client.get("/static/app.js")
        self.assertEqual(js_resp.status_code, 200)
        self.assertIn("initApp", js_resp.text)


if __name__ == "__main__":
    unittest.main()
