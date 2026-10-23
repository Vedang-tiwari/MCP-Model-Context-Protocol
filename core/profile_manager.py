"""Profile and search preferences manager with rule-based and semantic match scoring."""
import json
import logging
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

import uuid
from datetime import datetime, timezone

from .models import CandidateProfile, SearchPreferences, JobListing, RoleResumeMapping
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

    def save_profile(self):
        """Persists the current CandidateProfile to candidate_profile.json."""
        with open(self.profile_path, "w", encoding="utf-8") as f:
            json.dump(self.profile.model_dump(), f, indent=2)
        logger.info(f"Persisted candidate profile to {self.profile_path}")

    def add_role_resume(
        self,
        file_path: str,
        role_pattern: str,
        original_filename: str,
        is_default: bool = False
    ) -> RoleResumeMapping:
        """Adds or updates a resume mapped to a specific job role/designation."""
        path_obj = Path(file_path)
        size_kb = round(path_obj.stat().st_size / 1024, 1) if path_obj.exists() else 0.0

        if is_default:
            for item in self.profile.role_resumes:
                item.is_default = False

        # If role_pattern already exists, update it
        existing = next((r for r in self.profile.role_resumes if r.role_pattern.lower() == role_pattern.lower()), None)
        if existing:
            existing.file_path = str(path_obj)
            existing.file_name = original_filename
            existing.file_size_kb = size_kb
            existing.uploaded_at = datetime.now(timezone.utc).isoformat()
            existing.is_default = is_default or existing.is_default
            mapping = existing
        else:
            mapping = RoleResumeMapping(
                id=uuid.uuid4().hex[:8],
                role_pattern=role_pattern.strip(),
                file_path=str(path_obj),
                file_name=original_filename,
                file_size_kb=size_kb,
                uploaded_at=datetime.now(timezone.utc).isoformat(),
                is_default=is_default
            )
            self.profile.role_resumes.append(mapping)

        # Also update fallback resume_file_path if default or empty
        if is_default or not self.profile.resume_file_path:
            self.profile.resume_file_path = str(path_obj)

        self.save_profile()
        logger.info(f"Registered resume mapping: '{role_pattern}' -> {original_filename} ({size_kb} KB)")
        return mapping

    def remove_role_resume(self, resume_id_or_role: str) -> bool:
        """Removes a resume mapping by its ID or role pattern."""
        initial_len = len(self.profile.role_resumes)
        target = resume_id_or_role.strip().lower()

        self.profile.role_resumes = [
            r for r in self.profile.role_resumes
            if r.id.lower() != target and r.role_pattern.lower() != target
        ]

        if len(self.profile.role_resumes) < initial_len:
            self.save_profile()
            logger.info(f"Removed resume mapping for '{resume_id_or_role}'")
            return True
        return False

    def get_resume_by_id(self, resume_id: str) -> Optional[RoleResumeMapping]:
        """Finds a resume mapping by ID."""
        for r in self.profile.role_resumes:
            if r.id.lower() == resume_id.strip().lower():
                return r
        return None

    def get_resume_for_job(self, job: JobListing) -> Optional[Path]:
        """
        Dynamically selects the best-matching resume mapped to the job role.
        Evaluates title keywords, domain acronyms (SWE, FDE, AI, etc.), and fallbacks to default.
        """
        if not self.profile.role_resumes:
            # Fallback to single resume_file_path
            if self.profile.resume_file_path:
                fb = Path(self.profile.resume_file_path)
                if fb.exists():
                    return fb
            return None

        title_lower = job.title.lower().replace("-", " ")
        desc_lower = (job.description or "").lower()

        # Acronym & synonym aliases
        synonyms = {
            "ai": ["ai", "artificial intelligence", "machine learning", "ml", "deep learning", "llm", "nlp"],
            "swe": ["software engineer", "swe", "sde", "software development engineer", "programmer"],
            "fde": ["forward deployed", "forward deployment", "fde", "frontend", "front end", "ui engineer"],
            "frontend": ["frontend", "front end", "ui", "react", "next.js", "vue", "angular", "client"],
            "backend": ["backend", "back end", "server", "python", "golang", "java", "api", "distributed"],
            "full stack": ["full stack", "fullstack", "end to end"],
            "data": ["data engineer", "etl", "analytics", "data platform", "sql", "pipeline"]
        }

        # 1. Exact / Alias Match across configured role patterns
        best_match: Optional[RoleResumeMapping] = None
        highest_score = 0
        import re

        for mapping in self.profile.role_resumes:
            pattern = mapping.role_pattern.lower().strip()
            score = 0

            # Direct whole pattern match
            if pattern == "*":
                score = 1
            elif pattern in title_lower:
                score = 100 + len(pattern)
            else:
                # Token matching with word boundaries
                tokens = [tok for tok in re.split(r'[^a-zA-Z0-9]', pattern) if tok]
                matched_tokens = 0
                for tok in tokens:
                    if re.search(r'\b' + re.escape(tok) + r'\b', title_lower):
                        matched_tokens += 1
                    else:
                        tok_syns = synonyms.get(tok, [])
                        if any(re.search(r'\b' + re.escape(s) + r'\b', title_lower) for s in tok_syns):
                            matched_tokens += 1

                if tokens:
                    if matched_tokens == len(tokens):
                        score = 80 + (matched_tokens * 10)
                    elif matched_tokens > 0:
                        score = matched_tokens * 15

            if score > highest_score:
                highest_score = score
                best_match = mapping

        # 2. Check if best match file exists
        if best_match and highest_score > 10:
            candidate_path = Path(best_match.file_path)
            if candidate_path.exists():
                logger.info(f"Selected tailored resume for '{job.title}': {candidate_path.name} (Matched: '{best_match.role_pattern}', Score={highest_score})")
                return candidate_path

        # 3. Fallback: Default resume
        default_mapping = next((r for r in self.profile.role_resumes if r.is_default), None)
        if default_mapping:
            candidate_path = Path(default_mapping.file_path)
            if candidate_path.exists():
                logger.info(f"Using default fallback resume for '{job.title}': {candidate_path.name}")
                return candidate_path

        # 4. Fallback: First existing resume in role_resumes
        for r in self.profile.role_resumes:
            candidate_path = Path(r.file_path)
            if candidate_path.exists():
                logger.info(f"Using first available resume for '{job.title}': {candidate_path.name}")
                return candidate_path

        # 5. Fallback: Legacy resume_file_path
        if self.profile.resume_file_path:
            legacy_path = Path(self.profile.resume_file_path)
            if legacy_path.exists():
                return legacy_path

        logger.warning(f"No valid resume file found for '{job.title}'")
        return None

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
