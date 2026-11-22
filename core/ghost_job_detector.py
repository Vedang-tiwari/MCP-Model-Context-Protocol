"""Anti-Ghosting and Requisition Liveness Detection Engine.
Strictly adheres to Autonomous Job Application Blueprint §4.1 and §4.2.

Detects and eliminates:
1. Evergreen and generic talent community/pipeline postings (no active hiring).
2. Anonymous, stealth, and phantom staffing agency resume collectors ("Confidential Client").
3. Stale postings (posted > 14 days ago on aggregators or > 30 days on ATS boards).
4. Malformed placeholder URLs (e.g. boards without requisition IDs).
5. Dead / expired requisitions (404, "no longer accepting applications", "position filled").
"""
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List, Dict, Any
from urllib.parse import urlparse
import httpx

from core.models import JobListing

logger = logging.getLogger(__name__)

# Evergreen and talent pool keywords indicating no immediate open requisition
EVERGREEN_KEYWORDS = [
    r"\btalent\s+community\b",
    r"\btalent\s+pool\b",
    r"\bgeneral\s+application\b",
    r"\bfuture\s+opportunities\b",
    r"\bfuture\s+openings\b",
    r"\bevergreen\b",
    r"\bexpression\s+of\s+interest\b",
    r"\bpipeline\s+requisition\b",
    r"\bkeep\s+in\s+touch\b",
    r"\bspeculative\s+application\b",
    r"\bongoing\s+hiring\b",
    r"\bjoin\s+our\s+network\b",
    r"\bopen\s+application\b",
    r"\bbench\s+(candidate|resource)\b",
    r"\bgeneric\s+submission\b",
    r"\bpool\s+requisition\b",
    r"\bproactive\s+pipeline\b"
]

# Anonymous or ghost staffing agency keywords
GHOST_COMPANY_KEYWORDS = [
    r"\bconfidential\b",
    r"\bconfidential\s+client\b",
    r"\bstealth\s+startup\b",
    r"\bundisclosed\b",
    r"\bleading\s+(tech|financial|consulting)\s+firm\b",
    r"\btop\s+tier\s+company\b",
    r"\bfortune\s+500\s+client\b",
    r"\bclient\s+of\b",
    r"\bstaffing\s+solutions\b",
    r"\brecruiting\s+partner\b"
]

# Known dummy/seed companies that were historically hardcoded
KNOWN_DUMMY_COMPANIES = {
    "sprout verified partner",
    "sprout startup network",
    "sprout infrastructure hub",
    "sprout ai ventures",
    "sprout product labs",
    "sprout partner tech",
    "sprout network",
    "technova systems",
    "razorpay direct",
    "innomatrix ai",
    "finflow technologies",
    "dataweave india",
    "beep intelligence lab",
    "novaflow ai",
    "beep enterprise partner",
    "deepsynthese",
    "hypercognition ai",
    "polyflow labs",
    "biconomy ecosystem",
    "ethereum foundation grantee",
    "instadapp",
    "hyperlane",
    "quantmetrics ai",
    "teradata cloud",
    "nielseniq analytics",
    "cognizant data labs",
    "verisk analytics",
    "mosaicml ecosystem",
    "stability ai grantee",
    "weights & biases partner",
    "together ai network",
    "modular ai solutions",
    "frontier ai systems",
    "agentic workforce ai",
    "safeai labs",
    "promptmatrix",
    "neuralforge global",
    "anthropic partner ai",
    "scaleops ai",
    "cerebras systems",
    "cognition ai labs",
    "synthesia ai"
}

# Dead requisition text patterns returned by ATS portals when positions close
DEAD_POSTING_PATTERNS = [
    r"this\s+job\s+is\s+no\s+longer\s+available",
    r"this\s+position\s+has\s+been\s+(closed|filled)",
    r"this\s+posting\s+has\s+expired",
    r"no\s+longer\s+accepting\s+applications",
    r"the\s+job\s+you\s+are\s+looking\s+for\s+has\s+been\s+filled",
    r"position\s+is\s+closed",
    r"requisition\s+(has\s+been\s+)?closed",
    r"job\s+not\s+found",
    r"404\s+-\s+page\s+not\s+found",
    r"we\s+are\s+not\s+currently\s+accepting\s+resumes\s+for\s+this\s+position"
]


class GhostJobVerdict:
    def __init__(self, is_ghost: bool, reasons: Optional[List[str]] = None, risk_score: float = 0.0):
        self.is_ghost = is_ghost
        self.reasons = reasons or []
        self.risk_score = risk_score

    def __bool__(self):
        return not self.is_ghost  # True if job is VALID / NOT a ghost

    def __repr__(self):
        return f"<GhostJobVerdict is_ghost={self.is_ghost} score={self.risk_score} reasons={self.reasons}>"


class GhostJobDetector:
    """Detects ghost, stale, fake, and evergreen job postings with zero tolerance."""

    def __init__(self, max_age_days: int = 14, ats_max_age_days: int = 30):
        self.max_age_days = max_age_days
        self.ats_max_age_days = ats_max_age_days

    def evaluate(self, job: JobListing, max_age_hours: Optional[int] = None) -> GhostJobVerdict:
        """
        Fast, deterministic inspection of a job listing for ghost indicators.
        """
        reasons: List[str] = []
        risk_score = 0.0

        title_lower = (job.title or "").lower().strip()
        comp_lower = (job.company or "").lower().strip()
        desc_lower = (job.description or "").lower().strip()
        url_lower = (job.url or "").lower().strip()

        # 1. Check known dummy / seed companies
        if comp_lower in KNOWN_DUMMY_COMPANIES:
            reasons.append(f"Hardcoded dummy/seed employer: '{job.company}'")
            return GhostJobVerdict(is_ghost=True, reasons=reasons, risk_score=1.0)

        # 2. Check ghost / anonymous employer keywords
        for pat in GHOST_COMPANY_KEYWORDS:
            if re.search(pat, comp_lower):
                reasons.append(f"Anonymous or staffing harvester employer: '{job.company}'")
                risk_score += 0.6
                break

        # 3. Check evergreen / talent pool requisition patterns
        for pat in EVERGREEN_KEYWORDS:
            if re.search(pat, title_lower):
                reasons.append(f"Title indicates an evergreen or pipeline requisition (not an active opening)")
                risk_score += 0.8
                break
            elif re.search(pat, desc_lower[:600]):
                reasons.append(f"Description indicates an ongoing talent pool / expression of interest")
                risk_score += 0.5
                break

        # 4. Check URL validity and placeholder patterns
        parsed = urlparse(job.url or "")
        path = parsed.path.rstrip("/")
        if not path or path in ["", "/jobs", "/job", "/careers", "/career"]:
            # URL does not point to a specific requisition
            reasons.append(f"Generic career board URL without a specific requisition ID: '{job.url}'")
            risk_score += 0.7

        if "lever.co/stripe/job" in url_lower:
            reasons.append("Malformed generic placeholder URL")
            risk_score += 1.0

        if "usesprout.com/jobs/" in url_lower and not any(c.isdigit() for c in path):
            reasons.append("Unverified placeholder slug on sprout without requisition ID")
            risk_score += 0.7

        # 5. Check Posting Age & Freshness
        if job.posted_at:
            now = datetime.now(timezone.utc)
            posted_dt = job.posted_at
            if posted_dt.tzinfo is None:
                posted_dt = posted_dt.replace(tzinfo=timezone.utc)

            age = now - posted_dt
            allowed_days = self.ats_max_age_days if job.platform == "ats_direct" else self.max_age_days

            if max_age_hours:
                allowed_hours = max_age_hours
            else:
                allowed_hours = allowed_days * 24

            if age > timedelta(hours=allowed_hours):
                age_days = round(age.total_seconds() / 86400, 1)
                reasons.append(f"Stale requisition: posted {age_days} days ago (exceeds {allowed_days} day limit)")
                risk_score += 0.6

        is_ghost = risk_score >= 0.5 or len(reasons) > 0
        return GhostJobVerdict(is_ghost=is_ghost, reasons=reasons, risk_score=min(1.0, risk_score))

    async def verify_liveness(self, url: str) -> Tuple[bool, str]:
        """
        Actively checks if a job requisition URL is live on the web and accepting applications.
        Returns (is_live: bool, message: str).
        """
        if not url or not url.startswith("http"):
            return False, "Invalid or missing URL scheme"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        try:
            async with httpx.AsyncClient(headers=headers, timeout=5.0, follow_redirects=True) as client:
                res = await client.get(url)

                if res.status_code in [404, 410]:
                    return False, f"Requisition closed or page not found (HTTP {res.status_code})"

                if res.status_code >= 400:
                    return False, f"Job portal returned error status (HTTP {res.status_code})"

                # Inspect HTML content for dead requisition phrases
                page_text = res.text[:20000].lower()
                for pat in DEAD_POSTING_PATTERNS:
                    if re.search(pat, page_text):
                        return False, "Job portal explicitly states the position is closed or no longer accepting applications"

                return True, "Requisition is live and accessible"

        except Exception as e:
            logger.debug(f"Liveness verification check encountered error for {url}: {e}")
            # Network timeout or block; do not drop if server was just slow, but note error
            return True, f"Liveness check passed with caution: {e}"
