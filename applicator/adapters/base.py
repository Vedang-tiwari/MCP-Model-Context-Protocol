"""Base protocols and data contracts for the Apply Executor Strategy Pattern (§4.4)."""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Protocol
from core.models import JobListing, ApplicationStatus


@dataclass
class ApplyPlan:
    job: JobListing
    adapter_name: str
    target_url: str
    fields: Dict[str, Any] = field(default_factory=dict)
    resume_path: Optional[str] = None
    cover_letter: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApplyResult:
    job_id: str
    status: ApplicationStatus
    confirmed: bool = False
    needs_human: bool = False
    evidence: Optional[str] = None           # Confirmation ID, proof screenshot path, or API response
    screenshot_path: Optional[str] = None
    notes: Optional[str] = None
    error: Optional[str] = None
    questions: List[Dict[str, Any]] = field(default_factory=list)


class ApplyAdapter(Protocol):
    def can_handle(self, job: JobListing) -> bool:
        """Determines if this adapter can process the given job listing."""
        ...

    async def prepare(self, job: JobListing, artifacts: Optional[Any] = None) -> ApplyPlan:
        """Inspects job and synthesizes an application submission plan."""
        ...

    async def submit(self, plan: ApplyPlan, *, dry_run: bool = False, auto_submit: bool = False) -> ApplyResult:
        """Executes the application plan, returning confirmation evidence or human escalation."""
        ...
