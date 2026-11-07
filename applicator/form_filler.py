"""Autonomous Form Filler for standard ATS portals (Greenhouse, Lever, Ashby) and universal job platforms."""
import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from playwright.async_api import Page, Frame

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
        # Bounded concurrency: allows up to 3 simultaneous browser applications
        self._semaphore = asyncio.Semaphore(3)

    async def apply(
        self,
        job: JobListing,
        auto_submit: bool = False,
        page: Optional[Page] = None
    ) -> ApplicationRecord:
        """
        Executes the autonomous application workflow for a given job.
        If auto_submit is True, fills out the form and clicks submit.
        If auto_submit is False (Review Mode), fills out the form and leaves the tab open for inspection.
        """
        async with self._semaphore:
            logger.info(f"Initiating autonomous application for '{job.title}' at '{job.company}' ({job.url})")
            self.db.update_job_status(job.id, ApplicationStatus.APPLYING)

            record = ApplicationRecord(
                job_id=job.id,
                status=ApplicationStatus.APPLYING,
                applied_at=None,
                attempts=1,
                answers_submitted={}
            )

            own_page = False
            target_url = job.apply_url or job.url
            if target_url and not target_url.startswith("http"):
                target_url = f"https://{target_url}"

            try:
                if page is None:
                    page = await self.session_mgr.new_tab()
                    own_page = True

                logger.info(f"Navigating stealth browser to: {target_url}")
                await page.goto(target_url, wait_until="domcontentloaded", timeout=35000)
                await asyncio.sleep(2)

                # Dismiss cookie consent overlays that obstruct clicking
                await self._dismiss_cookie_banners(page)

                # Step 1: Pre-form navigation - click Apply / Apply Now if on a job listing page
                page = await self._navigate_to_application_form(page)

                # Dismiss cookie banners again in case new page or modal opened
                await self._dismiss_cookie_banners(page)

                # Step 2: Check for active CAPTCHA / bot challenges
                if await self._detect_captcha(page):
                    await self.hitl.notify_human_action_required(
                        reason="CAPTCHA or Bot Detection encountered",
                        job_title=job.title,
                        company=job.company,
                        url=target_url
                    )
                    record.status = ApplicationStatus.MANUAL_REVIEW
                    record.notes = "Security verification / CAPTCHA challenge detected. Please complete verification in the opened browser window."
                    self.db.update_job_status(job.id, ApplicationStatus.MANUAL_REVIEW)
                    self.db.record_application(record)
                    return record

                # Step 3: Fill application form based on current URL / ATS
                current_url = page.url or target_url
                if "greenhouse.io" in current_url or job.metadata.get("ats_type") == "greenhouse":
                    record = await self._fill_greenhouse(page, job, auto_submit)
                elif "lever.co" in current_url or job.metadata.get("ats_type") == "lever":
                    record = await self._fill_lever(page, job, auto_submit)
                elif "linkedin.com" in current_url:
                    record = await self._fill_linkedin_easy_apply(page, job, auto_submit)
                else:
                    record = await self._fill_generic_form(page, job, auto_submit)

                # Capture screenshot evidence
                screenshot_file = str(self.screenshots_dir / f"job_{job.id}.png")
                try:
                    await page.screenshot(path=screenshot_file, full_page=False)
                    record.screenshot_path = screenshot_file
                except Exception as ss_err:
                    logger.debug(f"Screenshot capture skipped: {ss_err}")

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
                record.notes = f"Application attempt failed ({e}). Check opened browser tab to complete manually."
                record.error_message = str(e)
                self.db.update_job_status(job.id, ApplicationStatus.FAILED)
                self.db.record_application(record)

            finally:
                if auto_submit and record.status == ApplicationStatus.APPLIED and own_page and page and not page.is_closed():
                    try:
                        await page.close()
                    except Exception:
                        pass
                else:
                    logger.info("Browser session left open for manual inspection or review.")

            return record

    async def batch_apply(
        self,
        jobs: List[JobListing],
        auto_submit: bool = True,
        max_concurrency: int = 3
    ) -> List[ApplicationRecord]:
        """
        Executes autonomous applications across multiple jobs simultaneously
        using controlled Playwright tab concurrency.
        """
        logger.info(f"Starting batch application sweep for {len(jobs)} jobs (concurrency={max_concurrency}, auto_submit={auto_submit})")
        sem = asyncio.Semaphore(max_concurrency)

        async def _worker(job: JobListing) -> ApplicationRecord:
            async with sem:
                page: Optional[Page] = None
                record: Optional[ApplicationRecord] = None
                try:
                    page = await self.session_mgr.new_tab()
                    record = await self.apply(job, auto_submit=auto_submit, page=page)
                    return record
                except Exception as e:
                    logger.error(f"Batch application error on job {job.id} ({job.title}): {e}", exc_info=True)
                    record = ApplicationRecord(
                        job_id=job.id,
                        status=ApplicationStatus.FAILED,
                        notes=f"Batch execution error: {str(e)}",
                        error_message=str(e)
                    )
                    self.db.update_job_status(job.id, ApplicationStatus.FAILED)
                    self.db.record_application(record)
                    return record
                finally:
                    if auto_submit and record and record.status == ApplicationStatus.APPLIED and page and not page.is_closed():
                        try:
                            await page.close()
                        except Exception:
                            pass

        tasks = [_worker(job) for job in jobs]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results

    async def _dismiss_cookie_banners(self, page: Page):
        """Dismisses common GDPR / cookie consent banners that obstruct form interaction."""
        banner_selectors = [
            "#onetrust-accept-btn-handler",
            "button#accept-cookies",
            "button:has-text('Accept All Cookies')",
            "button:has-text('Accept all cookies')",
            "button:has-text('Accept All')",
            "button:has-text('Accept all')",
            "button:has-text('I Accept')",
            "button:has-text('Allow All')",
            "button:has-text('Got it')",
            "button:has-text('Agree & Continue')",
            "button[aria-label='Accept Cookies']",
            ".cookie-banner__accept",
            ".cc-btn.cc-allow"
        ]
        for frame in [page] + page.frames:
            for sel in banner_selectors:
                try:
                    btn = await frame.query_selector(sel)
                    if btn and await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(0.5)
                        return
                except Exception:
                    pass

    async def _navigate_to_application_form(self, page: Page) -> Page:
        """
        Detects if the current landing page is a job description and clicks the 'Apply'
        button to reveal the application form or follow any popup/redirect.
        """
        if await self._has_form_inputs(page):
            return page

        apply_selectors = [
            "a.postings-btn[href*='apply']",
            "a[href*='#app']",
            "a[href*='#apply']",
            "a[href*='/apply']",
            "a#apply_button",
            "button#apply_button",
            "button:has-text('Apply for this job')",
            "a:has-text('Apply for this job')",
            "button:has-text('Apply Now')",
            "a:has-text('Apply Now')",
            "button:has-text('Apply now')",
            "a:has-text('Apply now')",
            "button:has-text('Quick Apply')",
            "a:has-text('Quick Apply')",
            "button:has-text('Easy Apply')",
            "a:has-text('Easy Apply')",
            "button:has-text('Apply on company site')",
            "a:has-text('Apply on company site')",
            "button:has-text('Apply')",
            "a:has-text('Apply')",
            "button:has-text(\"I'm Interested\")",
            "a:has-text(\"I'm Interested\")",
            "[data-test='apply-button']",
            "[data-qa='apply-button']",
            "[data-testid*='apply']",
            ".apply-button",
            ".jobs-apply-button",
        ]

        context = page.context
        for sel in apply_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    logger.info(f"Clicking application trigger: '{sel}'")
                    target_attr = await btn.get_attribute("target")
                    href_attr = await btn.get_attribute("href")
                    
                    if href_attr and href_attr.startswith("http") and not href_attr.startswith("#"):
                        if target_attr == "_blank":
                            try:
                                async with context.expect_page(timeout=5000) as new_page_info:
                                    await btn.click()
                                new_page = await new_page_info.value
                                await new_page.wait_for_load_state("domcontentloaded", timeout=15000)
                                return new_page
                            except Exception:
                                await page.goto(href_attr, wait_until="domcontentloaded", timeout=20000)
                                return page
                        else:
                            try:
                                await page.goto(href_attr, wait_until="domcontentloaded", timeout=20000)
                                return page
                            except Exception:
                                pass

                    try:
                        async with context.expect_page(timeout=4000) as new_page_info:
                            await btn.click()
                        new_page = await new_page_info.value
                        await new_page.wait_for_load_state("domcontentloaded", timeout=15000)
                        return new_page
                    except Exception:
                        await asyncio.sleep(2)
                        return page
            except Exception as e:
                logger.debug(f"Apply trigger click error with selector {sel}: {e}")

        return page

    async def _has_form_inputs(self, page: Page) -> bool:
        """Checks if standard application inputs are present in page or frames."""
        all_frames = [page] + page.frames
        for frame in all_frames:
            try:
                inputs = await frame.query_selector_all("input[type='email'], input[name*='name'], input[type='file'], #first_name, #email")
                if len(inputs) >= 2:
                    return True
            except Exception:
                pass
        return False

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
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                return True
        return False

    async def _fill_greenhouse(self, page: Page, job: JobListing, auto_submit: bool) -> ApplicationRecord:
        """Automates Greenhouse ATS form filling."""
        page = await self._navigate_to_application_form(page)
        p = self.profile_mgr.profile
        answers = {}

        all_frames = [page] + page.frames
        full_name = p.personal_info.full_name
        first_name = full_name.split()[0] if full_name else ""
        last_name = " ".join(full_name.split()[1:]) if full_name and len(full_name.split()) > 1 else first_name

        filled_count = 0
        for frame in all_frames:
            if await self._try_fill_any(frame, ["#first_name", "input[name='first_name']", "input[id*='first_name' i]"], first_name):
                filled_count += 1
                answers["First Name"] = first_name
            if await self._try_fill_any(frame, ["#last_name", "input[name='last_name']", "input[id*='last_name' i]"], last_name):
                filled_count += 1
                answers["Last Name"] = last_name
            if await self._try_fill_any(frame, ["#email", "input[type='email']", "input[name='email']"], p.personal_info.email):
                filled_count += 1
                answers["Email"] = p.personal_info.email
            if await self._try_fill_any(frame, ["#phone", "input[type='tel']", "input[name='phone']"], p.personal_info.phone):
                filled_count += 1
                answers["Phone"] = p.personal_info.phone

            # Resume upload
            resume_path = self.profile_mgr.get_resume_for_job(job)
            if resume_path and resume_path.exists():
                upload_input = await frame.query_selector("input[type='file']")
                if upload_input:
                    try:
                        await upload_input.set_input_files(str(resume_path.resolve()))
                        filled_count += 1
                        answers["_resume_attached"] = resume_path.name
                        logger.info(f"Attached tailored resume '{resume_path.name}' for role '{job.title}'")
                    except Exception as fe:
                        logger.debug(f"Resume upload error: {fe}")

            # Social links
            if p.personal_info.linkedin_url:
                await self._try_fill_any(frame, ["input[name*='linkedin'], input[id*='linkedin']"], p.personal_info.linkedin_url)
            if p.personal_info.portfolio_url:
                await self._try_fill_any(frame, ["input[name*='website'], input[name*='portfolio']"], p.personal_info.portfolio_url)

            # Custom screening questions
            custom_fields = await frame.query_selector_all(".field, .application-question")
            for field in custom_fields:
                label_el = await field.query_selector("label")
                if not label_el:
                    continue
                question_text = (await label_el.inner_text()).strip()

                input_el = await field.query_selector("input[type='text'], textarea")
                if input_el and not await input_el.input_value():
                    answer = await self.solver.answer_question(question_text)
                    await input_el.fill(answer)
                    answers[question_text] = answer

            await self._fill_standard_screening_radios(frame, p)
            await self._fill_standard_screening_selects(frame, p)
            await self._check_consent_checkboxes(frame)

        if auto_submit and filled_count > 0:
            for frame in all_frames:
                submit_btn = await frame.query_selector("#submit_app, button[type='submit'], input[type='submit'], button:has-text('Submit')")
                if submit_btn and await submit_btn.is_visible():
                    await submit_btn.scroll_into_view_if_needed()
                    await submit_btn.click()
                    await asyncio.sleep(4)
                    return ApplicationRecord(
                        job_id=job.id,
                        status=ApplicationStatus.APPLIED,
                        applied_at=datetime.now(timezone.utc),
                        notes=f"Greenhouse form submitted autonomously ({filled_count} fields filled + resume attached).",
                        answers_submitted=answers
                    )

        if filled_count > 0:
            return ApplicationRecord(
                job_id=job.id,
                status=ApplicationStatus.MANUAL_REVIEW,
                notes=f"Greenhouse form pre-filled ({filled_count} fields + resume). Ready for review in opened browser tab.",
                answers_submitted=answers
            )
        else:
            return ApplicationRecord(
                job_id=job.id,
                status=ApplicationStatus.MANUAL_REVIEW,
                notes="Greenhouse job opened in browser; no direct form fields found. Complete application manually.",
                answers_submitted=answers
            )

    async def _fill_lever(self, page: Page, job: JobListing, auto_submit: bool) -> ApplicationRecord:
        """Automates Lever ATS form filling."""
        page = await self._navigate_to_application_form(page)
        p = self.profile_mgr.profile
        answers = {}
        all_frames = [page] + page.frames
        filled_count = 0

        for frame in all_frames:
            if await self._try_fill_any(frame, ["input[name='name']", "input[id='name']"], p.personal_info.full_name):
                filled_count += 1
                answers["Full Name"] = p.personal_info.full_name
            if await self._try_fill_any(frame, ["input[name='email']", "input[id='email']"], p.personal_info.email):
                filled_count += 1
                answers["Email"] = p.personal_info.email
            if await self._try_fill_any(frame, ["input[name='phone']", "input[id='phone']"], p.personal_info.phone):
                filled_count += 1
                answers["Phone"] = p.personal_info.phone
            if p.work_experience:
                await self._try_fill_any(frame, ["input[name='org']", "input[id='org']"], p.work_experience[0].company)

            # Social URLs
            if p.personal_info.linkedin_url:
                await self._try_fill_any(frame, ["input[name='urls[LinkedIn]']", "input[id*='linkedin' i]"], p.personal_info.linkedin_url)
            if p.personal_info.github_url:
                await self._try_fill_any(frame, ["input[name='urls[GitHub]']", "input[id*='github' i]"], p.personal_info.github_url)
            if p.personal_info.portfolio_url:
                await self._try_fill_any(frame, ["input[name='urls[Portfolio]']", "input[id*='portfolio' i]"], p.personal_info.portfolio_url)

            # Resume upload
            resume_path = self.profile_mgr.get_resume_for_job(job)
            if resume_path and resume_path.exists():
                file_input = await frame.query_selector("input[type='file']#resume-upload-input, input[type='file']")
                if file_input:
                    try:
                        await file_input.set_input_files(str(resume_path.resolve()))
                        filled_count += 1
                        answers["_resume_attached"] = resume_path.name
                        logger.info(f"Attached tailored resume '{resume_path.name}' for role '{job.title}'")
                    except Exception as fe:
                        logger.debug(f"Lever resume upload error: {fe}")

            await self._fill_standard_screening_radios(frame, p)
            await self._fill_standard_screening_selects(frame, p)
            await self._check_consent_checkboxes(frame)

        if auto_submit and filled_count > 0:
            for frame in all_frames:
                submit_btn = await frame.query_selector("#btn-submit, button[type='submit'], input[type='submit'], button:has-text('Submit Application')")
                if submit_btn and await submit_btn.is_visible():
                    await submit_btn.scroll_into_view_if_needed()
                    await submit_btn.click()
                    await asyncio.sleep(4)
                    return ApplicationRecord(
                        job_id=job.id,
                        status=ApplicationStatus.APPLIED,
                        applied_at=datetime.now(timezone.utc),
                        notes=f"Lever form submitted autonomously ({filled_count} fields filled + resume attached).",
                        answers_submitted=answers
                    )

        if filled_count > 0:
            return ApplicationRecord(
                job_id=job.id,
                status=ApplicationStatus.MANUAL_REVIEW,
                notes=f"Lever form pre-filled ({filled_count} fields + resume). Ready for review in opened browser tab.",
                answers_submitted=answers
            )
        else:
            return ApplicationRecord(
                job_id=job.id,
                status=ApplicationStatus.MANUAL_REVIEW,
                notes="Lever job opened in browser; no direct form fields found. Complete application manually.",
                answers_submitted=answers
            )

    async def _fill_linkedin_easy_apply(self, page: Page, job: JobListing, auto_submit: bool) -> ApplicationRecord:
        """Navigates LinkedIn Easy Apply multi-page modal."""
        page = await self._navigate_to_application_form(page)
        apply_btn = await page.query_selector(".jobs-apply-button")
        if not apply_btn:
            return ApplicationRecord(job_id=job.id, status=ApplicationStatus.MANUAL_REVIEW, notes="Opened in browser; login or manual completion required")

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
                return ApplicationRecord(job_id=job.id, status=ApplicationStatus.MANUAL_REVIEW, notes="Ready for final review submission in opened browser", answers_submitted=answers)

            next_btn = await page.query_selector("button[aria-label='Continue to next step'], button[aria-label='Review your application']")
            if next_btn:
                await next_btn.click()
                await asyncio.sleep(1.5)
            else:
                break

        return ApplicationRecord(job_id=job.id, status=ApplicationStatus.MANUAL_REVIEW, notes="Easy Apply pre-filled; final review required", answers_submitted=answers)

    async def _fill_generic_form(self, page: Page, job: JobListing, auto_submit: bool) -> ApplicationRecord:
        """Universal autonomous form filler detecting semantic input names, dropzones, radios, and submit buttons."""
        page = await self._navigate_to_application_form(page)
        p = self.profile_mgr.profile
        answers = {}
        filled_count = 0

        all_frames = [page] + page.frames

        # Names
        full_name = p.personal_info.full_name
        first_name = full_name.split()[0] if full_name else ""
        last_name = " ".join(full_name.split()[1:]) if full_name and len(full_name.split()) > 1 else first_name

        for frame in all_frames:
            # First Name
            if await self._try_fill_any(frame, [
                "input[name*='first_name' i]", "input[id*='first_name' i]", "input[name*='firstName' i]",
                "input[id*='firstName' i]", "input[autocomplete='given-name']", "input[placeholder*='First Name' i]",
                "input[aria-label*='First Name' i]"
            ], first_name):
                filled_count += 1
                answers["First Name"] = first_name

            # Last Name
            if await self._try_fill_any(frame, [
                "input[name*='last_name' i]", "input[id*='last_name' i]", "input[name*='lastName' i]",
                "input[id*='lastName' i]", "input[autocomplete='family-name']", "input[placeholder*='Last Name' i]",
                "input[aria-label*='Last Name' i]"
            ], last_name):
                filled_count += 1
                answers["Last Name"] = last_name

            # Full Name (if no separate first/last name was filled)
            if "First Name" not in answers:
                if await self._try_fill_any(frame, [
                    "input[name='name' i]", "input[id='name' i]", "input[name='fullName' i]", "input[id='fullName' i]",
                    "input[name='full_name' i]", "input[id='full_name' i]", "input[autocomplete='name']",
                    "input[placeholder*='Full Name' i]", "input[placeholder='Name' i]", "input[aria-label*='Full Name' i]"
                ], full_name):
                    filled_count += 1
                    answers["Full Name"] = full_name

            # Email
            if await self._try_fill_any(frame, [
                "input[type='email']", "input[name*='email' i]", "input[id*='email' i]",
                "input[autocomplete='email']", "input[placeholder*='email' i]", "input[aria-label*='email' i]"
            ], p.personal_info.email):
                filled_count += 1
                answers["Email"] = p.personal_info.email

            # Phone
            if await self._try_fill_any(frame, [
                "input[type='tel']", "input[name*='phone' i]", "input[id*='phone' i]", "input[name*='mobile' i]",
                "input[autocomplete='tel']", "input[placeholder*='phone' i]", "input[aria-label*='phone' i]"
            ], p.personal_info.phone):
                filled_count += 1
                answers["Phone"] = p.personal_info.phone

            # Location / City
            location_val = f"{p.personal_info.current_city}, {p.personal_info.country}".strip(", ")
            if await self._try_fill_any(frame, [
                "input[name*='city' i]", "input[id*='city' i]", "input[name*='location' i]", "input[id*='location' i]",
                "input[placeholder*='city' i]", "input[placeholder*='location' i]", "input[aria-label*='city' i]"
            ], location_val):
                filled_count += 1
                answers["Location"] = location_val

            # Current Company
            company_val = p.work_experience[0].company if p.work_experience else ""
            if company_val and await self._try_fill_any(frame, [
                "input[name*='company' i]", "input[name*='org' i]", "input[id*='company' i]", "input[id*='org' i]",
                "input[placeholder*='company' i]", "input[placeholder*='organization' i]"
            ], company_val):
                filled_count += 1
                answers["Company"] = company_val

            # Social Profiles
            if p.personal_info.linkedin_url:
                if await self._try_fill_any(frame, [
                    "input[name*='linkedin' i]", "input[id*='linkedin' i]", "input[placeholder*='linkedin' i]"
                ], p.personal_info.linkedin_url):
                    filled_count += 1
                    answers["LinkedIn"] = p.personal_info.linkedin_url

            if p.personal_info.github_url:
                if await self._try_fill_any(frame, [
                    "input[name*='github' i]", "input[id*='github' i]", "input[placeholder*='github' i]"
                ], p.personal_info.github_url):
                    filled_count += 1
                    answers["GitHub"] = p.personal_info.github_url

            if p.personal_info.portfolio_url:
                if await self._try_fill_any(frame, [
                    "input[name*='portfolio' i]", "input[name*='website' i]", "input[id*='portfolio' i]",
                    "input[id*='website' i]", "input[placeholder*='portfolio' i]", "input[placeholder*='website' i]"
                ], p.personal_info.portfolio_url):
                    filled_count += 1
                    answers["Portfolio"] = p.personal_info.portfolio_url

            # Cover Letter / Note
            if p.summary:
                if await self._try_fill_any(frame, [
                    "textarea[name*='cover_letter' i]", "textarea[id*='cover_letter' i]", "textarea[name*='comments' i]",
                    "textarea[name*='summary' i]", "textarea[placeholder*='cover letter' i]", "textarea[placeholder*='note' i]"
                ], p.summary):
                    filled_count += 1
                    answers["Cover Letter"] = "Attached candidate summary"

            # Resume Attachment
            resume_path = self.profile_mgr.get_resume_for_job(job)
            if resume_path and resume_path.exists():
                file_input = await frame.query_selector("input[type='file']")
                if file_input:
                    try:
                        await file_input.set_input_files(str(resume_path.resolve()))
                        filled_count += 1
                        answers["_resume_attached"] = resume_path.name
                        logger.info(f"Attached tailored resume '{resume_path.name}' for job '{job.title}'")
                    except Exception as fe:
                        logger.debug(f"File upload attempt error: {fe}")

            # Screening Radio Buttons, Selects & Checkboxes
            await self._fill_standard_screening_radios(frame, p)
            await self._fill_standard_screening_selects(frame, p)
            await self._check_consent_checkboxes(frame)

        # Submit or Review Mode
        if auto_submit and filled_count > 0:
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Submit Application')",
                "button:has-text('Submit application')",
                "button:has-text('Submit')",
                "button:has-text('Send Application')",
                "button:has-text('Complete Application')",
                "button:has-text('Apply Now')",
                "button.btn-submit",
                "#btn-submit",
                "#submit_app"
            ]
            for frame in all_frames:
                for sel in submit_selectors:
                    try:
                        submit_btn = await frame.query_selector(sel)
                        if submit_btn and await submit_btn.is_visible():
                            logger.info(f"Clicking application submit button: {sel}")
                            await submit_btn.scroll_into_view_if_needed()
                            await submit_btn.click()
                            await asyncio.sleep(4)
                            return ApplicationRecord(
                                job_id=job.id,
                                status=ApplicationStatus.APPLIED,
                                applied_at=datetime.now(timezone.utc),
                                notes=f"Application submitted autonomously ({filled_count} fields filled + resume attached).",
                                answers_submitted=answers
                            )
                    except Exception as se:
                        logger.debug(f"Submit click error on selector {sel}: {se}")

        if filled_count > 0:
            return ApplicationRecord(
                job_id=job.id,
                status=ApplicationStatus.MANUAL_REVIEW,
                notes=f"Form pre-filled ({filled_count} fields + resume attached). Ready for review in opened browser tab.",
                answers_submitted=answers
            )
        else:
            return ApplicationRecord(
                job_id=job.id,
                status=ApplicationStatus.MANUAL_REVIEW,
                notes="External job application portal opened in browser; no standard form inputs found. Manual review required.",
                answers_submitted=answers
            )

    async def _try_fill_any(self, frame, selectors: List[str], text: str) -> bool:
        if not text:
            return False
        for sel in selectors:
            try:
                el = await frame.query_selector(sel)
                if el and await el.is_visible():
                    val = await el.input_value()
                    if not val:
                        await el.scroll_into_view_if_needed()
                        await el.fill(text)
                        return True
                    elif val.strip().lower() == text.strip().lower():
                        return True
            except Exception:
                pass
        return False

    async def _fill_standard_screening_radios(self, frame, profile):
        """Answers standard Yes/No screening radio buttons."""
        try:
            radio_groups = await frame.query_selector_all("input[type='radio']")
            for r in radio_groups:
                name = (await r.get_attribute("name") or "").lower()
                val = (await r.get_attribute("value") or "").lower()
                parent_text = ""
                try:
                    parent = await r.evaluate_handle("el => el.closest('div, label, fieldset')")
                    if parent:
                        parent_text = (await parent.inner_text()).lower()
                except Exception:
                    pass

                # Work Authorization -> Yes
                if any(k in parent_text or k in name for k in ["authorized", "eligibility", "legally", "right to work"]):
                    if val in ["yes", "true", "1"] or "yes" in parent_text:
                        await r.check()

                # Sponsorship -> No (or candidate preference)
                elif any(k in parent_text or k in name for k in ["sponsor", "visa"]):
                    target_val = "yes" if profile.standard_answers.requires_sponsorship else "no"
                    if val in [target_val, "true" if target_val == "yes" else "false", "1" if target_val == "yes" else "0"]:
                        await r.check()

                # 18 or older -> Yes
                elif any(k in parent_text for k in ["18 years", "legal age", "minimum age"]):
                    if val in ["yes", "true", "1"]:
                        await r.check()
        except Exception:
            pass

    async def _fill_standard_screening_selects(self, frame, profile):
        """Selects appropriate answers in dropdowns for standard screening questions."""
        try:
            selects = await frame.query_selector_all("select")
            for sel_el in selects:
                name = (await sel_el.get_attribute("name") or "").lower()
                id_attr = (await sel_el.get_attribute("id") or "").lower()
                parent_text = ""
                try:
                    parent = await sel_el.evaluate_handle("el => el.closest('div, label, fieldset')")
                    if parent:
                        parent_text = (await parent.inner_text()).lower()
                except Exception:
                    pass

                # Work Authorization -> Yes
                if any(k in parent_text or k in name or k in id_attr for k in ["authorized", "eligibility", "legally", "right to work"]):
                    options = await sel_el.query_selector_all("option")
                    for opt in options:
                        txt = (await opt.inner_text()).strip().lower()
                        val = (await opt.get_attribute("value") or "").lower()
                        if txt in ["yes", "true", "i am authorized"] or val in ["yes", "true", "1"]:
                            await sel_el.select_option(value=val or txt)
                            break

                # Sponsorship -> No (or candidate preference)
                elif any(k in parent_text or k in name or k in id_attr for k in ["sponsor", "visa"]):
                    target = "yes" if profile.standard_answers.requires_sponsorship else "no"
                    options = await sel_el.query_selector_all("option")
                    for opt in options:
                        txt = (await opt.inner_text()).strip().lower()
                        val = (await opt.get_attribute("value") or "").lower()
                        if target in txt or target in val:
                            await sel_el.select_option(value=val or txt)
                            break
        except Exception:
            pass

    async def _check_consent_checkboxes(self, frame):
        """Checks required agreement and terms checkboxes."""
        try:
            checkboxes = await frame.query_selector_all("input[type='checkbox']:not(:checked)")
            for cb in checkboxes:
                name = (await cb.get_attribute("name") or "").lower()
                id_attr = (await cb.get_attribute("id") or "").lower()
                if any(k in name or k in id_attr for k in ["consent", "terms", "agree", "privacy", "certify", "acknowledge"]):
                    if await cb.is_visible():
                        await cb.check()
        except Exception:
            pass
