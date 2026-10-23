"""RemoteOK job discovery provider via the official RemoteOK JSON API.
Provides instant real-time access to high-paying remote developer and startup jobs.
"""
import logging
import httpx
from typing import List, Optional
from datetime import datetime, timezone
from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus

logger = logging.getLogger(__name__)


class RemoteOKProvider(BaseJobProvider):
    API_URL = "https://remoteok.com/api"

    def __init__(self):
        super().__init__(name="remoteok")
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
        # Add general technical anchor tokens
        tech_anchors = {"engineer", "developer", "backend", "frontend", "fullstack", "software", "python", "devops", "cloud", "data", "ai", "ml"}

        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=15.0, follow_redirects=True) as client:
                res = await client.get(self.API_URL)
                if res.status_code != 200:
                    logger.warning(f"RemoteOK API returned status {res.status_code}")
                    return results

                items = res.json()
                if not isinstance(items, list):
                    return results

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    # Skip the legal disclaimer item
                    if "legal" in item and "position" not in item:
                        continue

                    title = item.get("position", "").strip()
                    company = item.get("company", "Remote Tech Company").strip()
                    if not title:
                        continue

                    title_lower = title.lower()
                    tags = [t.lower() for t in item.get("tags", [])]

                    # Match if title contains role tokens or technical anchors
                    has_role_match = any(token in title_lower for token in role_tokens)
                    has_tech_match = any(a in title_lower for a in tech_anchors) or any(a in tags for a in tech_anchors)

                    if not (has_role_match or has_tech_match):
                        continue

                    url = item.get("url") or item.get("apply_url") or f"https://remoteok.com/remote-jobs/{item.get('id', '')}"
                    apply_url = item.get("apply_url") or url
                    location = item.get("location") or "Remote"
                    raw_desc = item.get("description", "")
                    clean_desc = (raw_desc[:800] if raw_desc else f"Remote role for {title} at {company}")

                    job_id = self.generate_job_id("remoteok", company, title, url)

                    results.append(JobListing(
                        id=job_id,
                        platform="remoteok",
                        title=title,
                        company=company,
                        location=location,
                        url=url,
                        apply_url=apply_url,
                        is_easy_apply=False,
                        description=clean_desc,
                        posted_at=datetime.now(timezone.utc),
                        discovered_at=datetime.now(timezone.utc),
                        status=ApplicationStatus.DISCOVERED,
                        metadata={
                            "salary_min": item.get("salary_min"),
                            "salary_max": item.get("salary_max"),
                            "tags": tags[:6]
                        }
                    ))

        except Exception as e:
            logger.error(f"Error fetching RemoteOK jobs: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} active RemoteOK jobs")
        return results
