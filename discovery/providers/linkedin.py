"""LinkedIn real-time guest job search provider.
Polls recently posted jobs (past 24h) via public guest endpoints without risking account credentials.
"""
import logging
import urllib.parse
import httpx
from bs4 import BeautifulSoup
from typing import List, Optional
from datetime import datetime
from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus

logger = logging.getLogger(__name__)


class LinkedInProvider(BaseJobProvider):
    BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    def __init__(self):
        super().__init__(name="linkedin")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def fetch_recent_jobs(
        self,
        roles: List[str],
        locations: List[str],
        max_age_hours: int = 24
    ) -> List[JobListing]:
        results: List[JobListing] = []
        # Filter: past 24 hours (r86400) or past 1 hour (r3600)
        time_filter = "r3600" if max_age_hours <= 1 else "r86400"

        async with httpx.AsyncClient(headers=self.headers, timeout=12.0) as client:
            for role in roles[:4]:  # Prioritize top target roles
                for location in locations[:2]:
                    try:
                        params = {
                            "keywords": role,
                            "location": location,
                            "f_TPR": time_filter,
                            "start": 0
                        }
                        res = await client.get(self.BASE_URL, params=params)
                        if res.status_code != 200:
                            logger.warning(f"LinkedIn search returned status {res.status_code} for {role}")
                            continue

                        soup = BeautifulSoup(res.text, "html.parser")
                        cards = soup.select("li")
                        for card in cards:
                            title_el = card.select_one(".base-search-card__title")
                            company_el = card.select_one(".base-search-card__subtitle")
                            link_el = card.select_one("a.base-card__full-link")
                            loc_el = card.select_one(".job-search-card__location")

                            if not (title_el and link_el):
                                continue

                            title = title_el.get_text(strip=True)
                            company = company_el.get_text(strip=True) if company_el else "Unknown"
                            loc = loc_el.get_text(strip=True) if loc_el else location
                            job_url = link_el.get("href", "").split("?")[0]

                            job_id = self.generate_job_id("linkedin", company, title, job_url)

                            results.append(JobListing(
                                id=job_id,
                                platform="linkedin",
                                title=title,
                                company=company,
                                location=loc,
                                url=job_url,
                                apply_url=job_url,
                                is_easy_apply=True,
                                description=f"LinkedIn posting for {title} at {company}",
                                posted_at=datetime.utcnow(),
                                discovered_at=datetime.utcnow(),
                                status=ApplicationStatus.DISCOVERED,
                                metadata={"search_role": role, "search_location": location}
                            ))
                    except Exception as e:
                        logger.error(f"Error fetching LinkedIn jobs for {role}: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} recent LinkedIn jobs")
        return results
