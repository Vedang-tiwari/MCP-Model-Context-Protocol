"""Indeed real-time job discovery provider using stealth browser rendering.
Scrapes fresh, sorted-by-date job postings directly from Indeed search without RSS feed dependencies.
"""
import logging
import urllib.parse
from typing import List
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus

logger = logging.getLogger(__name__)


class IndeedProvider(BaseJobProvider):
    SEARCH_BASE = "https://www.indeed.com/jobs"

    def __init__(self):
        super().__init__(name="indeed")

    async def fetch_recent_jobs(
        self,
        roles: List[str],
        locations: List[str],
        max_age_hours: int = 24
    ) -> List[JobListing]:
        results: List[JobListing] = []
        seen_urls = set()

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
                )
                page = await browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                )

                for role in roles[:2]:
                    for location in (locations[:1] if locations else ["Remote"]):
                        try:
                            params = urllib.parse.urlencode({
                                "q": role,
                                "l": location,
                                "sort": "date"
                            })
                            search_url = f"{self.SEARCH_BASE}?{params}"
                            await page.goto(search_url, timeout=25000, wait_until="domcontentloaded")
                            await page.wait_for_timeout(2000)

                            html = await page.content()
                            soup = BeautifulSoup(html, "html.parser")
                            cards = soup.select(".job_seen_beacon, td.resultContent, div.cardOutline")

                            for card in cards:
                                title_el = card.select_one("h2.jobTitle a, a[data-jk], a.jcs-JobTitle")
                                if not title_el:
                                    continue

                                title = title_el.get_text(strip=True)
                                jk = title_el.get("data-jk") or card.get("data-jk")
                                href = title_el.get("href", "")

                                if jk:
                                    job_url = f"https://www.indeed.com/viewjob?jk={jk}"
                                elif href.startswith("http"):
                                    job_url = href
                                elif href:
                                    job_url = f"https://www.indeed.com{href}"
                                else:
                                    continue

                                if job_url in seen_urls:
                                    continue
                                seen_urls.add(job_url)

                                comp_el = card.select_one("[data-testid='company-name'], .companyName, span.companyName")
                                company = comp_el.get_text(strip=True) if comp_el else "Employer on Indeed"

                                loc_el = card.select_one("[data-testid='text-location'], .companyLocation")
                                loc = loc_el.get_text(strip=True) if loc_el else location

                                snippet_el = card.select_one(".job-snippet, [data-testid='job-snippet']")
                                snippet = snippet_el.get_text(" ", strip=True) if snippet_el else f"{title} at {company}"

                                job_id = self.generate_job_id("indeed", company, title, job_url)

                                results.append(JobListing(
                                    id=job_id,
                                    platform="indeed",
                                    title=title,
                                    company=company,
                                    location=loc,
                                    url=job_url,
                                    apply_url=job_url,
                                    is_easy_apply=False,
                                    description=snippet[:800],
                                    posted_at=datetime.now(timezone.utc),
                                    discovered_at=datetime.now(timezone.utc),
                                    status=ApplicationStatus.DISCOVERED,
                                    metadata={"search_role": role, "search_location": location}
                                ))

                                if len(results) >= 40:
                                    break

                        except Exception as inner_e:
                            logger.debug(f"Indeed sweep for '{role}' encountered: {inner_e}")

                await browser.close()

        except Exception as e:
            logger.error(f"Error executing Indeed discovery: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} fresh Indeed jobs")
        return results
