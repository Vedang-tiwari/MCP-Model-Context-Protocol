"""Aggregator coordinating multi-platform job discovery, deduplication, and evaluation."""
import asyncio
import logging
from typing import List, Dict, Any, Optional

from core.models import JobListing, ApplicationStatus
from core.database import DatabaseManager
from core.profile_manager import ProfileManager
from .providers import (
    LinkedInProvider,
    IndeedProvider,
    ATSDirectProvider,
    WellfoundProvider,
    NaukriProvider,
    InternshalaProvider
)

from .registry import PlatformRegistry

logger = logging.getLogger(__name__)


class JobAggregator:
    def __init__(
        self,
        db: DatabaseManager,
        profile_mgr: ProfileManager,
        registry: Optional[PlatformRegistry] = None
    ):
        self.db = db
        self.profile_mgr = profile_mgr
        self.registry = registry or PlatformRegistry()

    @property
    def providers(self) -> Dict[str, Any]:
        return self.registry.providers

    async def run_discovery_cycle(
        self,
        roles: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        max_age_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Executes one full discovery sweep across all enabled platforms.
        Deduplicates against the local SQLite database and evaluates fit.
        """
        prefs = self.profile_mgr.preferences
        active_roles = roles or prefs.target_roles
        active_locs = locations or prefs.locations
        active_age = max_age_hours or prefs.max_job_age_hours

        logger.info(f"Starting discovery sweep for {len(active_roles)} roles across enabled platforms...")

        tasks = []
        for name, provider in self.providers.items():
            if prefs.platforms.get(name, True):
                tasks.append(self._safely_fetch(provider, active_roles, active_locs, active_age))

        # Run all provider tasks concurrently
        provider_results = await asyncio.gather(*tasks)

        all_discovered: List[JobListing] = []
        for res_list in provider_results:
            all_discovered.extend(res_list)

        newly_inserted = 0
        qualified_jobs = 0

        for job in all_discovered:
            # Check if seen
            if self.db.is_job_seen(job.id):
                continue

            # Evaluate fit against candidate profile
            score, reasons = self.profile_mgr.evaluate_fit(job)
            job.match_score = score
            job.match_reasons = reasons

            # If score meets threshold and auto_apply is enabled, queue it
            if score >= prefs.match_threshold_percent:
                qualified_jobs += 1
                if prefs.auto_apply:
                    job.status = ApplicationStatus.QUEUED
                else:
                    job.status = ApplicationStatus.EVALUATED
            else:
                job.status = ApplicationStatus.DISCOVERED

            # Persist to database
            if self.db.insert_job(job):
                newly_inserted += 1

        summary = {
            "total_fetched": len(all_discovered),
            "new_unique_jobs": newly_inserted,
            "qualified_matches": qualified_jobs,
            "threshold": prefs.match_threshold_percent,
            "auto_apply_enabled": prefs.auto_apply
        }

        logger.info(f"Discovery sweep completed: {newly_inserted} new unique jobs found, {qualified_jobs} qualified.")
        return summary

    async def _safely_fetch(self, provider, roles, locs, max_age):
        try:
            return await provider.fetch_recent_jobs(roles, locs, max_age)
        except Exception as e:
            logger.error(f"Provider {provider.name} failed during cycle: {e}")
            return []
