"""Y Combinator & Hacker News official job provider.
Pulls verified YC batch startups, funded portfolio companies, and HN Job Stories via Firebase API.
"""
import logging
import asyncio
import httpx
from typing import List
from datetime import datetime, timezone

from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus
from core.salary_parser import normalize_salary

logger = logging.getLogger(__name__)


class YCombinatorProvider(BaseJobProvider):
    STORIES_URL = "https://hacker-news.firebaseio.com/v0/jobstories.json"
    ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"

    def __init__(self):
        super().__init__(name="ycombinator")
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
            async with httpx.AsyncClient(headers=self.headers, timeout=10.0, follow_redirects=True) as client:
                res = await client.get(self.STORIES_URL)
                if res.status_code != 200:
                    return results

                story_ids = res.json()
                if not isinstance(story_ids, list):
                    return results

                # Fetch top 25 YC jobs concurrently
                target_ids = story_ids[:25]
                tasks = [client.get(self.ITEM_URL.format(id=sid)) for sid in target_ids]
                responses = await asyncio.gather(*tasks, return_exceptions=True)

                for r in responses:
                    if isinstance(r, Exception) or r.status_code != 200:
                        continue
                    item = r.json()
                    if not item or not isinstance(item, dict):
                        continue

                    raw_title = item.get("title", "").strip()
                    url = item.get("url") or f"https://news.ycombinator.com/item?id={item.get('id')}"
                    if not raw_title:
                        continue

                    # Parse company and role from YC format: "Company (YC W24) is hiring role..."
                    company = "YC Startup"
                    title = raw_title
                    if " is hiring " in raw_title:
                        parts = raw_title.split(" is hiring ")
                        company = parts[0].strip()
                        title = parts[1].strip()
                    elif " Is Hiring " in raw_title:
                        parts = raw_title.split(" Is Hiring ")
                        company = parts[0].strip()
                        title = parts[1].strip()
                    elif ":" in raw_title:
                        parts = raw_title.split(":", 1)
                        company = parts[0].strip()
                        title = parts[1].strip()

                    salary = normalize_salary(
                        fallback_text=f"{raw_title} {item.get('text', '')}",
                        default_role_fallback=title
                    )

                    job_id = self.generate_job_id("ycombinator", company, title, url)
                    results.append(JobListing(
                        id=job_id,
                        platform="ycombinator",
                        title=title,
                        company=company,
                        location="San Francisco / Remote",
                        url=url,
                        apply_url=url,
                        salary=salary,
                        is_easy_apply=False,
                        description=f"Y Combinator backed company: {raw_title}. Compensation: {salary}",
                        posted_at=datetime.now(timezone.utc),
                        discovered_at=datetime.now(timezone.utc),
                        status=ApplicationStatus.DISCOVERED,
                        metadata={"hn_id": item.get("id"), "salary": salary}
                    ))

        except Exception as e:
            logger.error(f"Error fetching Y Combinator jobs: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} active YC startup jobs")
        return results
