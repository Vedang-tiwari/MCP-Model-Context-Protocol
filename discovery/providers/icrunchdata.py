"""iCrunchData analytics, big data, AI, and data engineering job provider.
Monitors high-value data science, analytics engineering, and machine learning positions.
"""
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List
from datetime import datetime, timezone

from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus
from core.salary_parser import normalize_salary

logger = logging.getLogger(__name__)


class ICrunchDataProvider(BaseJobProvider):
    SEARCH_URL = "https://icrunchdata.com/jobs"

    def __init__(self):
        super().__init__(name="icrunchdata")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml"
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
                res = await client.get(self.SEARCH_URL)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    links = soup.find_all("a", href=True)
                    seen = set()

                    for a in links:
                        href = a.get("href", "")
                        if ("/job/" in href or "/jobs/" in href) and href not in seen:
                            seen.add(href)
                            title = a.get_text(strip=True)
                            if not title or len(title) < 5 or any(skip in title.lower() for skip in ["post a job", "employer", "terms"]):
                                continue

                            url = href if href.startswith("http") else f"https://icrunchdata.com{href}"
                            salary = normalize_salary(fallback_text=title, default_role_fallback=title)

                            job_id = self.generate_job_id("icrunchdata", "iCrunchData Verified", title, url)
                            results.append(JobListing(
                                id=job_id,
                                platform="icrunchdata",
                                title=title,
                                company="iCrunchData Verified",
                                location="Remote / US / Global",
                                url=url,
                                apply_url=url,
                                salary=salary,
                                is_easy_apply=True,
                                description=f"iCrunchData role: {title}. Compensation: {salary}",
                                posted_at=datetime.now(timezone.utc),
                                discovered_at=datetime.now(timezone.utc),
                                status=ApplicationStatus.DISCOVERED,
                                metadata={"icrunchdata": True, "salary": salary}
                            ))

                            if len(results) >= 20:
                                break

        except Exception as e:
            logger.debug(f"Live iCrunchData scrape encountered: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} active iCrunchData jobs")
        return results
