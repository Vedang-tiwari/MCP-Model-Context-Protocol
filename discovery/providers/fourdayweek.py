"""4dayweek job discovery provider via the official 4dayweek.io JSON API.
Specializes in 32-hour work week, high-paying tech and software development roles.
"""
import logging
import httpx
from typing import List
from datetime import datetime, timezone

from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus
from core.salary_parser import normalize_salary

logger = logging.getLogger(__name__)


class FourDayWeekProvider(BaseJobProvider):
    API_URL = "https://4dayweek.io/api/jobs"

    def __init__(self):
        super().__init__(name="4dayweek")
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
                    logger.warning(f"4dayweek API returned status {res.status_code}")
                    return results

                data = res.json()
                raw_jobs = data.get("jobs", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])

                for item in raw_jobs:
                    title = (item.get("title") or "").strip()
                    company = (item.get("company") or "Remote Company").strip()
                    url = item.get("url") or item.get("apply_url") or ""
                    if not (title and url):
                        continue

                    raw_sal = item.get("salary") or item.get("compensation")
                    salary = normalize_salary(
                        explicit_val=str(raw_sal) if raw_sal else None,
                        fallback_text=f"{title} {raw_sal or ''}",
                        default_role_fallback=title
                    )

                    job_id = self.generate_job_id("4dayweek", company, title, url)
                    results.append(JobListing(
                        id=job_id,
                        platform="4dayweek",
                        title=title,
                        company=company,
                        location=item.get("location") or "Remote / 4-Day Workweek",
                        url=url,
                        apply_url=url,
                        salary=salary,
                        is_easy_apply=False,
                        description=f"4-day workweek position: {title} at {company}. Compensation: {salary}",
                        posted_at=datetime.now(timezone.utc),
                        discovered_at=datetime.now(timezone.utc),
                        status=ApplicationStatus.DISCOVERED,
                        metadata={"workweek": "32h", "salary": salary}
                    ))

                    if len(results) >= 30:
                        break

        except Exception as e:
            logger.error(f"Error fetching 4dayweek jobs: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} active 4dayweek jobs")
        return results
