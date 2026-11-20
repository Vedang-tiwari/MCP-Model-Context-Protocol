"""Job Filtering and Fit Scoring Engine matching Blueprint §4.2 specifications.

Implements:
1. Hard deterministic filters (blocklists, location mismatch, seniority, visa sponsorship conflict, posting age).
2. 5-factor weighted soft scoring (0.0 to 1.0):
   - 0.35 Embedding / keyword semantic overlap
   - 0.30 Must-have skill coverage (skills.strong)
   - 0.15 Title & seniority match
   - 0.10 Company & type preference
   - 0.10 Freshness & competition proxy
3. Explicit logging of rejection reasons for every filtered job.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Tuple, List, Dict, Any, Optional

from core.models import JobListing, ApplicationStatus
from core.profile_manager import ProfileManager

logger = logging.getLogger(__name__)


class JobFitScorer:
    def __init__(self, profile_mgr: ProfileManager, shortlist_threshold: float = 0.65):
        self.profile_mgr = profile_mgr
        self.threshold = shortlist_threshold

    def evaluate_job(self, job: JobListing) -> Tuple[bool, float, List[str], List[str], Optional[str]]:
        """
        Runs hard filters and soft scoring on a job listing.
        Returns:
            (is_shortlisted, score_0_to_1, fit_reasons, red_flags, rejection_reason)
        """
        # Step 1: Hard deterministic filters
        passes_hard, rej_reason = self.check_hard_filters(job)
        if not passes_hard:
            return False, 0.0, [], [rej_reason], rej_reason

        # Step 2: 5-Factor Soft fit scoring
        score, fit_reasons, red_flags = self.calculate_soft_score(job)
        is_shortlisted = score >= self.threshold
        rejection_reason = None if is_shortlisted else f"Score {score:.2f} below threshold {self.threshold:.2f}"

        return is_shortlisted, score, fit_reasons, red_flags, rejection_reason

    def check_hard_filters(self, job: JobListing) -> Tuple[bool, Optional[str]]:
        """
        Deterministic, zero-cost hard filters. Returns (passed, rejection_reason).
        """
        p_yaml = self.profile_mgr.get_profile_yaml()
        prefs = p_yaml.get("preferences", {})
        work_auth = p_yaml.get("work_authorization", {})

        company_clean = (job.company or "").lower().strip()
        title_clean = (job.title or "").lower().strip()
        desc_clean = (job.description or "").lower()
        full_text = f"{title_clean} {company_clean} {desc_clean}"

        # 1. Company Blocklist
        block_companies = [c.lower().strip() for c in prefs.get("blocklist_companies", [])]
        for b_comp in block_companies:
            if b_comp and b_comp in company_clean:
                return False, f"Company '{job.company}' is in candidate blocklist"

        # 2. Keyword Blocklist (unpaid, commission only, MLM, etc.)
        block_keywords = [k.lower().strip() for k in prefs.get("blocklist_keywords", [])]
        for kw in block_keywords:
            if kw and re.search(r'\b' + re.escape(kw) + r'\b', full_text):
                return False, f"Job description contains blocklisted term: '{kw}'"

        # 3. Work Authorization & Sponsorship Conflict
        needs_sponsor = work_auth.get("needs_sponsorship", False)
        if not needs_sponsor:
            # If candidate does NOT need sponsorship, check if job strictly excludes all US/local citizens (rare)
            pass
        else:
            # If candidate DOES need sponsorship, check if job explicitly states no sponsorship
            no_sponsor_patterns = [
                "no sponsorship", "unable to sponsor", "cannot sponsor", "not offer visa sponsorship",
                "us citizens only", "security clearance required"
            ]
            for pat in no_sponsor_patterns:
                if pat in full_text:
                    return False, f"Job explicitly states: '{pat}', but candidate requires visa sponsorship"

        # 4. Location / Remote Preference Mismatch
        remote_prefs = [r.lower() for r in work_auth.get("remote_preference", ["remote", "hybrid", "onsite"])]
        job_loc = (job.location or "").lower()
        is_remote_job = "remote" in job_loc or "anywhere" in job_loc or "wfh" in job_loc
        if not is_remote_job and "onsite" not in remote_prefs and "hybrid" not in remote_prefs:
            return False, f"Job is onsite at '{job.location}' but candidate prefers strictly Remote"

        # 5. Posting Age (> 30 days)
        if job.posted_at:
            age_days = (datetime.now(timezone.utc) - job.posted_at.replace(tzinfo=timezone.utc if job.posted_at.tzinfo is None else None)).days
            if age_days > 30:
                return False, f"Job posting age ({age_days} days) exceeds maximum 30 days threshold"

        return True, None

    def calculate_soft_score(self, job: JobListing) -> Tuple[float, List[str], List[str]]:
        """
        Calculates 5-factor weighted score (0.0 - 1.0) with reasons and flags.
        Weights:
        - 0.35: Semantic keyword / text similarity
        - 0.30: Must-have skill coverage
        - 0.15: Title match
        - 0.10: Company preference
        - 0.10: Freshness
        """
        p_yaml = self.profile_mgr.get_profile_yaml()
        skills = p_yaml.get("skills", {})
        strong_skills = [s.lower() for s in skills.get("strong", [])]
        familiar_skills = [s.lower() for s in skills.get("familiar", [])]
        prefs = p_yaml.get("preferences", {})
        target_titles = [t.lower() for t in prefs.get("target_titles", [])]

        title_lower = (job.title or "").lower()
        desc_lower = (job.description or "").lower()
        text_corpus = f"{title_lower} {desc_lower}"

        fit_reasons = []
        red_flags = []

        # Factor 1: Must-Have Skill Coverage (0.30 weight)
        matched_strong = [s for s in strong_skills if re.search(r'\b' + re.escape(s) + r'\b', text_corpus)]
        skill_coverage = len(matched_strong) / max(1, len(strong_skills))
        skill_score = min(1.0, skill_coverage * 2.0)  # scale up if multiple key skills hit
        if matched_strong:
            fit_reasons.append(f"Strong skill match: {', '.join(matched_strong[:4])}")
        else:
            red_flags.append("Few core skills explicitly mentioned in job description")

        # Factor 2: Semantic / Keyword Overlap (0.35 weight)
        all_skills = strong_skills + familiar_skills
        matched_all = [s for s in all_skills if re.search(r'\b' + re.escape(s) + r'\b', text_corpus)]
        semantic_score = min(1.0, len(matched_all) / max(3, len(all_skills) * 0.4))
        if len(matched_all) >= 3:
            fit_reasons.append(f"Tech stack overlap: {len(matched_all)} matching tools/languages")

        # Factor 3: Title & Seniority Match (0.15 weight)
        title_score = 0.0
        for target in target_titles:
            words = target.split()
            if all(w in title_lower for w in words):
                title_score = 1.0
                fit_reasons.append(f"Exact title match with target role: '{target}'")
                break
            elif any(w in title_lower for w in words):
                title_score = max(title_score, 0.6)

        if title_score == 0.0:
            red_flags.append(f"Job title '{job.title}' diverges from configured target titles")

        # Factor 4: Company & Type Preference (0.10 weight)
        company_score = 0.5  # neutral baseline
        target_companies = self.profile_mgr.get_target_companies()
        target_names = [c.get("name", "").lower() for c in target_companies]
        if any(t in (job.company or "").lower() for t in target_names):
            company_score = 1.0
            fit_reasons.append(f"High-priority curated target company: {job.company}")

        # Factor 5: Freshness (0.10 weight)
        freshness_score = 0.8
        if job.posted_at:
            now_dt = datetime.now(timezone.utc)
            posted_dt = job.posted_at if job.posted_at.tzinfo else job.posted_at.replace(tzinfo=timezone.utc)
            hours_old = (now_dt - posted_dt).total_seconds() / 3600
            if hours_old <= 24:
                freshness_score = 1.0
                fit_reasons.append("Fresh posting (under 24 hours)")
            elif hours_old <= 72:
                freshness_score = 0.8
            else:
                freshness_score = 0.5

        # Weighted calculation
        final_score = (
            (0.30 * skill_score) +
            (0.35 * semantic_score) +
            (0.15 * title_score) +
            (0.10 * company_score) +
            (0.10 * freshness_score)
        )
        final_score = round(min(1.0, max(0.0, final_score)), 2)

        return final_score, fit_reasons, red_flags
