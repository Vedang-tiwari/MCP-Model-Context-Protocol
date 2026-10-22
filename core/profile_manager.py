"""Profile and search preferences manager with rule-based and semantic match scoring."""
import json
import logging
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

from .models import CandidateProfile, SearchPreferences, JobListing
from .config import settings

logger = logging.getLogger(__name__)


class ProfileManager:
    def __init__(self, profile_path: Optional[Path] = None, prefs_path: Optional[Path] = None):
        self.profile_path = profile_path or settings.PROFILE_PATH
        self.prefs_path = prefs_path or settings.SEARCH_PREFS_PATH

        if not self.profile_path.exists():
            example_profile = self.profile_path.parent / "candidate_profile.example.json"
            if example_profile.exists():
                self.profile_path.write_text(example_profile.read_text(encoding="utf-8"), encoding="utf-8")

        if not self.prefs_path.exists():
            example_prefs = self.prefs_path.parent / "search_preferences.example.json"
            if example_prefs.exists():
                self.prefs_path.write_text(example_prefs.read_text(encoding="utf-8"), encoding="utf-8")

        self.profile: CandidateProfile = self._load_profile()
        self.preferences: SearchPreferences = self._load_preferences()

    def _load_profile(self) -> CandidateProfile:
        with open(self.profile_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return CandidateProfile(**data)

    def _load_preferences(self) -> SearchPreferences:
        with open(self.prefs_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return SearchPreferences(**data)

    def reload(self):
        self.profile = self._load_profile()
        self.preferences = self._load_preferences()

    def evaluate_fit(self, job: JobListing) -> Tuple[int, List[str]]:
        """
        Calculates a compatibility score (0-100) between the candidate profile and job listing.
        Considers:
        - Blacklisted companies (immediate score 0)
        - Target roles matching (weight 40%)
        - Skill overlap in description (weight 40%)
        - Location / Remote match (weight 20%)
        """
        reasons: List[str] = []

        # 1. Blacklist check
        for blacklisted in self.preferences.blacklist_companies:
            if blacklisted.lower() in job.company.lower():
                return 0, [f"Company '{job.company}' is in blacklist ({blacklisted})"]

        score = 0
        title_lower = job.title.lower()
        desc_lower = (job.description or "").lower()

        # 2. Target Role match (up to 40 points)
        role_matched = False
        for role in self.preferences.target_roles:
            role_keywords = role.lower().split()
            # If all keywords in target role appear in title or description
            if all(k in title_lower for k in role_keywords):
                score += 40
                reasons.append(f"Title perfectly matches target role: '{role}'")
                role_matched = True
                break
            elif any(k in title_lower for k in role_keywords):
                score += 25
                reasons.append(f"Title partially matches target role: '{role}'")
                role_matched = True
                break

        if not role_matched:
            # Check if any role keyword is in the description
            for role in self.preferences.target_roles:
                if role.lower() in desc_lower:
                    score += 15
                    reasons.append(f"Description mentions target role: '{role}'")
                    break

        # 3. Skills overlap (up to 40 points)
        matched_skills = []
        candidate_skills = []
        for cat, skills in self.profile.skills.items():
            candidate_skills.extend(skills)

        for skill in candidate_skills:
            # Word boundary check for skill
            if f" {skill.lower()} " in f" {desc_lower} " or f" {skill.lower()} " in f" {title_lower} ":
                matched_skills.append(skill)

        if matched_skills:
            skill_points = min(40, len(matched_skills) * 8)
            score += skill_points
            reasons.append(f"Matched {len(matched_skills)} core skills: {', '.join(matched_skills[:5])}")
        else:
            reasons.append("No explicit skill keywords identified in initial snippet")

        # 4. Location & Remote match (up to 20 points)
        loc_lower = job.location.lower()
        if "remote" in loc_lower or "anywhere" in loc_lower or "wfh" in loc_lower:
            score += 20
            reasons.append("Remote job matches candidate preference")
        else:
            matched_loc = False
            for preferred_loc in self.preferences.locations:
                if preferred_loc.lower() in loc_lower:
                    score += 20
                    reasons.append(f"Location matches preferred: '{preferred_loc}'")
                    matched_loc = True
                    break
            if not matched_loc:
                if self.preferences.remote_only:
                    return 0, ["Job is not remote, but remote_only preference is set"]
                score += 5
                reasons.append(f"Job location is '{job.location}'")

        final_score = min(100, max(0, score))
        return final_score, reasons

    def format_profile_for_llm(self) -> str:
        """Serializes candidate profile into a compact, high-signal prompt context for LLMs."""
        p = self.profile
        lines = [
            f"Candidate: {p.personal_info.full_name}",
            f"Email: {p.personal_info.email} | Phone: {p.personal_info.phone}",
            f"Location: {p.personal_info.current_city}, {p.personal_info.country}",
            f"Summary: {p.summary}",
            "Core Skills: " + ", ".join([f"{k}: {', '.join(v)}" for k, v in p.skills.items()]),
            f"Experience: {p.standard_answers.years_of_experience} years total",
            f"Notice Period: {p.standard_answers.notice_period_days} days",
            f"Work Authorization: {p.standard_answers.work_authorization} (Sponsorship needed: {p.standard_answers.requires_sponsorship})",
            f"Expected Compensation: ${p.standard_answers.expected_salary_usd} USD / ₹{p.standard_answers.expected_salary_inr} INR",
            "Key Work Experience:"
        ]
        for exp in p.work_experience[:3]:
            lines.append(f"- {exp.role} at {exp.company} ({exp.start_date} to {exp.end_date}): {exp.description}")

        lines.append("Education:")
        for edu in p.education:
            lines.append(f"- {edu.degree} in {edu.field_of_study} from {edu.institution} ({edu.graduation_year})")

        if p.qa_knowledge_base:
            lines.append("Knowledge Base Q&A:")
            for qa in p.qa_knowledge_base:
                lines.append(f"- [{qa.topic}] Q: {', '.join(qa.question_keywords)} -> A: {qa.answer}")

        return "\n".join(lines)
