"""Wellfound (formerly AngelList Talent) job discovery provider.
Focuses on high-growth tech startups and remote roles.
"""
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List
from datetime import datetime
from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus

logger = logging.getLogger(__name__)


class WellfoundProvider(BaseJobProvider):
    BASE_URL = "https://wellfound.com/jobs"

    def __init__(self):
        super().__init__(name="wellfound")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

    async def fetch_recent_jobs(
        self,
        roles: List[str],
        locations: List[str],
        max_age_hours: int = 24
    ) -> List[JobListing]:
        results: List[JobListing] = []

        async with httpx.AsyncClient(headers=self.headers, timeout=12.0) as client:
            for role in roles[:3]:
                try:
                    formatted_role = role.lower().replace(" ", "-")
                    url = f"https://wellfound.com/role/l/{formatted_role}"
                    res = await client.get(url)
                    if res.status_code != 200:
                        continue

                    soup = BeautifulSoup(res.text, "html.parser")
                    # Find job cards
                    job_elements = soup.select("[data-test='StartupResult'], .styles_result__")
                    for el in job_elements:
                        title_el = el.select_one("h2, a[href*='/jobs/']")
                        company_el = el.select_one("h3, .styles_name__")

                        if not title_el:
                            continue

                        title = title_el.get_text(strip=True)
                        company = company_el.get_text(strip=True) if company_el else "Startup"
                        link = title_el.get("href", "")
                        if not link.startswith("http"):
                            link = f"https://wellfound.com{link}"

                        job_id = self.generate_job_id("wellfound", company, title, link)

                        results.append(JobListing(
                            id=job_id,
                            platform="wellfound",
                            title=title,
                            company=company,
                            location="Remote",
                            url=link,
                            apply_url=link,
                            is_easy_apply=True,
                            description=f"Startup role at {company} for {title}",
                            posted_at=datetime.utcnow(),
                            discovered_at=datetime.utcnow(),
                            status=ApplicationStatus.DISCOVERED,
                            metadata={"role": role}
                        ))
                except Exception as e:
                    logger.debug(f"Wellfound check for {role} encountered: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} Wellfound jobs")
        return results
