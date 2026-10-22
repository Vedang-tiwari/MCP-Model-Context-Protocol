"""Internshala, Unstop, and Early-Career Job Provider.
Monitors junior developer roles, graduate developer positions, and early-career tech jobs.
"""
import logging
import httpx
from bs4 import BeautifulSoup
from typing import List
from datetime import datetime
from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus

logger = logging.getLogger(__name__)


class InternshalaProvider(BaseJobProvider):
    BASE_URL = "https://internshala.com/jobs"

    def __init__(self):
        super().__init__(name="internshala")
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

        async with httpx.AsyncClient(headers=self.headers, timeout=12.0) as client:
            for role in roles[:2]:
                try:
                    formatted_role = role.lower().replace(" ", "-")
                    url = f"{self.BASE_URL}/{formatted_role}-jobs"
                    res = await client.get(url)
                    if res.status_code != 200:
                        continue

                    soup = BeautifulSoup(res.text, "html.parser")
                    cards = soup.select(".individual_internship")

                    for card in cards:
                        title_el = card.select_one(".job-internship-name, .profile a")
                        company_el = card.select_one(".company-name, .company_name a")
                        loc_el = card.select_one(".row-1-item.locations span, #location_names a")

                        if not (title_el and company_el):
                            continue

                        title = title_el.get_text(strip=True)
                        company = company_el.get_text(strip=True)
                        loc = loc_el.get_text(strip=True) if loc_el else "Remote"
                        href = title_el.get("href", "")
                        if not href.startswith("http"):
                            href = f"https://internshala.com{href}"

                        job_id = self.generate_job_id("internshala", company, title, href)

                        results.append(JobListing(
                            id=job_id,
                            platform="internshala",
                            title=title,
                            company=company,
                            location=loc,
                            url=href,
                            apply_url=href,
                            is_easy_apply=True,
                            description=f"Internshala opportunity for {title} at {company}",
                            posted_at=datetime.utcnow(),
                            discovered_at=datetime.utcnow(),
                            status=ApplicationStatus.DISCOVERED,
                            metadata={"role": role}
                        ))
                except Exception as e:
                    logger.debug(f"Internshala search for {role} encountered: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} Internshala jobs")
        return results
