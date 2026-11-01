"""Dev.to developer community jobs and opportunities provider.
Monitors verified developer, open-source, and developer advocacy roles.
"""
import logging
import httpx
from typing import List
from datetime import datetime, timezone

from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus
from core.salary_parser import normalize_salary

logger = logging.getLogger(__name__)


class DevToProvider(BaseJobProvider):
    API_URL = "https://dev.to/api/articles?tag=jobs&per_page=25"

    def __init__(self):
        super().__init__(name="devto")
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
            async with httpx.AsyncClient(headers=self.headers, timeout=10.0, follow_redirects=True) as client:
                res = await client.get(self.API_URL)
                if res.status_code != 200:
                    return results

                articles = res.json()
                if not isinstance(articles, list):
                    return results

                for item in articles:
                    title = (item.get("title") or "").strip()
                    user = item.get("user") or {}
                    org = item.get("organization") or {}
                    company = (org.get("name") if isinstance(org, dict) else None) or (user.get("name") if isinstance(user, dict) else "Dev Community")
                    url = item.get("url") or ""
                    if not (title and url):
                        continue

                    desc = item.get("description") or f"Developer role posted on Dev.to: {title}"
                    salary = normalize_salary(
                        fallback_text=f"{title} {desc}",
                        default_role_fallback=title
                    )

                    job_id = self.generate_job_id("devto", company, title, url)
                    results.append(JobListing(
                        id=job_id,
                        platform="devto",
                        title=title,
                        company=company,
                        location="Remote / Worldwide",
                        url=url,
                        apply_url=url,
                        salary=salary,
                        is_easy_apply=False,
                        description=f"{desc}. Compensation: {salary}",
                        posted_at=datetime.now(timezone.utc),
                        discovered_at=datetime.now(timezone.utc),
                        status=ApplicationStatus.DISCOVERED,
                        metadata={"tags": item.get("tag_list", [])[:4], "salary": salary}
                    ))

                    if len(results) >= 20:
                        break

        except Exception as e:
            logger.error(f"Error fetching Dev.to jobs: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} active Dev.to jobs")
        return results
