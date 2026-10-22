"""Naukri & Indian tech ecosystem job provider.
Monitors recent engineering postings across Indian tech hubs (Bengaluru, Hyderabad, Pune, Gurgaon, Remote).
"""
import logging
import urllib.parse
import httpx
from typing import List
from datetime import datetime
from discovery.base import BaseJobProvider
from core.models import JobListing, ApplicationStatus

logger = logging.getLogger(__name__)


class NaukriProvider(BaseJobProvider):
    # Naukri public gateway search endpoint
    SEARCH_ENDPOINT = "https://www.naukri.com/jobapi/v3/search"

    def __init__(self):
        super().__init__(name="naukri")
        self.headers = {
            "appid": "109",
            "systemid": "Naukri",
            "clientid": "d3419644-8d48-4cb1-86a1-026d36e2f694",
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

        async with httpx.AsyncClient(headers=self.headers, timeout=12.0) as client:
            for role in roles[:3]:
                for location in locations[:2]:
                    try:
                        params = {
                            "noOfResults": 15,
                            "urlType": "search_by_keyword",
                            "searchType": "adv",
                            "keyword": role,
                            "location": location,
                            "sortType": "freshness"
                        }
                        res = await client.get(self.SEARCH_ENDPOINT, params=params)
                        if res.status_code != 200:
                            continue

                        data = res.json()
                        job_details = data.get("jobDetails", [])

                        for item in job_details:
                            title = item.get("title", "")
                            company = item.get("companyName", "Tech Employer")
                            job_id_raw = item.get("jobId", "")
                            url = f"https://www.naukri.com/job-listings-{job_id_raw}" if job_id_raw else item.get("jdURL", "")
                            desc = item.get("jobDescription", "")
                            loc = ", ".join(item.get("placeholders", [{}])[0].get("label", location).split(","))

                            job_id = self.generate_job_id("naukri", company, title, url)

                            results.append(JobListing(
                                id=job_id,
                                platform="naukri",
                                title=title,
                                company=company,
                                location=loc,
                                url=url,
                                apply_url=url,
                                is_easy_apply=True,
                                description=desc[:800],
                                posted_at=datetime.utcnow(),
                                discovered_at=datetime.utcnow(),
                                status=ApplicationStatus.DISCOVERED,
                                metadata={"job_id_raw": job_id_raw}
                            ))
                    except Exception as e:
                        logger.debug(f"Naukri search for {role} encountered: {e}")

        logger.info(f"[{self.name}] Discovered {len(results)} Naukri jobs")
        return results
