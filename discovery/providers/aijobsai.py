"""AI Jobs.ai generative AI, autonomous agent, and foundation models job provider.
Monitors cutting-edge AI engineering, RAG architects, and frontier LLM applications.
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


class AIJobsAIProvider(BaseJobProvider):
    SEARCH_URL = "https://aijobs.ai"

    def __init__(self):
        super().__init__(name="aijobsai")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml"
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
                    links = soup.find_all("a", href=True)
                    seen = set()

                    for a in links:
                        href = a.get("href", "")
                        if ("/job/" in href or "/jobs/" in href or "/position/" in href) and href not in seen:
                            seen.add(href)
                            title = a.get_text(strip=True)
                            if not title or len(title) < 5 or any(k in title.lower() for k in ["about", "pricing", "login", "post"]):
                                continue

                            url = href if href.startswith("http") else f"https://aijobs.ai{href}"
                            salary = normalize_salary(fallback_text=title, default_role_fallback=title)

                            job_id = self.generate_job_id("aijobsai", "AIJobs.ai Verified", title, url)
                            results.append(JobListing(
                                id=job_id,
                                platform="aijobsai",
                                title=title,
                                company="AIJobs.ai Verified",
                                location="Worldwide Remote",
                                url=url,
                                apply_url=url,
                                salary=salary,
                                is_easy_apply=True,
                                description=f"AIJobs.ai listing: {title}. Package: {salary}",
                                posted_at=datetime.now(timezone.utc),
                                discovered_at=datetime.now(timezone.utc),
                                status=ApplicationStatus.DISCOVERED,
                                metadata={"aijobsai": True, "salary": salary}
                            ))

                            if len(results) >= 20:
                                break

        except Exception as e:
            logger.debug(f"Live AIJobs.ai scrape encountered: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} active AIJobs.ai jobs")
        return results
