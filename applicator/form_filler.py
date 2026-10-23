"""Autonomous Form Filler for standard ATS portals (Greenhouse, Lever) and Easy Apply flows."""
import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from playwright.async_api import Page

from core.models import JobListing, ApplicationStatus, ApplicationRecord
from core.database import DatabaseManager
from core.profile_manager import ProfileManager
from .browser import BrowserSessionManager
from .screening_solver import ScreeningQuestionSolver
from .hitl import HITLNotifier

logger = logging.getLogger(__name__)


class ApplicationAgent:
    def __init__(
        self,
        db: DatabaseManager,
        profile_mgr: ProfileManager,
        session_mgr: BrowserSessionManager,
        hitl: HITLNotifier
    ):
        self.db = db
        self.profile_mgr = profile_mgr
        self.session_mgr = session_mgr
        self.hitl = hitl
        self.solver = ScreeningQuestionSolver(profile_mgr)
        self.screenshots_dir = Path("data/screenshots")
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    async def apply(self, job: JobListing, auto_submit: bool = False) -> ApplicationRecord:
        """
        Executes the automated application workflow for a given job.
        If auto_submit is False, fills out the form and stops at the final review step for user verification.
        """
        logger.info(f"Initiating application workflow for '{job.title}' at '{job.company}' ({job.url})")
        self.db.update_job_status(job.id, ApplicationStatus.APPLYING)

        context = await self.session_mgr.start()
        page = await context.new_page()

        record = ApplicationRecord(
            job_id=job.id,
            status=ApplicationStatus.APPLYING,
            applied_at=None,
            attempts=1,
            answers_submitted={}
        )

        try:
            # Navigate to application URL
            target_url = job.apply_url or job.url
            await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # Check for bot detection / CAPTCHA
            if await self._detect_captcha(page):
                await self.hitl.notify_human_action_required(
                    reason="CAPTCHA or Bot Detection encountered",
                    job_title=job.title,
                    company=job.company,
                    url=target_url
                )
                # Wait 60 seconds for manual resolution
                await asyncio.sleep(60)

            # Determine application flow based on platform / ATS
            if "greenhouse.io" in target_url or job.metadata.get("ats_type") == "greenhouse":
                record = await self._fill_greenhouse(page, job, auto_submit)
            elif "lever.co" in target_url or job.metadata.get("ats_type") == "lever":
                record = await self._fill_lever(page, job, auto_submit)
            elif "linkedin.com" in target_url:
                record = await self._fill_linkedin_easy_apply(page, job, auto_submit)
            else:
                record = await self._fill_generic_form(page, job, auto_submit)

            # Capture screenshot evidence
            screenshot_file = str(self.screenshots_dir / f"job_{job.id}.png")
            await page.screenshot(path=screenshot_file, full_page=False)
            record.screenshot_path = screenshot_file

            # Update database
            self.db.update_job_status(job.id, record.status)
            self.db.record_application(record)

            if record.status == ApplicationStatus.APPLIED:
                await self.hitl.notify_application_submitted(
                    job_title=job.title,
                    company=job.company,
                    url=target_url,
                    screenshot_path=screenshot_file
                )

        except Exception as e:
            logger.error(f"Application failed for job {job.id}: {e}", exc_info=True)
            record.status = ApplicationStatus.FAILED
            record.error_message = str(e)
            self.db.update_job_status(job.id, ApplicationStatus.FAILED)
            self.db.record_application(record)

        finally:
            await page.close()

        return record

    async def _detect_captcha(self, page: Page) -> bool:
        """Checks for common CAPTCHA / bot challenge indicators on page."""
        captcha_selectors = [
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            "iframe[src*='turnstile']",
            "#challenge-stage",
            ".g-recaptcha",
            "#captcha"
        ]
        for sel in captcha_selectors:
            if await page.query_selector(sel):
                return True
        return False

    async def _fill_greenhouse(self, page: Page, job: JobListing, auto_submit: bool) -> ApplicationRecord:
        """Automates Greenhouse ATS form filling."""
        p = self.profile_mgr.profile
        answers = {}

        # Basic Fields
        await self._fill_if_present(page, "#first_name", p.personal_info.full_name.split()[0])
        await self._fill_if_present(page, "#last_name", " ".join(p.personal_info.full_name.split()[1:]))
        await self._fill_if_present(page, "#email", p.personal_info.email)
        await self._fill_if_present(page, "#phone", p.personal_info.phone)

        # Dynamically select and upload tailored resume for this job role
        resume_path = self.profile_mgr.get_resume_for_job(job)
        if resume_path and resume_path.exists():
            upload_input = await page.query_selector("input[type='file']")
            if upload_input:
                await upload_input.set_input_files(str(resume_path.resolve()))
                answers["_resume_attached"] = resume_path.name
                logger.info(f"Attached tailored resume '{resume_path.name}' for role '{job.title}'")

        # Social links
        if p.personal_info.linkedin_url:
            await self._fill_if_present(page, "input[name*='linkedin'], input[id*='linkedin']", p.personal_info.linkedin_url)
        if p.personal_info.portfolio_url:
            await self._fill_if_present(page, "input[name*='website'], input[name*='portfolio']", p.personal_info.portfolio_url)

        # Custom screening questions
        custom_fields = await page.query_selector_all(".field, .application-question")
        for field in custom_fields:
            label_el = await field.query_selector("label")
            if not label_el:
                continue
            question_text = (await label_el.inner_text()).strip()

            input_el = await field.query_selector("input[type='text'], textarea")
            if input_el:
                answer = await self.solver.answer_question(question_text)
                await input_el.fill(answer)
                answers[question_text] = answer

        if auto_submit:
            submit_btn = await page.query_selector("#submit_app, button[type='submit']")
            if submit_btn:
                await submit_btn.click()
                await asyncio.sleep(5)
                return ApplicationRecord(job_id=job.id, status=ApplicationStatus.APPLIED, applied_at=datetime.now(timezone.utc), answers_submitted=answers)

        return ApplicationRecord(job_id=job.id, status=ApplicationStatus.MANUAL_REVIEW, notes="Form filled; pending final user submission", answers_submitted=answers)

    async def _fill_lever(self, page: Page, job: JobListing, auto_submit: bool) -> ApplicationRecord:
        """Automates Lever ATS form filling."""
        p = self.profile_mgr.profile
        answers = {}

        # Look for 'Apply' button on posting page
        apply_btn = await page.query_selector("a.postings-btn[href*='/apply']")
        if apply_btn:
            await apply_btn.click()
            await asyncio.sleep(2)

        # Fill standard fields
        await self._fill_if_present(page, "input[name='name']", p.personal_info.full_name)
        await self._fill_if_present(page, "input[name='email']", p.personal_info.email)
        await self._fill_if_present(page, "input[name='phone']", p.personal_info.phone)
        await self._fill_if_present(page, "input[name='org']", p.work_experience[0].company if p.work_experience else "")

        # Social URLs
        if p.personal_info.linkedin_url:
            await self._fill_if_present(page, "input[name='urls[LinkedIn]']", p.personal_info.linkedin_url)
        if p.personal_info.github_url:
            await self._fill_if_present(page, "input[name='urls[GitHub]']", p.personal_info.github_url)
        if p.personal_info.portfolio_url:
            await self._fill_if_present(page, "input[name='urls[Portfolio]']", p.personal_info.portfolio_url)

        # Resume upload
        resume_path = self.profile_mgr.get_resume_for_job(job)
        if resume_path and resume_path.exists():
            file_input = await page.query_selector("input[type='file']#resume-upload-input, input[type='file']")
            if file_input:
                await file_input.set_input_files(str(resume_path.resolve()))
                answers["_resume_attached"] = resume_path.name
                logger.info(f"Attached tailored resume '{resume_path.name}' for role '{job.title}'")

        if auto_submit:
            submit_btn = await page.query_selector("#btn-submit, button[type='submit']")
            if submit_btn:
                await submit_btn.click()
                await asyncio.sleep(5)
                return ApplicationRecord(job_id=job.id, status=ApplicationStatus.APPLIED, applied_at=datetime.now(timezone.utc), answers_submitted=answers)

        return ApplicationRecord(job_id=job.id, status=ApplicationStatus.MANUAL_REVIEW, notes="Lever form filled; pending final submission", answers_submitted=answers)

    async def _fill_linkedin_easy_apply(self, page: Page, job: JobListing, auto_submit: bool) -> ApplicationRecord:
        """Navigates LinkedIn Easy Apply multi-page modal."""
        apply_btn = await page.query_selector(".jobs-apply-button")
        if not apply_btn:
            return ApplicationRecord(job_id=job.id, status=ApplicationStatus.FAILED, error_message="No Easy Apply button visible (may require login)")

        await apply_btn.click()
        await asyncio.sleep(2)

        answers = {}
        # Multi-step loop (max 6 steps to avoid infinite loops)
        for step in range(6):
            # Check if resume upload requested on current modal step
            file_input = await page.query_selector("input[type='file']")
            if file_input:
                resume_path = self.profile_mgr.get_resume_for_job(job)
                if resume_path and resume_path.exists():
                    try:
                        await file_input.set_input_files(str(resume_path.resolve()))
                        answers["_resume_attached"] = resume_path.name
                        logger.info(f"Attached tailored resume '{resume_path.name}' to LinkedIn Easy Apply")
                    except Exception as e:
                        logger.debug(f"LinkedIn resume attachment skipped: {e}")

            # Check if submitted
            success_heading = await page.query_selector(".artdeco-inline-feedback--success, .jpac-modal-header")
            if success_heading:
                return ApplicationRecord(job_id=job.id, status=ApplicationStatus.APPLIED, applied_at=datetime.now(timezone.utc), answers_submitted=answers)

            # Check next or review or submit
            submit_btn = await page.query_selector("button[aria-label='Submit application']")
            if submit_btn and auto_submit:
                await submit_btn.click()
                await asyncio.sleep(3)
                return ApplicationRecord(job_id=job.id, status=ApplicationStatus.APPLIED, applied_at=datetime.now(timezone.utc), answers_submitted=answers)
            elif submit_btn and not auto_submit:
                return ApplicationRecord(job_id=job.id, status=ApplicationStatus.MANUAL_REVIEW, notes="Ready for final review submission", answers_submitted=answers)

            next_btn = await page.query_selector("button[aria-label='Continue to next step'], button[aria-label='Review your application']")
            if next_btn:
                await next_btn.click()
                await asyncio.sleep(1.5)
            else:
                break

        return ApplicationRecord(job_id=job.id, status=ApplicationStatus.MANUAL_REVIEW, notes="Partial Easy Apply completion", answers_submitted=answers)

    async def _fill_generic_form(self, page: Page, job: JobListing, auto_submit: bool) -> ApplicationRecord:
        """Generic fallback form filler detecting standard semantic input names."""
        p = self.profile_mgr.profile
        await self._fill_if_present(page, "input[name*='name'], input[id*='name']", p.personal_info.full_name)
        await self._fill_if_present(page, "input[type='email'], input[name*='email']", p.personal_info.email)
        await self._fill_if_present(page, "input[type='tel'], input[name*='phone']", p.personal_info.phone)

        # Attach tailored resume
        resume_path = self.profile_mgr.get_resume_for_job(job)
        if resume_path and resume_path.exists():
            file_input = await page.query_selector("input[type='file']")
            if file_input:
                try:
                    await file_input.set_input_files(str(resume_path.resolve()))
                except Exception:
                    pass

        return ApplicationRecord(job_id=job.id, status=ApplicationStatus.MANUAL_REVIEW, notes="Generic form pre-filled; manual review advised")

    async def _fill_if_present(self, page: Page, selector: str, text: str):
        try:
            el = await page.query_selector(selector)
            if el and await el.is_visible():
                await el.fill(text)
        except Exception:
            pass
