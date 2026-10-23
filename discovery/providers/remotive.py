"""Remotive job discovery provider via the official Remotive public JSON API.
Specializes in curated global remote software development, devops, and data engineering positions.
"""
import logging
import httpx
from typing import List
from datetime import datetime, timezone
from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus

logger = logging.getLogger(__name__)


class RemotiveProvider(BaseJobProvider):
    API_URL = "https://remotive.com/api/remote-jobs?category=software-dev&limit=40"

    def __init__(self):
        super().__init__(name="remotive")
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
                    logger.warning(f"Remotive API returned status {res.status_code}")
                    return results

                data = res.json()
                raw_jobs = data.get("jobs", [])

                for item in raw_jobs:
                    title = item.get("title", "").strip()
                    company = item.get("company_name", "Remote Company").strip()
                    url = item.get("url", "")
                    if not (title and url):
                        continue

                    location = item.get("candidate_required_location") or "Worldwide / Remote"
                    desc = item.get("description", "")
                    clean_desc = (desc[:800] if desc else f"Remotive job posting for {title} at {company}")

                    job_id = self.generate_job_id("remotive", company, title, url)

                    results.append(JobListing(
                        id=job_id,
                        platform="remotive",
                        title=title,
                        company=company,
                        location=location,
                        url=url,
                        apply_url=url,
                        is_easy_apply=False,
                        description=clean_desc,
                        posted_at=datetime.now(timezone.utc),
                        discovered_at=datetime.now(timezone.utc),
                        status=ApplicationStatus.DISCOVERED,
                        metadata={
                            "salary": item.get("salary"),
                            "job_type": item.get("job_type"),
                            "tags": item.get("tags", [])[:5]
                        }
                    ))

        except Exception as e:
            logger.error(f"Error fetching Remotive jobs: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} active Remotive jobs")
        return results
