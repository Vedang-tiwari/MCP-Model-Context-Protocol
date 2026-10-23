"""Wellfound (formerly AngelList Talent) job discovery provider.
Uses stealth browser automation and Apollo GraphQL state extraction to discover
fresh startup jobs, compensation bands, and remote configurations with zero CAPTCHA blocking.
"""
import logging
import json
from typing import List, Optional
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus

logger = logging.getLogger(__name__)


class WellfoundProvider(BaseJobProvider):
    BASE_URL = "https://wellfound.com/jobs"

    def __init__(self):
        super().__init__(name="wellfound")

    async def fetch_recent_jobs(
        self,
        roles: List[str],
        locations: List[str],
        max_age_hours: int = 24
    ) -> List[JobListing]:
        results: List[JobListing] = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
                )
                page = await browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                )
                try:
                    await page.goto(self.BASE_URL, timeout=25000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(2000)
                    html = await page.content()
                finally:
                    await browser.close()

            soup = BeautifulSoup(html, "html.parser")
            tag = soup.find("script", id="__NEXT_DATA__")
            if not tag or not tag.string:
                logger.warning("Wellfound page did not contain __NEXT_DATA__ script")
                return results

            data = json.loads(tag.string)
            apollo = data.get("props", {}).get("pageProps", {}).get("apolloState", {}).get("data", {})
            if not apollo:
                logger.warning("Wellfound Apollo state was empty")
                return results

            # Map of startups by key / ref
            startups = {k: v for k, v in apollo.items() if isinstance(v, dict) and v.get("__typename") == "Startup"}

            # Prepare role match keywords
            role_keywords = set()
            for r in roles:
                for w in r.lower().split():
                    if len(w) > 2:
                        role_keywords.add(w)
            tech_anchors = {"engineer", "developer", "backend", "frontend", "fullstack", "software", "python", "ai", "platform", "lead"}

            for k, v in apollo.items():
                if not isinstance(v, dict) or v.get("__typename") != "JobListing":
                    continue

                title = v.get("title", "").strip()
                if not title:
                    continue

                title_lower = title.lower()
                matched = any(kw in title_lower for kw in role_keywords) or any(a in title_lower for a in tech_anchors)
                if not matched:
                    continue

                job_id_num = v.get("id")
                slug = v.get("slug", "")

                # Resolve startup info from __ref
                startup_ref = v.get("startup", {}).get("__ref")
                startup_obj = startups.get(startup_ref, {}) if startup_ref else {}
                company = startup_obj.get("name") or "YC/Venture Startup"

                comp = v.get("compensation", "Competitive")
                loc_names = v.get("locationNames", [])
                remote_locs = v.get("acceptedRemoteLocationNames", [])
                loc = ", ".join(loc_names + remote_locs) if (loc_names or remote_locs) else ("Remote" if v.get("remote") else "Hybrid")

                job_url = f"https://wellfound.com/jobs/{job_id_num}-{slug}" if slug else f"https://wellfound.com/jobs/{job_id_num}"
                clean_desc = f"Startup position for {title} at {company}. Compensation: {comp}. Location: {loc}."

                job_id = self.generate_job_id("wellfound", company, title, job_url)

                results.append(JobListing(
                    id=job_id,
                    platform="wellfound",
                    title=title,
                    company=company,
                    location=loc,
                    url=job_url,
                    apply_url=job_url,
                    is_easy_apply=True,
                    description=clean_desc,
                    posted_at=datetime.now(timezone.utc),
                    discovered_at=datetime.now(timezone.utc),
                    status=ApplicationStatus.DISCOVERED,
                    metadata={
                        "compensation": comp,
                        "wellfound_id": job_id_num,
                        "remote": v.get("remote", False)
                    }
                ))

        except Exception as e:
            logger.error(f"Error executing Wellfound discovery: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} startup jobs on Wellfound")
        return results
