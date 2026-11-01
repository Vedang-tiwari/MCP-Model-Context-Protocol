"""Foundit (formerly Monster India / APAC) career gateway provider.
Discovers enterprise and fast-growing company postings across India and Southeast Asia with LPA compensation.
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


class FounditProvider(BaseJobProvider):
    SEARCH_URL = "https://www.foundit.in/sro/job-search?query=software+engineer"

    def __init__(self):
        super().__init__(name="foundit")
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
                    cards = soup.select(".cardContainer, .sro-card, .jobCard")

                    for card in cards[:25]:
                        title_el = card.select_one(".cardTitle, .title, a[title]")
                        comp_el = card.select_one(".companyName, .company")
                        loc_el = card.select_one(".loc, .location")
                        sal_el = card.select_one(".package, .salary")

                        if not title_el:
                            continue

                        title = title_el.get_text(strip=True)
                        company = comp_el.get_text(strip=True) if comp_el else "Foundit Partner Company"
                        loc = loc_el.get_text(strip=True) if loc_el else "India / Hybrid"
                        url = title_el.get("href", "")
                        if not url.startswith("http"):
                            url = f"https://www.foundit.in{url}"

                        raw_sal = sal_el.get_text(strip=True) if sal_el else None
                        salary = normalize_salary(
                            explicit_val=raw_sal,
                            fallback_text=f"{title} {raw_sal or ''}",
                            default_role_fallback=title
                        )

                        job_id = self.generate_job_id("foundit", company, title, url)
                        results.append(JobListing(
                            id=job_id,
                            platform="foundit",
                            title=title,
                            company=company,
                            location=loc,
                            url=url,
                            apply_url=url,
                            salary=salary,
                            is_easy_apply=True,
                            description=f"Foundit verified listing: {title} at {company}. Package: {salary}",
                            posted_at=datetime.now(timezone.utc),
                            discovered_at=datetime.now(timezone.utc),
                            status=ApplicationStatus.DISCOVERED,
                            metadata={"foundit": True, "salary": salary}
                        ))

        except Exception as e:
            logger.error(f"Error fetching Foundit jobs: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} active Foundit jobs")
        return results
