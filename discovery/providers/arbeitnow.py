"""Arbeitnow job discovery provider via the official Arbeitnow JSON API.
Offers hundreds of European and international remote engineering and tech positions.
"""
import logging
import httpx
from typing import List
from datetime import datetime, timezone
from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus

logger = logging.getLogger(__name__)


class ArbeitnowProvider(BaseJobProvider):
    API_URL = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(self):
        super().__init__(name="arbeitnow")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }

    async def fetch_recent_jobs(
        self,
        roles: List[str],
        locations: List[str],
        max_age_hours: int = 24
    ) -> List[JobListing]:
        results: List[JobListing] = []

        # Keywords for matching engineering roles
        role_tokens = set()
        for r in roles:
            for token in r.lower().split():
                if len(token) > 2:
                    role_tokens.add(token)
        tech_anchors = {"engineer", "developer", "backend", "frontend", "fullstack", "software", "python", "devops", "cloud", "data", "ai", "ml"}

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=12.0, follow_redirects=True) as client:
                res = await client.get(self.API_URL)
                if res.status_code != 200:
                    logger.warning(f"Arbeitnow API returned status {res.status_code}")
                    return results

                data = res.json()
                raw_jobs = data.get("data", [])

                for item in raw_jobs:
                    title = item.get("title", "").strip()
                    company = item.get("company_name", "Tech Company").strip()
                    url = item.get("url", "")
                    if not (title and url):
                        continue

                    title_lower = title.lower()
                    tags = [t.lower() for t in item.get("tags", [])]

                    # Match roles
                    has_role_match = any(token in title_lower for token in role_tokens)
                    has_tech_match = any(a in title_lower for a in tech_anchors) or any(a in tags for a in tech_anchors)

                    if not (has_role_match or has_tech_match):
                        continue

                    location = "Remote" if item.get("remote") else (item.get("location") or "Hybrid/Remote")
                    desc = item.get("description", "")
                    clean_desc = (desc[:800] if desc else f"Opportunity for {title} at {company}")

                    job_id = self.generate_job_id("arbeitnow", company, title, url)

                    results.append(JobListing(
                        id=job_id,
                        platform="arbeitnow",
                        title=title,
                        company=company,
                        location=location,
                        url=url,
                        apply_url=url,
                        is_easy_apply=False,
                        description=clean_desc,
                        posted_at=datetime.now(timezone.utc),
                        discovered_at=datetime.now(timezone.utc),
                        status=ApplicationStatus.DISCOVERED,
                        metadata={
                            "remote": item.get("remote"),
                            "tags": tags[:5]
                        }
                    ))

                    if len(results) >= 60:
                        break

        except Exception as e:
            logger.error(f"Error fetching Arbeitnow jobs: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} active Arbeitnow jobs")
        return results
