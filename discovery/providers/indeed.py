"""Indeed real-time job discovery provider via RSS feeds.
RSS feeds sorted by date provide instant alerts for freshly published postings.
"""
import logging
import urllib.parse
import xml.etree.ElementTree as ET
import httpx
from typing import List
from datetime import datetime
from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus

logger = logging.getLogger(__name__)


class IndeedProvider(BaseJobProvider):
    BASE_RSS = "https://www.indeed.com/rss"

    def __init__(self):
        super().__init__(name="indeed")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
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
                for location in locations[:2]:
                    try:
                        params = {
                            "q": role,
                            "l": location,
                            "sort": "date"
                        }
                        res = await client.get(self.BASE_RSS, params=params)
                        if res.status_code != 200:
                            continue

                        # Parse RSS XML
                        root = ET.fromstring(res.text)
                        channel = root.find("channel")
                        if channel is None:
                            continue

                        for item in channel.findall("item"):
                            title_el = item.find("title")
                            link_el = item.find("link")
                            desc_el = item.find("description")
                            source_el = item.find("source")

                            if title_el is None or link_el is None:
                                continue

                            title = title_el.text or ""
                            url = link_el.text or ""
                            desc = desc_el.text or "" if desc_el is not None else ""
                            company = source_el.text if source_el is not None else "Company"

                            # Parse title / company if format is "Title - Company"
                            if " - " in title:
                                parts = title.split(" - ")
                                title = parts[0].strip()
                                company = parts[-1].strip()

                            job_id = self.generate_job_id("indeed", company, title, url)

                            results.append(JobListing(
                                id=job_id,
                                platform="indeed",
                                title=title,
                                company=company,
                                location=location,
                                url=url,
                                apply_url=url,
                                is_easy_apply=False,
                                description=desc[:800],
                                posted_at=datetime.utcnow(),
                                discovered_at=datetime.utcnow(),
                                status=ApplicationStatus.DISCOVERED,
                                metadata={"search_role": role, "search_location": location}
                            ))
                    except Exception as e:
                        logger.error(f"Error fetching Indeed RSS for {role}: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} recent Indeed jobs")
        return results
