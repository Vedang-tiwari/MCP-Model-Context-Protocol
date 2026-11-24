"""Unit and integration test checks for MCP Job Scout components."""
import unittest
import asyncio
from pathlib import Path

from core.models import JobListing, ApplicationStatus
from core.database import DatabaseManager
from core.profile_manager import ProfileManager


class TestMCPComponents(unittest.TestCase):
    def setUp(self):
        self.test_db_path = "data/test_jobs.db"
        self.db = DatabaseManager(self.test_db_path)
        self.profile_mgr = ProfileManager()

    def tearDown(self):
        p = Path(self.test_db_path)
        if p.exists():
            p.unlink()

    def test_database_insert_and_deduplication(self):
        job = JobListing(
            id="test_job_123",
            platform="ats_direct",
            title="Senior Full Stack Engineer",
            company="Stripe",
            location="Remote",
            url="https://stripe.com/jobs/123",
            apply_url="https://stripe.com/jobs/123/apply",
            is_easy_apply=False,
            status=ApplicationStatus.DISCOVERED
        )
        # First insert should succeed
        inserted = self.db.insert_job(job)
        self.assertTrue(inserted)

        # Duplicate insert should return False
        dup = self.db.insert_job(job)
        self.assertFalse(dup)

        retrieved = self.db.get_job("test_job_123")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.company, "Stripe")

    def test_profile_evaluation(self):
        job = JobListing(
            id="test_fit_job",
            platform="ats_direct",
            title="Senior Full Stack Engineer",
            company="OpenAI",
            location="Remote",
            url="https://openai.com/jobs/fit",
            description="Looking for an engineer with Python, FastAPI, and Next.js experience.",
            status=ApplicationStatus.DISCOVERED
        )
        score, reasons = self.profile_mgr.evaluate_fit(job)
        self.assertGreater(score, 50)
        self.assertTrue(any("Title" in r for r in reasons))

    def test_blacklist_enforcement(self):
        job = JobListing(
            id="test_blacklist_job",
            platform="indeed",
            title="Software Developer",
            company="Revature",
            location="Remote",
            url="https://indeed.com/jobs/revature",
            status=ApplicationStatus.DISCOVERED
        )
        score, reasons = self.profile_mgr.evaluate_fit(job)
        self.assertEqual(score, 0)
        self.assertTrue(any("blacklist" in r.lower() for r in reasons))

    def test_llm_client_initialization(self):
        from core.llm_client import LLMClient
        # Default initialization (Google Gemini)
        default_client = LLMClient()
        self.assertEqual(default_client.provider, "gemini")
        self.assertEqual(default_client.model, "gemini-2.0-flash")
        self.assertEqual(default_client.base_url, "https://generativelanguage.googleapis.com/v1beta/openai")

        # Explicit gemini provider
        gemini_client = LLMClient(provider="gemini", model="gemini-1.5-flash", api_key="test_gemini_key")
        self.assertEqual(gemini_client.provider, "gemini")
        self.assertEqual(gemini_client.model, "gemini-1.5-flash")
        self.assertEqual(gemini_client.api_key, "test_gemini_key")
        self.assertEqual(gemini_client.base_url, "https://generativelanguage.googleapis.com/v1beta/openai")

        # Google alias
        google_client = LLMClient(provider="google")
        self.assertEqual(google_client.provider, "google")
        self.assertEqual(google_client.model, "gemini-2.0-flash")
        self.assertEqual(google_client.base_url, "https://generativelanguage.googleapis.com/v1beta/openai")

        # Ollama provider
        ollama_client = LLMClient(provider="ollama", model="qwen2.5:14b")
        self.assertEqual(ollama_client.provider, "ollama")
        self.assertEqual(ollama_client.model, "qwen2.5:14b")

        # Groq provider
        groq_client = LLMClient(provider="groq", api_key="test_groq_key")
        self.assertEqual(groq_client.provider, "groq")
        self.assertEqual(groq_client.model, "llama-3.3-70b-versatile")
        self.assertEqual(groq_client.base_url, "https://api.groq.com/openai/v1")

    def test_orchestrator_tool_definitions(self):
        from core.orchestrator import TOOL_DEFINITIONS
        tool_names = [t["function"]["name"] for t in TOOL_DEFINITIONS]
        self.assertIn("search_recent_jobs", tool_names)
        self.assertIn("evaluate_job_fit", tool_names)
        self.assertIn("apply_to_job", tool_names)
        self.assertIn("get_application_status", tool_names)

    def test_platform_registry_and_custom_addition(self):
        from discovery.registry import PlatformRegistry
        from core.models import CustomPlatformConfig, PlatformType

        test_config_path = Path("data/test_custom_platforms.json")
        registry = PlatformRegistry(custom_platforms_path=test_config_path)

        # Built-ins should be present
        self.assertIn("linkedin", registry.providers)
        self.assertIn("indeed", registry.providers)

        # Add custom platform
        cfg = CustomPlatformConfig(
            name="test_board",
            display_name="Test Board",
            platform_type=PlatformType.RSS,
            url_template="https://example.com/feed.rss"
        )
        registry.add_custom_platform(cfg)
        self.assertIn("test_board", registry.providers)

        # List platforms
        all_platforms = registry.list_platforms()
        slugs = [p["name"] for p in all_platforms]
        self.assertIn("test_board", slugs)

        # Cleanup
        registry.remove_custom_platform("test_board")
        self.assertNotIn("test_board", registry.providers)
        if test_config_path.exists():
            test_config_path.unlink()


if __name__ == "__main__":
    unittest.main()
