"""Unstop (formerly Dare2Compete) job and career opportunity provider.
Monitors tech, software engineering, hackathon, and early career hiring from top enterprises and startups in India and globally.
"""
import logging
import httpx
from typing import List
from datetime import datetime, timezone

from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus
from core.salary_parser import normalize_salary

logger = logging.getLogger(__name__)


class UnstopProvider(BaseJobProvider):
    API_URL = "https://unstop.com/api/public/opportunity/search-result?opportunity=jobs&per_page=30"

    def __init__(self):
        super().__init__(name="unstop")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "application/json"
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
                res = await client.get(self.API_URL)
                if res.status_code != 200:
                    logger.warning(f"Unstop API returned status {res.status_code}")
                    return results

                payload = res.json()
                opps = payload.get("data", {}).get("data", [])

                for item in opps:
                    title = (item.get("title") or "").strip()
                    org = item.get("organisation", {})
                    company = (org.get("name") if isinstance(org, dict) else str(org)) or "Unstop Partner"
                    seo_url = item.get("seo_url") or ""
                    url = f"https://unstop.com/{seo_url}" if seo_url and not seo_url.startswith("http") else (seo_url or f"https://unstop.com/o/{item.get('id')}")

                    if not title:
                        continue

                    job_detail = item.get("job_detail") or {}
                    raw_amount = item.get("payment_amount") or (job_detail.get("salary") if isinstance(job_detail, dict) else None)
                    loc = "India / Remote"
                    if isinstance(job_detail, dict) and job_detail.get("locations"):
                        loc_list = job_detail.get("locations")
                        if isinstance(loc_list, list) and loc_list:
                            loc = ", ".join(str(l) for l in loc_list[:2])

                    salary = normalize_salary(
                        explicit_val=str(raw_amount) if raw_amount else None,
                        fallback_text=f"{title} {raw_amount or ''}",
                        default_role_fallback=title
                    )

                    job_id = self.generate_job_id("unstop", company, title, url)
                    results.append(JobListing(
                        id=job_id,
                        platform="unstop",
                        title=title,
                        company=company,
                        location=loc,
                        url=url,
                        apply_url=url,
                        salary=salary,
                        is_easy_apply=True,
                        description=f"Unstop technology opportunity: {title} at {company}. Package: {salary}",
                        posted_at=datetime.now(timezone.utc),
                        discovered_at=datetime.now(timezone.utc),
                        status=ApplicationStatus.DISCOVERED,
                        metadata={"unstop_id": item.get("id"), "salary": salary}
                    ))

                    if len(results) >= 30:
                        break

        except Exception as e:
            logger.error(f"Error fetching Unstop jobs: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} active Unstop jobs")
        return results
