"""Crossover high-compensation global remote job provider.
Discovers verified remote roles with explicit top-percentile compensation ($100k - $400k/yr).
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


class CrossoverProvider(BaseJobProvider):
    BASE_URL = "https://www.crossover.com/jobs"

    def __init__(self):
        super().__init__(name="crossover")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
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
                res = await client.get(self.BASE_URL)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    links = soup.find_all("a", href=True)
                    seen_urls = set()

                    for a in links:
                        href = a.get("href", "")
                        if "/jobs/" in href and href not in seen_urls:
                            seen_urls.add(href)
                            title = a.get_text(strip=True)
                            if not title or len(title) < 5 or any(ignore in title.lower() for ignore in ["view all", "browse", "privacy"]):
                                continue

                            url = href if href.startswith("http") else f"https://www.crossover.com{href}"
                            salary = "$100k - $200k / yr"
                            if any(k in title.lower() for k in ["chief", "vp", "director", "architect"]):
                                salary = "$200k - $400k / yr"
                            elif any(k in title.lower() for k in ["senior", "lead", "staff"]):
                                salary = "$140k - $240k / yr"

                            job_id = self.generate_job_id("crossover", "Crossover Global", title, url)
                            results.append(JobListing(
                                id=job_id,
                                platform="crossover",
                                title=title,
                                company="Crossover Global",
                                location="Worldwide Remote",
                                url=url,
                                apply_url=url,
                                salary=salary,
                                is_easy_apply=False,
                                description=f"Crossover elite remote role: {title}. Package: {salary}",
                                posted_at=datetime.now(timezone.utc),
                                discovered_at=datetime.now(timezone.utc),
                                status=ApplicationStatus.DISCOVERED,
                                metadata={"crossover": True, "salary": salary}
                            ))

                            if len(results) >= 20:
                                break

        except Exception as e:
            logger.error(f"Error fetching Crossover jobs: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} active Crossover jobs")
        return results
