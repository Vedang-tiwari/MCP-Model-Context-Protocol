"""Working Nomads job discovery provider via the official Working Nomads JSON API.
Specializes in curated global remote software development, devops, engineering, and data roles.
"""
import logging
import httpx
from typing import List
from datetime import datetime, timezone

from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus
from core.salary_parser import normalize_salary

logger = logging.getLogger(__name__)


class WorkingNomadsProvider(BaseJobProvider):
    API_URL = "https://www.workingnomads.com/api/exposed_jobs/"

    def __init__(self):
        super().__init__(name="workingnomads")
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
                    logger.warning(f"WorkingNomads API returned status {res.status_code}")
                    return results

                items = res.json()
                if not isinstance(items, list):
                    return results

                for item in items[:100]:
                    title = (item.get("title") or "").strip()
                    company = (item.get("company_name") or "Remote Employer").strip()
                    url = item.get("url") or item.get("apply_url") or ""
                    if not (title and url):
                        continue

                    title_lower = title.lower()
                    category = (item.get("category_name") or "").lower()
                    has_role_match = any(tok in title_lower for tok in role_tokens)
                    has_tech_match = any(a in title_lower or a in category for a in tech_anchors)

                    if not (has_role_match or has_tech_match):
                        continue

                    raw_sal = item.get("salary") or item.get("compensation")
                    salary = normalize_salary(
                        explicit_val=raw_sal,
                        fallback_text=f"{title} {item.get('description', '')[:300]}",
                        default_role_fallback=title
                    )

                    job_id = self.generate_job_id("workingnomads", company, title, url)
                    results.append(JobListing(
                        id=job_id,
                        platform="workingnomads",
                        title=title,
                        company=company,
                        location="Remote",
                        url=url,
                        apply_url=url,
                        salary=salary,
                        is_easy_apply=False,
                        description=(item.get("description") or f"Working Nomads role for {title} at {company}")[:800],
                        posted_at=datetime.now(timezone.utc),
                        discovered_at=datetime.now(timezone.utc),
                        status=ApplicationStatus.DISCOVERED,
                        metadata={"category": category, "salary": salary}
                    ))

                    if len(results) >= 40:
                        break

        except Exception as e:
            logger.error(f"Error fetching WorkingNomads jobs: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} active WorkingNomads jobs")
        return results
