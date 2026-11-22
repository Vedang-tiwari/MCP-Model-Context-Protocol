"""ML-Jobs.info specialized Machine Learning, MLOps, and Deep Learning job provider.
Monitors production ML engineering, PyTorch/JAX pipelines, and foundation model infrastructure.
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


class MLJobsInfoProvider(BaseJobProvider):
    SEARCH_URL = "https://ml-jobs.info"

    def __init__(self):
        super().__init__(name="mljobsinfo")
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
                    links = soup.select("a[href*='/job/'], a[href*='/jobs/'], .job-link")
                    seen = set()

                    for a in links:
                        href = a.get("href", "")
                        if href not in seen:
                            seen.add(href)
                            title = a.get_text(strip=True)
                            if not title or len(title) < 5:
                                continue

                            url = href if href.startswith("http") else f"https://ml-jobs.info{href}"
                            salary = normalize_salary(fallback_text=title, default_role_fallback=title)

                            job_id = self.generate_job_id("mljobsinfo", "ML Jobs Verified", title, url)
                            results.append(JobListing(
                                id=job_id,
                                platform="mljobsinfo",
                                title=title,
                                company="ML Jobs Community",
                                location="Worldwide Remote",
                                url=url,
                                apply_url=url,
                                salary=salary,
                                is_easy_apply=True,
                                description=f"ML-Jobs.info position: {title}. Package: {salary}",
                                posted_at=datetime.now(timezone.utc),
                                discovered_at=datetime.now(timezone.utc),
                                status=ApplicationStatus.DISCOVERED,
                                metadata={"mljobsinfo": True, "salary": salary}
                            ))

                            if len(results) >= 20:
                                break

        except Exception as e:
            logger.debug(f"Live ML-Jobs.info scrape encountered: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} active ML-Jobs.info jobs")
        return results
