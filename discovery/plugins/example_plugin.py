"""Example drop-in Python plugin for adding a custom job platform.
Any file in discovery/plugins/ that subclasses BaseJobProvider is automatically discovered and registered!
"""
import logging
from typing import List
from datetime import datetime
from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus

logger = logging.getLogger(__name__)


class SampleCustomPlatformProvider(BaseJobProvider):
    def __init__(self):
        super().__init__(name="sample_tech_board")

    async def fetch_recent_jobs(
        self,
        roles: List[str],
        locations: List[str],
        max_age_hours: int = 24
    ) -> List[JobListing]:
        """
        Custom scraping or API fetching logic for your proprietary or niche job board.
        """
        logger.info(f"[{self.name}] Running custom provider for roles: {roles}")
        
        # Example demonstration of a generated/fetched listing
        results = [
            JobListing(
                id=self.generate_job_id(self.name, "Acme AI Corp", "Lead AI Engineer", "https://example.com/jobs/acme-ai"),
                platform=self.name,
                title="Lead AI Engineer",
                company="Acme AI Corp",
                location="Remote",
                url="https://example.com/jobs/acme-ai",
                apply_url="https://example.com/jobs/acme-ai/apply",
                is_easy_apply=True,
                description="Seeking a Lead AI Engineer with experience in Autonomous Agents, LLM tool-calling, and Python.",
                posted_at=datetime.utcnow(),
                discovered_at=datetime.utcnow(),
                status=ApplicationStatus.DISCOVERED,
                metadata={"provider_type": "python_plugin"}
            )
        ]
        return results
