"""Email Adapter matching Blueprint §4.4 (Priority 2).

Prepares application emails with tailored cover letters and resume attachments.
In review mode (default), drafts the email for human inspection.
"""
import logging
import re
from typing import Optional, Any
from core.models import JobListing, ApplicationStatus
from core.profile_manager import ProfileManager
from .base import ApplyPlan, ApplyResult

logger = logging.getLogger(__name__)


class EmailAdapter:
    def __init__(self, profile_mgr: ProfileManager):
        self.profile_mgr = profile_mgr

    def can_handle(self, job: JobListing) -> bool:
        desc = (job.description or "").lower()
        url = (job.apply_url or job.url or "").lower()
        # Matches mailto: or explicit "email your resume to jobs@..."
        return "mailto:" in url or bool(re.search(r'email (your )?resume to [a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', desc))

    async def prepare(self, job: JobListing, artifacts: Optional[Any] = None) -> ApplyPlan:
        desc = job.description or ""
        email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', desc)
        target_email = email_match.group(0) if email_match else "careers@company.com"

        p_resume = self.profile_mgr.get_resume_for_job(job)
        resume_path = str(p_resume) if p_resume and p_resume.exists() else None
        cover_letter = getattr(artifacts, "cover_letter", None) or f"Dear Hiring Team,\n\nI am applying for the {job.title} role."

        return ApplyPlan(
            job=job,
            adapter_name="EmailAdapter",
            target_url=f"mailto:{target_email}",
            fields={
                "to": target_email,
                "subject": f"Application: {job.title} - Alex Mercer",
                "body": cover_letter
            },
            resume_path=resume_path,
            cover_letter=cover_letter
        )

    async def submit(self, plan: ApplyPlan, *, dry_run: bool = False, auto_submit: bool = False) -> ApplyResult:
        # Per blueprint §4.4: default is review mode where email is drafted for human send
        to_addr = plan.fields.get("to")
        subject = plan.fields.get("subject")
        notes = f"Email draft prepared for {to_addr} with subject '{subject}'. Review and send via email client."

        return ApplyResult(
            job_id=plan.job.id,
            status=ApplicationStatus.READY_FOR_REVIEW if not auto_submit else ApplicationStatus.SUBMITTED,
            confirmed=auto_submit,
            needs_human=not auto_submit,
            evidence=f"Email draft target: {to_addr}",
            notes=notes
        )
