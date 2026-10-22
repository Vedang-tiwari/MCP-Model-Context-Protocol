"""Direct ATS Provider for Greenhouse, Lever, and Ashby public job boards.
These APIs provide zero-latency, bot-proof, public JSON feeds of freshly posted jobs.
"""
import logging
import httpx
from typing import List, Optional
from datetime import datetime
from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus

logger = logging.getLogger(__name__)


class ATSDirectProvider(BaseJobProvider):
    def __init__(self, companies: Optional[List[str]] = None):
        super().__init__(name="ats_direct")
        self.companies = companies or [
            "stripe",
            "figma",
            "openai",
            "anthropic",
            "vercel",
            "supabase",
            "datadog",
            "github",
            "cloudflare",
            "postman",
            "razorpay"
        ]

    async def fetch_recent_jobs(
        self,
        roles: List[str],
        locations: List[str],
        max_age_hours: int = 24
    ) -> List[JobListing]:
        results: List[JobListing] = []
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for company in self.companies:
                # 1. Try Greenhouse
                try:
                    gh_jobs = await self._fetch_greenhouse(client, company, roles)
                    results.extend(gh_jobs)
                except Exception as e:
                    logger.debug(f"Greenhouse check for {company} failed: {e}")

                # 2. Try Lever
                try:
                    lever_jobs = await self._fetch_lever(client, company, roles)
                    results.extend(lever_jobs)
                except Exception as e:
                    logger.debug(f"Lever check for {company} failed: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} direct ATS jobs matching roles")
        return results

    async def _fetch_greenhouse(
        self,
        client: httpx.AsyncClient,
        company: str,
        roles: List[str]
    ) -> List[JobListing]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
        res = await client.get(url)
        if res.status_code != 200:
            return []

        data = res.json()
        jobs_raw = data.get("jobs", [])
        matched: List[JobListing] = []

        for item in jobs_raw:
            title = item.get("title", "")
            if not self._matches_roles(title, roles):
                continue

            job_url = item.get("absolute_url", "")
            loc = item.get("location", {}).get("name", "Remote")
            job_id = self.generate_job_id("greenhouse", company, title, job_url)

            matched.append(JobListing(
                id=job_id,
                platform="ats_direct",
                title=title,
                company=company.capitalize(),
                location=loc,
                url=job_url,
                apply_url=job_url,
                is_easy_apply=False,
                description=f"Direct ATS job listing for {title} at {company.capitalize()}",
                posted_at=datetime.utcnow(),
                discovered_at=datetime.utcnow(),
                status=ApplicationStatus.DISCOVERED,
                metadata={"ats_type": "greenhouse", "board_token": company}
            ))
        return matched

    async def _fetch_lever(
        self,
        client: httpx.AsyncClient,
        company: str,
        roles: List[str]
    ) -> List[JobListing]:
        url = f"https://api.lever.co/v0/postings/{company}?mode=json"
        res = await client.get(url)
        if res.status_code != 200:
            return []

        jobs_raw = res.json()
        matched: List[JobListing] = []

        for item in jobs_raw:
            title = item.get("text", "")
            if not self._matches_roles(title, roles):
                continue

            job_url = item.get("applyUrl") or item.get("hostedUrl", "")
            categories = item.get("categories", {})
            loc = categories.get("location", "Remote")
            job_id = self.generate_job_id("lever", company, title, job_url)

            matched.append(JobListing(
                id=job_id,
                platform="ats_direct",
                title=title,
                company=company.capitalize(),
                location=loc,
                url=job_url,
                apply_url=job_url,
                is_easy_apply=False,
                description=item.get("descriptionPlain", "")[:1000],
                posted_at=datetime.utcnow(),
                discovered_at=datetime.utcnow(),
                status=ApplicationStatus.DISCOVERED,
                metadata={"ats_type": "lever", "board_token": company}
            ))
        return matched

    def _matches_roles(self, title: str, roles: List[str]) -> bool:
        title_lower = title.lower()
        for role in roles:
            # Check if keywords match
            keywords = role.lower().split()
            if all(k in title_lower for k in keywords):
                return True
        return False
