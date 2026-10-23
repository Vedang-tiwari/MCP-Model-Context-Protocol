"""Direct ATS Provider for Greenhouse and Lever public job feeds.
Provides zero-latency, bot-proof, public JSON feeds of freshly posted jobs across top tech companies.
"""
import logging
import httpx
from typing import List, Optional
from datetime import datetime, timezone
from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus

logger = logging.getLogger(__name__)


class ATSDirectProvider(BaseJobProvider):
    def __init__(self, companies: Optional[List[str]] = None):
        super().__init__(name="ats_direct")
        self.companies = companies or [
            "datadog",
            "stripe",
            "figma",
            "openai",
            "anthropic",
            "vercel",
            "supabase",
            "cloudflare",
            "postman",
            "github",
            "discord",
            "canva",
            "retool",
            "linear",
            "zapier",
            "gitlab",
            "docker",
            "reddit",
            "pinterest",
            "twitch",
            "instacart",
            "snowflake",
            "databricks",
            "brex",
            "ramp",
            "gusto",
            "affirm",
            "sentry",
            "hashicorp",
            "doordash",
            "robinhood",
            "coinbase",
            "mongodb",
            "elastic"
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
                # 1. Greenhouse
                try:
                    gh_jobs = await self._fetch_greenhouse(client, company, roles)
                    results.extend(gh_jobs)
                except Exception as e:
                    logger.debug(f"Greenhouse check for {company} encountered: {e}")

                # 2. Lever
                try:
                    lever_jobs = await self._fetch_lever(client, company, roles)
                    results.extend(lever_jobs)
                except Exception as e:
                    logger.debug(f"Lever check for {company} encountered: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} direct ATS jobs across tech leaders")
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
                posted_at=datetime.now(timezone.utc),
                discovered_at=datetime.now(timezone.utc),
                status=ApplicationStatus.DISCOVERED,
                metadata={"ats_type": "greenhouse", "board_token": company}
            ))

            if len(matched) >= 30:  # Cap per company to keep balance
                break

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
        if not isinstance(jobs_raw, list):
            return []

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
                description=item.get("descriptionPlain", "")[:800],
                posted_at=datetime.now(timezone.utc),
                discovered_at=datetime.now(timezone.utc),
                status=ApplicationStatus.DISCOVERED,
                metadata={"ats_type": "lever", "board_token": company}
            ))

            if len(matched) >= 30:
                break

        return matched

    def _matches_roles(self, title: str, roles: List[str]) -> bool:
        t = title.lower().replace("-", " ")

        for role in roles:
            # Token match with developer/engineer equivalence
            tokens = [tok for tok in role.lower().split() if len(tok) > 2]
            if all(tok in t for tok in tokens):
                return True

            equiv_tokens = set(tokens)
            if "developer" in equiv_tokens:
                equiv_tokens.discard("developer")
                equiv_tokens.add("engineer")
            elif "engineer" in equiv_tokens:
                equiv_tokens.discard("engineer")
                equiv_tokens.add("developer")

            if all(tok in t for tok in equiv_tokens):
                return True

        # General tech stems matching
        tech_stems = [
            "software engineer", "frontend", "backend", "full stack",
            "fullstack", "devops", "platform engineer", "data engineer",
            "machine learning", "ai engineer", "systems engineer"
        ]
        return any(stem in t for stem in tech_stems)
