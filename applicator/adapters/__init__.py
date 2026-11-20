"""Apply Adapters module implementing the Strategy Pattern (§4.4)."""
from .base import ApplyAdapter, ApplyPlan, ApplyResult
from .ats_api import ATSAPIAdapter
from .email_adapter import EmailAdapter
from .redirect_adapter import RedirectAdapter
from .browser_adapter import BrowserAdapter
from core.models import JobListing
from core.profile_manager import ProfileManager
from applicator.browser import BrowserSessionManager
from applicator.hitl import HITLNotifier


def get_adapter_for_job(
    job: JobListing,
    profile_mgr: ProfileManager,
    session_mgr: BrowserSessionManager,
    hitl: HITLNotifier
) -> ApplyAdapter:
    """
    Selects the most specific, reliable ApplyAdapter for a job listing
    following the priority order defined in Blueprint §4.4:
    1. Direct ATS API Adapter
    2. Email Adapter
    3. Browser Adapter (with integrated redirect following)
    """
    ats_adapter = ATSAPIAdapter(profile_mgr)
    if ats_adapter.can_handle(job):
        return ats_adapter

    email_adapter = EmailAdapter(profile_mgr)
    if email_adapter.can_handle(job):
        return email_adapter

    return BrowserAdapter(profile_mgr, session_mgr, hitl)


__all__ = [
    "ApplyAdapter",
    "ApplyPlan",
    "ApplyResult",
    "ATSAPIAdapter",
    "EmailAdapter",
    "RedirectAdapter",
    "BrowserAdapter",
    "get_adapter_for_job"
]
