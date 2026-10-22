"""Model Context Protocol (MCP) Server for Job Scout & Autonomous Application Agent."""
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
try:
    from mcp.server import MCPServer as FastMCP
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        from fastmcp import FastMCP

from core.database import DatabaseManager
from core.profile_manager import ProfileManager
from core.models import ApplicationStatus
from discovery.aggregator import JobAggregator
from applicator.browser import BrowserSessionManager
from applicator.form_filler import ApplicationAgent
from applicator.hitl import HITLNotifier

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_server")

# Initialize FastMCP Server
mcp = FastMCP("JobApplicationAgentMCP")

# Core dependencies
db = DatabaseManager()
profile_mgr = ProfileManager()
hitl = HITLNotifier()
session_mgr = BrowserSessionManager()
aggregator = JobAggregator(db, profile_mgr)
agent = ApplicationAgent(db, profile_mgr, session_mgr, hitl)


@mcp.tool()
async def search_recent_jobs(
    roles: Optional[List[str]] = None,
    platform: Optional[str] = None,
    min_match_score: Optional[int] = None,
    trigger_live_crawl: bool = False,
    limit: int = 15
) -> str:
    """
    Search recently discovered jobs matching preferred roles.
    If trigger_live_crawl is True, immediately initiates a real-time web sweep across LinkedIn, Indeed, ATS direct feeds, Naukri, and Wellfound.
    """
    if trigger_live_crawl:
        logger.info("Triggering live crawl across enabled job platforms...")
        summary = await aggregator.run_discovery_cycle(roles=roles)
        crawl_info = f"Live crawl completed: {summary['new_unique_jobs']} new jobs discovered.\n\n"
    else:
        crawl_info = ""

    jobs = db.list_jobs(
        status=None,
        platform=platform,
        limit=limit,
        min_match_score=min_match_score
    )

    if not jobs:
        return f"{crawl_info}No jobs found matching criteria. Consider running with trigger_live_crawl=True."

    output = [f"{crawl_info}### Recent Discovered Jobs ({len(jobs)} shown):\n"]
    for j in jobs:
        score_str = f" [Match: {j.match_score}%]" if j.match_score is not None else ""
        easy_str = " (⚡ Easy Apply)" if j.is_easy_apply else ""
        output.append(
            f"- **[{j.id}]** **{j.title}** at **{j.company}** ({j.location}) | Platform: `{j.platform}`{score_str}{easy_str}\n"
            f"  Status: `{j.status.value}` | URL: {j.url}"
        )

    return "\n".join(output)


@mcp.tool()
async def evaluate_job_fit(job_id: str) -> str:
    """
    Evaluates compatibility between the candidate's profile and a specific job posting.
    Returns match percentage, matched skills, role alignment, and recommendation.
    """
    job = db.get_job(job_id)
    if not job:
        return f"Error: Job with ID '{job_id}' not found in database."

    score, reasons = profile_mgr.evaluate_fit(job)
    db.update_job_status(job_id, job.status, match_score=score, match_reasons=reasons)

    reasons_formatted = "\n".join([f"- {r}" for r in reasons])
    verdict = "🔥 STRONG FIT - Recommended for Immediate Application" if score >= 75 else (
        "⚖️ MODERATE FIT - Review Details" if score >= 50 else "❌ LOW FIT - Not Recommended"
    )

    return (
        f"### Job Fit Evaluation for '{job.title}' at '{job.company}'\n"
        f"**Match Score**: {score} / 100 ({verdict})\n\n"
        f"**Evaluation Breakdown**:\n{reasons_formatted}\n\n"
        f"**Apply URL**: {job.apply_url or job.url}"
    )


@mcp.tool()
async def apply_to_job(job_id: str, auto_submit: bool = False) -> str:
    """
    Executes automated job application submission via stealth browser.
    Fills standard credentials, answers screening questions via LLM knowledge base, and uploads resume.
    Set auto_submit=True to submit the form, or False for pre-filling with manual final confirmation.
    """
    job = db.get_job(job_id)
    if not job:
        return f"Error: Job with ID '{job_id}' not found."

    record = await agent.apply(job, auto_submit=auto_submit)

    status_emoji = "✅" if record.status == ApplicationStatus.APPLIED else "⚠️"
    return (
        f"{status_emoji} **Application Status for '{job.title}' at '{job.company}'**: `{record.status.value}`\n"
        f"- Target URL: {job.apply_url or job.url}\n"
        f"- Screenshot Evidence: `{record.screenshot_path or 'None'}`\n"
        f"- Questions Answered: {len(record.answers_submitted)}\n"
        f"- Notes: {record.notes or record.error_message or 'Submitted successfully'}"
    )


@mcp.tool()
async def get_application_status() -> str:
    """
    Retrieves real-time analytics and tracking status of all job discoveries and submitted applications.
    """
    stats = db.get_stats()
    breakdown = stats.get("status_breakdown", {})
    platforms = stats.get("platform_breakdown", {})

    status_str = "\n".join([f"  - `{k}`: {v}" for k, v in breakdown.items()])
    platform_str = "\n".join([f"  - `{k}`: {v}" for k, v in platforms.items()])

    return (
        f"### 📊 Application & Discovery Dashboard\n\n"
        f"- **Total Discovered Jobs**: {stats.get('total_discovered', 0)}\n"
        f"- **Total Applications Submitted**: {stats.get('total_applied', 0)}\n\n"
        f"**Status Breakdown**:\n{status_str or '  - None yet'}\n\n"
        f"**Platforms Breakdown**:\n{platform_str or '  - None yet'}"
    )


@mcp.tool()
async def get_candidate_profile() -> str:
    """
    Returns the current candidate profile, credentials, and configured search preferences.
    """
    p = profile_mgr.profile
    prefs = profile_mgr.preferences
    return (
        f"### 👤 Candidate Profile\n"
        f"- **Name**: {p.personal_info.full_name} ({p.personal_info.email})\n"
        f"- **Location**: {p.personal_info.current_city}, {p.personal_info.country}\n"
        f"- **Experience**: {p.standard_answers.years_of_experience} years | Notice: {p.standard_answers.notice_period_days} days\n"
        f"- **Target Roles**: {', '.join(prefs.target_roles)}\n"
        f"- **Preferred Locations**: {', '.join(prefs.locations)}\n"
        f"- **Auto-Apply Enabled**: {prefs.auto_apply} (Threshold: {prefs.match_threshold_percent}%)\n"
        f"- **Resume File**: `{p.resume_file_path}`"
    )


@mcp.tool()
async def list_job_platforms() -> str:
    """
    Lists all active job platforms, including built-in providers, custom declarative platforms, and plugins.
    """
    platforms = aggregator.registry.list_platforms()
    lines = ["### 🌐 Available Job Platforms\n"]
    for p in platforms:
        status_icon = "🟢" if p["enabled"] else "⚪"
        lines.append(
            f"- {status_icon} **{p['display_name']}** (`{p['name']}`) | Type: `{p['type']}` | Source: `{p['source']}`"
        )
        if "url_template" in p:
            lines.append(f"  URL: `{p['url_template']}`")
    return "\n".join(lines)


@mcp.tool()
async def add_custom_job_platform(
    name: str,
    platform_type: str,
    url_template: str,
    display_name: Optional[str] = None,
    field_mappings: Optional[Dict[str, str]] = None,
    selectors: Optional[Dict[str, str]] = None
) -> str:
    """
    Add a new job platform dynamically. Supports:
    - 'rss': Provide url_template e.g. 'https://remoteok.com/remote-jobs.rss'
    - 'json_api': Provide endpoint with optional field_mappings (e.g. items, title, company, url, location)
    - 'html_scraper': Provide url_template with selectors (card, title, company, link)
    """
    from core.models import CustomPlatformConfig, PlatformType

    try:
        ptype = PlatformType(platform_type.lower())
    except ValueError:
        return f"Error: Invalid platform_type '{platform_type}'. Must be 'rss', 'json_api', or 'html_scraper'."

    cfg = CustomPlatformConfig(
        name=name.lower().strip(),
        display_name=display_name or name.capitalize(),
        platform_type=ptype,
        enabled=True,
        url_template=url_template,
        field_mappings=field_mappings or {},
        selectors=selectors or {}
    )

    success = aggregator.registry.add_custom_platform(cfg)
    if success:
        return f"✅ Platform '{cfg.display_name}' (`{cfg.name}`) successfully registered and enabled for 24/7 discovery!"
    return f"Failed to register platform '{name}'."


@mcp.tool()
async def toggle_job_platform(name: str, enabled: bool) -> str:
    """
    Enables or disables a job platform by name.
    """
    success = aggregator.registry.toggle_platform(name.lower().strip(), enabled)
    if success:
        state = "enabled" if enabled else "disabled"
        return f"Platform '{name}' is now {state}."
    return f"Platform '{name}' not found."


@mcp.prompt()
def generate_cover_letter_prompt(job_id: str) -> str:
    """Prompt template for synthesizing a tailored cover letter based on candidate profile and job description."""
    job = db.get_job(job_id)
    job_desc = job.description if job else "N/A"
    job_title = job.title if job else "Software Engineer"
    company = job.company if job else "Hiring Company"

    return (
        f"Write a concise, compelling 3-paragraph cover letter for the role of '{job_title}' at '{company}'.\n"
        f"Highlight specific achievements from the candidate profile that directly solve requirements in the job description.\n\n"
        f"CANDIDATE PROFILE:\n{profile_mgr.format_profile_for_llm()}\n\n"
        f"JOB DESCRIPTION:\n{job_desc}"
    )


if __name__ == "__main__":
    # Run FastMCP server
    mcp.run()
