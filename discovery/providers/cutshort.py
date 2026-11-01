"""Cutshort Indian tech startup and high-growth company job provider.
Monitors product engineers, backend developers, and AI talent opportunities with LPA CTC packages.
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


class CutshortProvider(BaseJobProvider):
    SEARCH_URL = "https://cutshort.io/jobs/software-engineer-jobs"

    def __init__(self):
        super().__init__(name="cutshort")
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
                res = await client.get(self.SEARCH_URL)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    links = soup.find_all("a", href=True)
                    seen = set()

                    for a in links:
                        href = a.get("href", "")
                        if "/job/" in href and href not in seen:
                            seen.add(href)
                            title = a.get_text(strip=True)
                            if not title or len(title) < 4:
                                continue

                            url = href if href.startswith("http") else f"https://cutshort.io{href}"
                            salary = normalize_salary(fallback_text=title, default_role_fallback=title)

                            job_id = self.generate_job_id("cutshort", "Indian Tech Startup", title, url)
                            results.append(JobListing(
                                id=job_id,
                                platform="cutshort",
                                title=title,
                                company="Indian Tech Startup",
                                location="Bengaluru / Remote",
                                url=url,
                                apply_url=url,
                                salary=salary,
                                is_easy_apply=True,
                                description=f"Cutshort verified tech opportunity: {title}. Package: {salary}",
                                posted_at=datetime.now(timezone.utc),
                                discovered_at=datetime.now(timezone.utc),
                                status=ApplicationStatus.DISCOVERED,
                                metadata={"cutshort": True, "salary": salary}
                            ))

                            if len(results) >= 20:
                                break

        except Exception as e:
            logger.error(f"Error fetching Cutshort jobs: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} active Cutshort jobs")
        return results
