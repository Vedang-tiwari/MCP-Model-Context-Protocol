"""Simplify Jobs provider via Simplify's curated tech and early-career repository index.
Provides high-signal software engineering, AI, and systems opportunities from top tech firms.
"""
import logging
import httpx
from typing import List
from datetime import datetime, timezone

from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus
from core.salary_parser import normalize_salary

logger = logging.getLogger(__name__)


class SimplifyJobsProvider(BaseJobProvider):
    DATA_URL = "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json"

    def __init__(self):
        super().__init__(name="simplify")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        }

    async def fetch_recent_jobs(
        self,
        roles: List[str],
        locations: List[str],
        max_age_hours: int = 24
    ) -> List[JobListing]:
        results: List[JobListing] = []

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=12.0, follow_redirects=True) as client:
                res = await client.get(self.DATA_URL)
                if res.status_code != 200:
                    return results

                listings = res.json()
                if not isinstance(listings, list):
                    return results

                for item in listings[:50]:
                    title = (item.get("title") or "Software Engineer").strip()
                    company = (item.get("company_name") or "Tech Enterprise").strip()
                    url = item.get("url") or ""
                    if not url:
                        continue

                    loc_raw = item.get("locations") or ["Remote"]
                    loc = ", ".join(loc_raw[:2]) if isinstance(loc_raw, list) else str(loc_raw)

                    salary = normalize_salary(
                        fallback_text=f"{title} {loc}",
                        default_role_fallback=title
                    )

                    job_id = self.generate_job_id("simplify", company, title, url)
                    results.append(JobListing(
                        id=job_id,
                        platform="simplify",
                        title=title,
                        company=company,
                        location=loc,
                        url=url,
                        apply_url=url,
                        salary=salary,
                        is_easy_apply=True,
                        description=f"Simplify Curated Position: {title} at {company}. Estimated Package: {salary}",
                        posted_at=datetime.now(timezone.utc),
                        discovered_at=datetime.now(timezone.utc),
                        status=ApplicationStatus.DISCOVERED,
                        metadata={"simplify_item": True, "salary": salary}
                    ))

                    if len(results) >= 30:
                        break

        except Exception as e:
            logger.error(f"Error fetching Simplify jobs: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} active Simplify jobs")
        return results
