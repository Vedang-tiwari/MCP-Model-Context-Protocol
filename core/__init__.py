"""Core module for MCP Job Application Agent."""
from .models import JobListing, ApplicationRecord, CandidateProfile, ApplicationStatus, SearchPreferences
from .database import DatabaseManager

__all__ = [
    "JobListing",
    "ApplicationRecord",
    "CandidateProfile",
    "ApplicationStatus",
    "SearchPreferences",
    "DatabaseManager"
]
