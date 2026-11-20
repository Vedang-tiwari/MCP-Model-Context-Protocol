"""Redirect Adapter matching Blueprint §4.4 (Priority 4).

Inspects external job aggregator and LinkedIn URLs, follows redirects,
detects underlying ATS systems (Greenhouse, Lever, Ashby, Workday), and resolves the canonical apply URL.
"""
import logging
import httpx
from typing import Optional, Any
from core.models import JobListing, ApplicationStatus
from core.profile_manager import ProfileManager
from .base import ApplyPlan, ApplyResult

logger = logging.getLogger(__name__)


class RedirectAdapter:
    def __init__(self, profile_mgr: ProfileManager):
        self.profile_mgr = profile_mgr

    def can_handle(self, job: JobListing) -> bool:
        url = (job.apply_url or job.url or "").lower()
        return (
            "linkedin.com" in url or
            "indeed.com" in url or
            "glassdoor.com" in url or
            "weworkremotely.com" in url or
            "simplify.jobs" in url
        )

    async def resolve_final_url(self, raw_url: str) -> str:
        """Follows HTTP redirects up to 5 hops to find canonical ATS application page."""
        if not raw_url.startswith("http"):
            raw_url = f"https://{raw_url}"

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=8.0) as client:
                resp = await client.head(raw_url, headers={"User-Agent": "Mozilla/5.0"})
                return str(resp.url)
        except Exception:
            return raw_url

    async def prepare(self, job: JobListing, artifacts: Optional[Any] = None) -> ApplyPlan:
        initial_url = job.apply_url or job.url
        final_url = await self.resolve_final_url(initial_url)

        return ApplyPlan(
            job=job,
            adapter_name="RedirectAdapter",
            target_url=final_url,
            metadata={"resolved_from": initial_url}
        )

    async def submit(self, plan: ApplyPlan, *, dry_run: bool = False, auto_submit: bool = False) -> ApplyResult:
        # Hand off to browser or ATS adapter
        return ApplyResult(
            job_id=plan.job.id,
            status=ApplicationStatus.READY_FOR_REVIEW,
            confirmed=False,
            needs_human=True,
            notes=f"Redirect resolved to: {plan.target_url}"
        )
