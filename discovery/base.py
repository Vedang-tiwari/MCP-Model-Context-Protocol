"""Abstract base class for all job discovery providers."""
import abc
import hashlib
from typing import List, Optional
from datetime import datetime
from core.models import JobListing


class BaseJobProvider(abc.ABC):
    def __init__(self, name: str):
        self.name = name

    @abc.abstractmethod
    async def fetch_recent_jobs(
        self,
        roles: List[str],
        locations: List[str],
        max_age_hours: int = 24
    ) -> List[JobListing]:
        """Fetch recently posted jobs from this platform."""
        pass

    def generate_job_id(self, platform: str, company: str, title: str, url: str) -> str:
        """Generates a deterministic unique hash for a job posting to prevent duplicate entries."""
        raw = f"{platform.lower()}_{company.lower().strip()}_{title.lower().strip()}_{url.strip()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
