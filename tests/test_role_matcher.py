"""Tests for strict role matching and keyword filtering."""
import unittest
from core.role_matcher import matches_target_roles


class TestRoleMatcher(unittest.TestCase):
    def test_empty_target_roles_matches_all(self):
        self.assertTrue(matches_target_roles("Civil Engineer", []))
        self.assertTrue(matches_target_roles("Marketing Manager", []))

    def test_exact_role_matching(self):
        roles = ["Gen AI Engineer", "Python Developer"]
        self.assertTrue(matches_target_roles("Gen AI Engineer", roles))
        self.assertTrue(matches_target_roles("Senior Python Developer", roles))

    def test_token_and_equivalence_matching(self):
        roles = ["Python Developer"]
        # 'engineer' is equivalent to 'developer'
        self.assertTrue(matches_target_roles("Senior Python Software Engineer", roles))
        self.assertTrue(matches_target_roles("Python Backend Dev", roles))
        # Non-matching tech role
        self.assertFalse(matches_target_roles("Senior Java Engineer", roles))
        self.assertFalse(matches_target_roles("Ruby Developer", roles))

    def test_acronym_matching(self):
        self.assertTrue(matches_target_roles("Software Engineer II", ["SWE"]))
        self.assertTrue(matches_target_roles("Senior SWE", ["Software Engineer"]))
        self.assertTrue(matches_target_roles("Forward Deployed Engineer", ["FDE"]))
        self.assertTrue(matches_target_roles("FDE - Enterprise Solutions", ["Forward Deployed Engineer"]))

    def test_single_keyword_specialty(self):
        roles = ["Solidity"]
        self.assertTrue(matches_target_roles("Solidity Smart Contract Engineer", roles))
        self.assertFalse(matches_target_roles("React Frontend Developer", roles))

    def test_ai_and_genai_variations(self):
        roles = ["Gen AI Engineer"]
        self.assertTrue(matches_target_roles("Generative AI Software Engineer", roles))
        self.assertTrue(matches_target_roles("GenAI Research Engineer", roles))
        self.assertFalse(matches_target_roles("Civil Structural Engineer", roles))
        self.assertFalse(matches_target_roles("Sales Account Executive", roles))

    def test_tag_matching(self):
        self.assertTrue(matches_target_roles("Software Engineer", ["Python Developer"], tags=["python", "django"]))
        self.assertFalse(matches_target_roles("Software Engineer", ["Python Developer"], tags=["java", "spring"]))

    def test_aggregator_strict_filtering(self):
        import asyncio
        from unittest.mock import MagicMock, AsyncMock
        from core.models import JobListing, ApplicationStatus
        from discovery.aggregator import JobAggregator
        from datetime import datetime, timezone

        mock_db = MagicMock()
        mock_db.is_job_seen.return_value = False
        mock_db.insert_job.return_value = True

        mock_profile_mgr = MagicMock()
        mock_profile_mgr.preferences.target_roles = ["Gen AI Engineer", "Solidity"]
        mock_profile_mgr.preferences.locations = ["Remote"]
        mock_profile_mgr.preferences.max_job_age_hours = 24
        mock_profile_mgr.preferences.match_threshold_percent = 70
        mock_profile_mgr.preferences.auto_apply = False
        mock_profile_mgr.preferences.platforms = {"test_provider": True}
        mock_profile_mgr.evaluate_fit.return_value = (85, ["Good fit"])

        # Create two jobs: one matching, one non-matching
        matching_job = JobListing(
            id="job_1", platform="test_provider", title="Senior Gen AI Engineer",
            company="Anthropic", location="Remote", url="https://example.com/1",
            salary="20-30 LPA", is_easy_apply=False, description="Work on LLMs",
            posted_at=datetime.now(timezone.utc), discovered_at=datetime.now(timezone.utc),
            status=ApplicationStatus.DISCOVERED, metadata={}
        )
        non_matching_job = JobListing(
            id="job_2", platform="test_provider", title="Civil Structural Engineer",
            company="BuildCorp", location="Remote", url="https://example.com/2",
            salary="10-15 LPA", is_easy_apply=False, description="Bridges",
            posted_at=datetime.now(timezone.utc), discovered_at=datetime.now(timezone.utc),
            status=ApplicationStatus.DISCOVERED, metadata={}
        )

        mock_provider = MagicMock()
        mock_provider.name = "test_provider"
        mock_provider.fetch_recent_jobs = AsyncMock(return_value=[matching_job, non_matching_job])

        mock_registry = MagicMock()
        mock_registry.providers = {"test_provider": mock_provider}

        aggregator = JobAggregator(db=mock_db, profile_mgr=mock_profile_mgr, registry=mock_registry)
        summary = asyncio.run(aggregator.run_discovery_cycle(roles=["Gen AI Engineer", "Solidity"]))

        # Out of 2 fetched jobs, only 1 matched the target roles
        self.assertEqual(summary["total_fetched"], 2)
        self.assertEqual(summary["new_unique_jobs"], 1)
        # Verify db.insert_job was only called for the matching job
        mock_db.insert_job.assert_called_once_with(matching_job)


if __name__ == "__main__":
    unittest.main()
