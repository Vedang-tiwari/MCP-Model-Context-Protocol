"""Aggregator coordinating multi-platform job discovery, deduplication, and evaluation."""
import asyncio
import logging
from typing import List, Dict, Any, Optional

from core.models import JobListing, ApplicationStatus
from core.database import DatabaseManager
from core.profile_manager import ProfileManager
from core.role_matcher import matches_target_roles
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
        max_age_hours: Optional[int] = None,
        platform: Optional[str] = None,
        platforms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Executes a discovery sweep across all enabled or specifically targeted platforms.
        Deduplicates against the local SQLite database and evaluates fit.
        """
        prefs = self.profile_mgr.preferences
        active_roles = roles or prefs.target_roles
        active_locs = locations or prefs.locations
        active_age = max_age_hours or prefs.max_job_age_hours

        # Resolve targeted platforms if specified
        target_platforms = set()
        if platform and platform.strip():
            target_platforms.add(platform.strip().lower())
        if platforms:
            for p in platforms:
                if p and p.strip():
                    target_platforms.add(p.strip().lower())

        ats_aliases = {"greenhouse", "lever", "ashby", "direct_ats", "ats", "ats_direct"}
        if target_platforms.intersection(ats_aliases):
            target_platforms.add("ats_direct")

        if target_platforms:
            logger.info(f"Starting targeted discovery sweep for platforms {list(target_platforms)} ({len(active_roles)} roles)...")
        else:
            logger.info(f"Starting discovery sweep for {len(active_roles)} roles across enabled platforms...")

        tasks = []
        selected_providers = []
        seen_providers = set()

        for name, provider in self.providers.items():
            name_norm = name.lower()
            prov_name = getattr(provider, "name", "").lower()

            # Prevent duplicate execution if provider is aliased multiple times
            prov_id = id(provider)
            if prov_id in seen_providers:
                continue

            if target_platforms:
                matched = (
                    name_norm in target_platforms
                    or prov_name in target_platforms
                    or (name_norm == "ats_direct" and any(a in target_platforms for a in ats_aliases))
                    or any(name_norm.replace("-", "").replace(".", "").replace("_", "") == tp.replace("-", "").replace(".", "").replace("_", "") for tp in target_platforms)
                )
                if not matched:
                    continue
            else:
                if not prefs.platforms.get(name, True):
                    continue

            seen_providers.add(prov_id)
            tasks.append(self._safely_fetch(provider, active_roles, active_locs, active_age))
            selected_providers.append(name)

        if not tasks and target_platforms:
            logger.warning(f"No registered providers matched target platforms: {target_platforms}")

        # Run provider tasks concurrently
        provider_results = await asyncio.gather(*tasks) if tasks else []

        all_discovered: List[JobListing] = []
        for res_list in provider_results:
            all_discovered.extend(res_list)

        newly_inserted = 0
        qualified_jobs = 0

        # Broad tech / engineering keyword filter used when targeting a platform
        related_tech_keywords = [
            "engineer", "developer", "software", "ai", "machine learning", "ml", "data",
            "full stack", "fullstack", "backend", "frontend", "devops", "cloud", "platform",
            "python", "react", "typescript", "sde", "swe", "fde", "architect", "lead", "specialist"
        ]

        for job in all_discovered:
            tags = job.metadata.get("tags") if isinstance(job.metadata, dict) else None

            # Role filtering: if active_roles configured, check strict matching.
            # When specifically targeting a platform, also allow related tech/engineering postings.
            if active_roles:
                matched_role = matches_target_roles(job.title, active_roles, tags=tags, description=job.description)
                if not matched_role:
                    if target_platforms:
                        # Ensure it is at least related to tech/software engineering
                        is_related = any(kw in job.title.lower() for kw in related_tech_keywords)
                        if not is_related:
                            logger.debug(f"Filtering out '{job.title}' ({job.platform}) - not related to tech/engineering")
                            continue
                    else:
                        logger.debug(f"Filtering out '{job.title}' ({job.platform}) - does not match active target role keywords: {active_roles}")
                        continue

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
            "target_platform": platform or (platforms[0] if platforms else None),
            "executed_providers": selected_providers,
            "total_fetched": len(all_discovered),
            "new_unique_jobs": newly_inserted,
            "qualified_matches": qualified_jobs,
            "threshold": prefs.match_threshold_percent,
            "auto_apply_enabled": prefs.auto_apply
        }

        logger.info(f"Discovery sweep completed: {newly_inserted} new unique jobs found, {qualified_jobs} qualified across {selected_providers}.")
        return summary

    async def _safely_fetch(self, provider, roles, locs, max_age):
        try:
            return await provider.fetch_recent_jobs(roles, locs, max_age)
        except Exception as e:
            logger.error(f"Provider {provider.name} failed during cycle: {e}")
            return []
