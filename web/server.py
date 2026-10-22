"""Local Web Server and REST API backend for MCP Autonomous Job Scout & Application System."""
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse, HTMLResponse, Response
from starlette.staticfiles import StaticFiles
from starlette.requests import Request
import uvicorn

from core.database import DatabaseManager
from core.profile_manager import ProfileManager
from core.models import JobListing, ApplicationStatus, CustomPlatformConfig, PlatformType
from core.config import settings, CONFIG_DIR, DATA_DIR
from discovery.aggregator import JobAggregator
from discovery.registry import PlatformRegistry
from applicator.browser import BrowserSessionManager
from applicator.form_filler import ApplicationAgent
from applicator.hitl import HITLNotifier

logger = logging.getLogger("mcp.web")

# Paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Shared Singletons
db = DatabaseManager()
profile_mgr = ProfileManager()
registry = PlatformRegistry()
aggregator = JobAggregator(db, profile_mgr, registry=registry)
hitl = HITLNotifier()
session_mgr = BrowserSessionManager()
agent = ApplicationAgent(db, profile_mgr, session_mgr, hitl)


# -----------------------------------------------------------------------------
# Route Handlers
# -----------------------------------------------------------------------------

async def serve_index(request: Request) -> Response:
    """Serve the single-page application entrypoint."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>MCP Web Interface building in progress...</h1>", status_code=200)
    return HTMLResponse(index_file.read_text(encoding="utf-8"))


async def api_stats(request: Request) -> JSONResponse:
    """Return dashboard analytics and counters."""
    metrics = db.get_stats()
    
    # Calculate high match count (>= candidate threshold)
    threshold = profile_mgr.preferences.match_threshold_percent
    high_match_jobs = db.list_jobs(min_match_score=threshold, limit=1000)
    
    return JSONResponse({
        "total_discovered": metrics.get("total_discovered", 0),
        "total_applied": metrics.get("total_applied", 0),
        "high_match_count": len(high_match_jobs),
        "threshold_percent": threshold,
        "status_breakdown": metrics.get("status_breakdown", {}),
        "platform_breakdown": metrics.get("platform_breakdown", {}),
        "auto_apply_enabled": profile_mgr.preferences.auto_apply
    })


async def api_list_jobs(request: Request) -> JSONResponse:
    """List discovered jobs with search, platform, score, and status filters."""
    query_params = request.query_params
    search = query_params.get("q", "").strip().lower()
    platform = query_params.get("platform")
    status_str = query_params.get("status")
    min_score_str = query_params.get("min_score")
    limit = int(query_params.get("limit", 100))

    status_filter = ApplicationStatus(status_str) if status_str else None
    min_score = int(min_score_str) if min_score_str and min_score_str.isdigit() else None

    # Fetch candidate jobs
    raw_jobs = db.list_jobs(
        status=status_filter,
        platform=platform,
        limit=500,
        min_match_score=min_score
    )

    # Perform text search filtering if specified
    if search:
        filtered = []
        for j in raw_jobs:
            text = f"{j.title} {j.company} {j.location} {j.description or ''}".lower()
            if search in text:
                filtered.append(j)
        jobs = filtered[:limit]
    else:
        jobs = raw_jobs[:limit]

    output = []
    for j in jobs:
        output.append({
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "platform": j.platform,
            "url": j.url,
            "apply_url": j.apply_url or j.url,
            "is_easy_apply": j.is_easy_apply,
            "match_score": j.match_score,
            "match_reasons": j.match_reasons or [],
            "status": j.status.value,
            "discovered_at": j.discovered_at.isoformat() if j.discovered_at else None,
            "description_snippet": (j.description or "")[:280]
        })

    return JSONResponse({"count": len(output), "jobs": output})


async def api_get_job(request: Request) -> JSONResponse:
    """Fetch details of a specific job listing."""
    job_id = request.path_params["job_id"]
    job = db.get_job(job_id)
    if not job:
        return JSONResponse({"error": f"Job '{job_id}' not found"}, status_code=404)

    return JSONResponse({
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "platform": job.platform,
        "url": job.url,
        "apply_url": job.apply_url or job.url,
        "is_easy_apply": job.is_easy_apply,
        "match_score": job.match_score,
        "match_reasons": job.match_reasons or [],
        "status": job.status.value,
        "discovered_at": job.discovered_at.isoformat() if job.discovered_at else None,
        "description": job.description or "No full description provided.",
        "metadata": job.metadata or {}
    })


async def api_evaluate_job(request: Request) -> JSONResponse:
    """Re-evaluate match score for a job."""
    job_id = request.path_params["job_id"]
    job = db.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    score, reasons = profile_mgr.evaluate_fit(job)
    db.update_job_status(job_id, job.status, match_score=score, match_reasons=reasons)
    
    return JSONResponse({
        "job_id": job.id,
        "match_score": score,
        "match_reasons": reasons
    })


async def api_apply_job(request: Request) -> JSONResponse:
    """Execute automated job application."""
    job_id = request.path_params["job_id"]
    job = db.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    try:
        body = await request.json()
    except Exception:
        body = {}

    auto_submit = bool(body.get("auto_submit", False))
    record = await agent.apply(job, auto_submit=auto_submit)

    return JSONResponse({
        "job_id": job.id,
        "status": record.status.value,
        "screenshot_path": record.screenshot_path,
        "notes": record.notes or record.error_message or "Application processed."
    })


async def api_get_profile(request: Request) -> JSONResponse:
    """Retrieve candidate profile and search preferences."""
    profile_mgr.reload()
    return JSONResponse({
        "profile": profile_mgr.profile.model_dump(),
        "preferences": profile_mgr.preferences.model_dump()
    })


async def api_save_profile(request: Request) -> JSONResponse:
    """Save updated candidate profile and preferences to config files."""
    try:
        data = await request.json()
        if "profile" in data:
            with open(profile_mgr.profile_path, "w", encoding="utf-8") as f:
                json.dump(data["profile"], f, indent=2)
        if "preferences" in data:
            with open(profile_mgr.prefs_path, "w", encoding="utf-8") as f:
                json.dump(data["preferences"], f, indent=2)

        profile_mgr.reload()
        return JSONResponse({"success": True, "message": "Profile and preferences updated successfully."})
    except Exception as e:
        logger.error(f"Error saving profile: {e}")
        return JSONResponse({"error": str(e)}, status_code=400)


async def api_get_platforms(request: Request) -> JSONResponse:
    """List all registered platforms."""
    platforms = registry.list_platforms()
    return JSONResponse({"platforms": platforms})


async def api_add_platform(request: Request) -> JSONResponse:
    """Add a new custom job platform."""
    try:
        body = await request.json()
        cfg = CustomPlatformConfig(
            name=body["name"].lower().strip(),
            display_name=body.get("display_name") or body["name"].capitalize(),
            platform_type=PlatformType(body.get("platform_type", "rss")),
            enabled=True,
            url_template=body["url_template"],
            headers=body.get("headers", {}),
            field_mappings=body.get("field_mappings", {}),
            selectors=body.get("selectors", {}),
            max_items_per_cycle=int(body.get("max_items_per_cycle", 25))
        )
        registry.add_custom_platform(cfg)
        return JSONResponse({"success": True, "platform": cfg.model_dump()})
    except Exception as e:
        logger.error(f"Error adding platform: {e}")
        return JSONResponse({"error": str(e)}, status_code=400)


async def api_toggle_platform(request: Request) -> JSONResponse:
    """Enable or disable a platform."""
    name = request.path_params["name"]
    try:
        body = await request.json()
        enabled = bool(body.get("enabled", True))
        success = registry.toggle_platform(name, enabled)
        return JSONResponse({"success": success, "name": name, "enabled": enabled})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


async def api_trigger_scout(request: Request) -> JSONResponse:
    """Trigger a live multi-platform discovery sweep."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    roles = body.get("roles")
    locations = body.get("locations")
    max_age_hours = body.get("max_age_hours", 24)

    summary = await aggregator.run_discovery_cycle(
        roles=roles,
        locations=locations,
        max_age_hours=max_age_hours
    )
    return JSONResponse({"success": True, "summary": summary})


async def api_system_info(request: Request) -> JSONResponse:
    """Return system configuration and baseline model details."""
    db_file = Path(settings.DATABASE_PATH)
    db_size_kb = round(db_file.stat().st_size / 1024, 1) if db_file.exists() else 0

    return JSONResponse({
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "database_path": settings.DATABASE_PATH,
        "database_size_kb": db_size_kb,
        "browser_headless": settings.PLAYWRIGHT_HEADLESS,
        "active_platforms_count": len(registry.providers),
        "target_roles": profile_mgr.preferences.target_roles,
        "polling_interval_minutes": profile_mgr.preferences.polling_interval_minutes
    })


# -----------------------------------------------------------------------------
# Starlette Application Definition
# -----------------------------------------------------------------------------

routes = [
    Route("/", serve_index, methods=["GET"]),
    Route("/api/stats", api_stats, methods=["GET"]),
    Route("/api/jobs", api_list_jobs, methods=["GET"]),
    Route("/api/jobs/{job_id}", api_get_job, methods=["GET"]),
    Route("/api/jobs/{job_id}/evaluate", api_evaluate_job, methods=["POST"]),
    Route("/api/jobs/{job_id}/apply", api_apply_job, methods=["POST"]),
    Route("/api/profile", api_get_profile, methods=["GET"]),
    Route("/api/profile", api_save_profile, methods=["POST"]),
    Route("/api/platforms", api_get_platforms, methods=["GET"]),
    Route("/api/platforms", api_add_platform, methods=["POST"]),
    Route("/api/platforms/{name}/toggle", api_toggle_platform, methods=["POST"]),
    Route("/api/scout", api_trigger_scout, methods=["POST"]),
    Route("/api/system", api_system_info, methods=["GET"]),
    Mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
]

app = Starlette(debug=True, routes=routes)


def run_web_server(host: str = "127.0.0.1", port: int = 8000):
    """Launch the uvicorn ASGI web server."""
    logger.info(f"Starting MCP Web Dashboard at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_web_server()
