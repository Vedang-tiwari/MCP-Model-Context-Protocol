"""Data schemas and Pydantic models for the MCP Job Application System."""
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ApplicationStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    EVALUATED = "EVALUATED"
    QUEUED = "QUEUED"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    FAILED = "FAILED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    SKIPPED = "SKIPPED"


class JobPlatform(str, Enum):
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    WELLFOUND = "wellfound"
    NAUKRI = "naukri"
    INTERNSHALA = "internshala"
    ATS_DIRECT = "ats_direct"
    UNSTOP = "unstop"
    CUTSHORT = "cutshort"
    GLASSDOOR = "glassdoor"
    OTHER = "other"


class JobListing(BaseModel):
    id: str = Field(description="Unique identifier / deterministic hash of platform + company + title")
    platform: str = Field(description="Platform source e.g. linkedin, indeed, greenhouse")
    title: str
    company: str
    location: str = "Remote"
    url: str
    apply_url: Optional[str] = None
    is_easy_apply: bool = False
    description: Optional[str] = ""
    posted_at: Optional[datetime] = None
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    match_score: Optional[int] = None
    match_reasons: Optional[List[str]] = Field(default_factory=list)
    status: ApplicationStatus = ApplicationStatus.DISCOVERED
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ApplicationRecord(BaseModel):
    id: Optional[int] = None
    job_id: str
    status: ApplicationStatus
    applied_at: Optional[datetime] = None
    attempts: int = 0
    answers_submitted: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    notes: Optional[str] = None


class PersonalInfo(BaseModel):
    full_name: str
    email: str
    phone: str
    country_code: str = "+1"
    current_city: str
    country: str
    postal_code: str = ""
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    twitter_url: Optional[str] = None


class WorkExperience(BaseModel):
    company: str
    role: str
    start_date: str
    end_date: str = "Present"
    location: str = ""
    description: str = ""


class Education(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    graduation_year: int
    gpa: Optional[str] = None


class StandardAnswers(BaseModel):
    years_of_experience: int = 3
    notice_period_days: int = 15
    willing_to_relocate: bool = True
    open_to_remote: bool = True
    work_authorization: str = "Authorized to work"
    requires_sponsorship: bool = False
    expected_salary_usd: Optional[int] = 120000
    expected_salary_inr: Optional[int] = 2000000
    currency_preference: str = "USD"
    eeo: Dict[str, str] = Field(default_factory=dict)


class QAKnowledgeItem(BaseModel):
    topic: str
    question_keywords: List[str]
    answer: str


class CandidateProfile(BaseModel):
    personal_info: PersonalInfo
    summary: str
    skills: Dict[str, List[str]]
    work_experience: List[WorkExperience]
    education: List[Education]
    standard_answers: StandardAnswers
    qa_knowledge_base: List[QAKnowledgeItem] = Field(default_factory=list)
    resume_file_path: Optional[str] = "config/resume.pdf"


class SearchPreferences(BaseModel):
    target_roles: List[str]
    experience_levels: List[str] = Field(default_factory=lambda: ["entry_level", "mid_level"])
    locations: List[str] = Field(default_factory=lambda: ["Remote"])
    remote_only: bool = False
    max_job_age_hours: int = 24
    polling_interval_minutes: int = 15
    match_threshold_percent: int = 70
    auto_apply: bool = False
    platforms: Dict[str, bool] = Field(default_factory=dict)
    blacklist_companies: List[str] = Field(default_factory=list)
    direct_ats_companies: List[str] = Field(default_factory=list)


class PlatformType(str, Enum):
    RSS = "rss"
    JSON_API = "json_api"
    HTML_SCRAPER = "html_scraper"
    PLUGIN = "plugin"


class CustomPlatformConfig(BaseModel):
    name: str = Field(description="Unique lower-case slug for the platform e.g. 'remoteok', 'weworkremotely'")
    display_name: Optional[str] = None
    platform_type: PlatformType = PlatformType.RSS
    enabled: bool = True
    url_template: str = Field(description="URL or API endpoint with optional {role} and {location} placeholders")
    headers: Dict[str, str] = Field(default_factory=dict)
    field_mappings: Dict[str, str] = Field(
        default_factory=dict,
        description="JSON keys for items, title, company, url, location, description"
    )
    selectors: Dict[str, str] = Field(
        default_factory=dict,
        description="CSS selectors for card, title, company, link, location, description"
    )
    max_items_per_cycle: int = 20
