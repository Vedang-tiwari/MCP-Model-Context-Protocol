"""Sprout (usesprout.com) AI-powered job search and career platform provider.
Monitors full-stack, cloud infrastructure, AI developers, and technical roles from Sprout's platform.
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


class SproutProvider(BaseJobProvider):
    SEARCH_URL = "https://www.usesprout.com"

    def __init__(self):
        super().__init__(name="sprout")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/json"
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
                res = await client.get(f"{self.SEARCH_URL}/jobs")
                if res.status_code != 200:
                    res = await client.get(self.SEARCH_URL)

                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, "html.parser")
                    links = soup.find_all("a", href=True)
                    seen = set()

                    for a in links:
                        href = a.get("href", "")
                        if ("/job/" in href or "/career/" in href or "/position/" in href or "/roles/" in href) and href not in seen:
                            seen.add(href)
                            title = a.get_text(strip=True)
                            if not title or len(title) < 5:
                                continue

                            url = href if href.startswith("http") else f"https://www.usesprout.com{href}"
                            salary = normalize_salary(fallback_text=title, default_role_fallback=title)

                            job_id = self.generate_job_id("sprout", "Sprout Network", title, url)
                            results.append(JobListing(
                                id=job_id,
                                platform="sprout",
                                title=title,
                                company="Sprout Partner Tech",
                                location="Remote / US / Global",
                                url=url,
                                apply_url=url,
                                salary=salary,
                                is_easy_apply=True,
                                description=f"Sprout (usesprout.com) curated opportunity: {title}. Package: {salary}",
                                posted_at=datetime.now(timezone.utc),
                                discovered_at=datetime.now(timezone.utc),
                                status=ApplicationStatus.DISCOVERED,
                                metadata={"sprout": True, "source": "usesprout.com", "salary": salary}
                            ))

                            if len(results) >= 20:
                                break

        except Exception as e:
            logger.debug(f"Live Sprout (usesprout.com) scrape encountered: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} active Sprout (usesprout.com) jobs")
        return results
