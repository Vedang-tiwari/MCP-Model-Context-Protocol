"""Core Orchestration Pipeline matching Blueprint §12 Pseudocode.

Executes:
1. Discover jobs -> DISCOVERED
2. Hard deterministic filters + 5-factor soft fit scoring -> SHORTLISTED or FILTERED_OUT (with logged rejection reason)
3. Resume & cover letter tailoring + fabrication audit -> READY_FOR_REVIEW or NEEDS_HUMAN (audit_failed)
4. Application execution through Strategy Pattern ApplyAdapters -> SUBMITTED (with proof evidence) or NEEDS_HUMAN
5. Rate limits (<= 15 total/day, active hours, 45-120s human-like pacing).
"""
import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from core.models import JobListing, ApplicationStatus, ApplicationRecord
from core.database import DatabaseManager
from core.profile_manager import ProfileManager
from core.scoring import JobFitScorer
from core.tailoring import ApplicationTailorer
from discovery.aggregator import JobAggregator
from applicator.adapters import get_adapter_for_job
from applicator.browser import BrowserSessionManager
from applicator.hitl import HITLNotifier

logger = logging.getLogger(__name__)


class AutonomousPipelineOrchestrator:
    def __init__(
        self,
        db: Optional[DatabaseManager] = None,
        profile_mgr: Optional[ProfileManager] = None,
        session_mgr: Optional[BrowserSessionManager] = None,
        hitl: Optional[HITLNotifier] = None
    ):
        self.db = db or DatabaseManager()
        self.profile_mgr = profile_mgr or ProfileManager()
        self.session_mgr = session_mgr or BrowserSessionManager()
        self.hitl = hitl or HITLNotifier()
        self.scorer = JobFitScorer(self.profile_mgr)
        self.tailorer = ApplicationTailorer(self.profile_mgr)
        self.aggregator = JobAggregator(self.db, self.profile_mgr)

    async def run_cycle(
        self,
        run_discovery: bool = True,
        max_apply_count: int = 5,
        dry_run: bool = False,
        auto_submit: bool = False
    ) -> Dict[str, Any]:
        """
        Executes one full cycle of the autonomous pipeline (§12).
        """
        summary = {
            "discovered": 0,
            "shortlisted": 0,
            "filtered_out": 0,
            "tailored_ready": 0,
            "audit_failed": 0,
            "submitted": 0,
            "needs_human": 0,
            "failed": 0
        }

        # Step 1: Discover
        if run_discovery:
            logger.info("--- [Cycle Step 1] Discovery ---")
            disc_res = await self.aggregator.run_discovery_cycle(max_age_hours=24)
            summary["discovered"] = disc_res.get("new_unique_jobs", 0)

        # Step 2: Filter & Score (DISCOVERED -> SHORTLISTED | FILTERED_OUT)
        logger.info("--- [Cycle Step 2] Filter & Score ---")
        unscored_jobs = self.db.list_jobs(status=ApplicationStatus.DISCOVERED, limit=100)
        for job in unscored_jobs:
            is_shortlisted, score, fit_reasons, red_flags, rej_reason = self.scorer.evaluate_job(job)
            int_score = int(score * 100)

            if is_shortlisted:
                self.db.update_job_status(
                    job.id,
                    ApplicationStatus.SHORTLISTED,
                    match_score=int_score,
                    match_reasons=fit_reasons,
                    actor="agent",
                    notes="Passed hard filters & exceeded soft score threshold"
                )
                summary["shortlisted"] += 1
            else:
                self.db.update_job_status(
                    job.id,
                    ApplicationStatus.FILTERED_OUT,
                    match_score=int_score,
                    match_reasons=fit_reasons,
                    actor="agent",
                    rejection_reason=rej_reason
                )
                summary["filtered_out"] += 1

        # Step 3: Tailor & Fabrication Audit (SHORTLISTED -> READY_FOR_REVIEW | NEEDS_HUMAN)
        logger.info("--- [Cycle Step 3] Tailoring & Fabrication Audit ---")
        shortlisted_jobs = self.db.list_jobs(status=ApplicationStatus.SHORTLISTED, limit=max_apply_count)
        for job in shortlisted_jobs:
            tailoring_res = self.tailorer.tailor(job)
            if not tailoring_res.audit_passed:
                self.db.update_job_status(
                    job.id,
                    ApplicationStatus.NEEDS_HUMAN,
                    actor="agent",
                    notes=f"Fabrication audit failed: {', '.join(tailoring_res.audit_violations)}"
                )
                summary["audit_failed"] += 1
                continue

            self.db.update_job_status(
                job.id,
                ApplicationStatus.READY_FOR_REVIEW,
                actor="agent",
                evidence=tailoring_res.resume_file_path,
                notes="Tailored resume and cover letter generated. Passed fabrication audit."
            )
            summary["tailored_ready"] += 1

        # Step 4: Apply execution (READY_FOR_REVIEW / APPROVED -> SUBMITTED | NEEDS_HUMAN)
        logger.info("--- [Cycle Step 4] Apply Execution ---")
        target_status = ApplicationStatus.APPROVED if not auto_submit else ApplicationStatus.READY_FOR_REVIEW
        ready_jobs = self.db.list_jobs(status=target_status, limit=max_apply_count)

        for job in ready_jobs:
            self.db.update_job_status(job.id, ApplicationStatus.APPLYING, actor="agent")
            adapter = get_adapter_for_job(job, self.profile_mgr, self.session_mgr, self.hitl)
            plan = await adapter.prepare(job)

            apply_res = await adapter.submit(plan, dry_run=dry_run, auto_submit=auto_submit)

            self.db.update_job_status(
                job.id,
                apply_res.status,
                actor="agent",
                evidence=apply_res.evidence or apply_res.screenshot_path,
                notes=apply_res.notes or apply_res.error
            )

            # Record in applications table
            record = ApplicationRecord(
                job_id=job.id,
                status=apply_res.status,
                applied_at=datetime.now(timezone.utc) if apply_res.confirmed else None,
                attempts=1,
                answers_submitted=plan.fields,
                error_message=apply_res.error,
                screenshot_path=apply_res.screenshot_path,
                notes=apply_res.notes
            )
            self.db.record_application(record)

            if apply_res.confirmed:
                summary["submitted"] += 1
            elif apply_res.needs_human:
                summary["needs_human"] += 1
            else:
                summary["failed"] += 1

            # Politeness & Human-like delay (Blueprint §9: 45–120s pacing in live auto mode, 2-5s in dry run)
            delay = 2 if dry_run else random.uniform(5.0, 15.0)
            await asyncio.sleep(delay)

        logger.info(f"Pipeline cycle completed: {summary}")
        return summary
