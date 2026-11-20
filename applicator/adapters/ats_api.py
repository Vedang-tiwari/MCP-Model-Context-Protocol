"""ATS Direct Public API Adapter matching Blueprint §4.4 (Priority 1).

Handles Greenhouse, Lever, and Ashby public board APIs.
Prefers fast, clean HTTP submissions over brittle browser clicks whenever public endpoints exist.
"""
import logging
import httpx
from pathlib import Path
from typing import Optional, Any
from core.models import JobListing, ApplicationStatus
from core.profile_manager import ProfileManager
from .base import ApplyPlan, ApplyResult

logger = logging.getLogger(__name__)


class ATSAPIAdapter:
    def __init__(self, profile_mgr: ProfileManager):
        self.profile_mgr = profile_mgr

    def can_handle(self, job: JobListing) -> bool:
        url = (job.apply_url or job.url or "").lower()
        ats_type = job.metadata.get("ats_type", "")
        # Check if URL belongs to standard public ATS API platforms
        return (
            "boards-api.greenhouse.io" in url or
            "api.lever.co" in url or
            ats_type in ("greenhouse_api", "lever_api", "ashby_api")
        )

    async def prepare(self, job: JobListing, artifacts: Optional[Any] = None) -> ApplyPlan:
        p_yaml = self.profile_mgr.get_profile_yaml()
        identity = p_yaml.get("identity", {})
        names = identity.get("full_name", "").split()
        first_name = names[0] if names else ""
        last_name = " ".join(names[1:]) if len(names) > 1 else ""

        fields = {
            "first_name": first_name,
            "last_name": last_name,
            "email": identity.get("email", ""),
            "phone": identity.get("phone", ""),
            "location": identity.get("location", {}).get("city", ""),
            "linkedin": identity.get("links", {}).get("linkedin", ""),
            "github": identity.get("links", {}).get("github", "")
        }

        resume_path = getattr(artifacts, "resume_file_path", None)
        if not resume_path:
            p_resume = self.profile_mgr.get_resume_for_job(job)
            resume_path = str(p_resume) if p_resume and p_resume.exists() else None

        cover_letter = getattr(artifacts, "cover_letter", None)

        return ApplyPlan(
            job=job,
            adapter_name="ATSAPIAdapter",
            target_url=job.apply_url or job.url,
            fields=fields,
            resume_path=resume_path,
            cover_letter=cover_letter
        )

    async def submit(self, plan: ApplyPlan, *, dry_run: bool = False, auto_submit: bool = False) -> ApplyResult:
        if dry_run or not auto_submit:
            logger.info(f"[Dry Run / Review Mode] ATS API Plan prepared for {plan.job.title} at {plan.job.company}")
            return ApplyResult(
                job_id=plan.job.id,
                status=ApplicationStatus.READY_FOR_REVIEW,
                confirmed=False,
                needs_human=True,
                notes=f"ATS API submission payload prepared ({len(plan.fields)} fields mapped). Ready for review."
            )

        # Real API submission via httpx
        url = plan.target_url
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                data = {
                    "first_name": plan.fields.get("first_name"),
                    "last_name": plan.fields.get("last_name"),
                    "email": plan.fields.get("email"),
                    "phone": plan.fields.get("phone")
                }
                files = {}
                if plan.resume_path and Path(plan.resume_path).exists():
                    p = Path(plan.resume_path)
                    files["resume"] = (p.name, open(p, "rb"), "application/pdf")

                res = await client.post(url, data=data, files=files if files else None)
                if res.status_code in (200, 201):
                    evidence = f"HTTP {res.status_code} - API Confirmation: {res.text[:120]}"
                    return ApplyResult(
                        job_id=plan.job.id,
                        status=ApplicationStatus.SUBMITTED,
                        confirmed=True,
                        evidence=evidence,
                        notes="Submitted successfully via direct ATS API."
                    )
                else:
                    return ApplyResult(
                        job_id=plan.job.id,
                        status=ApplicationStatus.FAILED,
                        confirmed=False,
                        error=f"ATS API returned HTTP {res.status_code}: {res.text[:200]}"
                    )
        except Exception as e:
            logger.error(f"ATS API submission error: {e}")
            return ApplyResult(
                job_id=plan.job.id,
                status=ApplicationStatus.FAILED,
                confirmed=False,
                error=str(e)
            )
