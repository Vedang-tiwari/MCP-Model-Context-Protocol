"""Local Web Server and REST API backend for MCP Autonomous Job Scout & Application System."""
import os
import re
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

import asyncio
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse, HTMLResponse, Response, FileResponse
from starlette.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
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
from core.resume_tailor_agent import ResumeTailorAgent
from core.resume_docx_renderer import ResumeDocxRenderer

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
tailor_agent = ResumeTailorAgent(profile_mgr=profile_mgr)
docx_renderer = ResumeDocxRenderer()


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
        "fresh_jobs_count": metrics.get("fresh_jobs_count", 0),
        "threshold_percent": threshold,
        "status_breakdown": metrics.get("status_breakdown", {}),
        "platform_breakdown": metrics.get("platform_breakdown", {}),
        "auto_apply_enabled": profile_mgr.preferences.auto_apply
    })


async def api_list_jobs(request: Request) -> JSONResponse:
    """List discovered jobs with search, platform, score, freshness, pagination, and exclude filters."""
    query_params = request.query_params
    search = query_params.get("q", "").strip().lower()
    platform = query_params.get("platform")
    status_str = query_params.get("status")
    min_score_str = query_params.get("min_score")
    fresh_only_param = query_params.get("fresh_only", "").lower()
    fresh_only = fresh_only_param in ("true", "1", "yes")
    sort_by = query_params.get("sort_by", "fresh_first")
    if sort_by == "fresh_only":
        fresh_only = True
    limit = int(query_params.get("limit", 100))
    offset = int(query_params.get("offset", 0))

    exclude_ids_raw = query_params.get("exclude_ids", "").strip()
    exclude_ids = [i.strip() for i in exclude_ids_raw.split(",") if i.strip()] if exclude_ids_raw else None

    status_filter = ApplicationStatus(status_str) if status_str else None
    min_score = int(min_score_str) if min_score_str and min_score_str.isdigit() else None

    # Fetch candidate jobs with fresh <= 24h prioritized on first place
    raw_jobs = db.list_jobs(
        status=status_filter,
        platform=platform,
        limit=1000,
        min_match_score=min_score,
        fresh_only=fresh_only,
        prioritize_fresh=True,
        exclude_ids=exclude_ids
    )

    # Perform text search filtering if specified
    if search:
        filtered = []
        for j in raw_jobs:
            text = f"{j.title} {j.company} {j.location} {j.salary or ''} {j.description or ''}".lower()
            if search in text:
                filtered.append(j)
        jobs = filtered
    else:
        jobs = raw_jobs

    if fresh_only:
        jobs = [j for j in jobs if j.is_fresh_24h]

    # Ordering: Keep fresh jobs (<= 24 hrs) strictly on first place
    if sort_by in ("fresh_first", "fresh_only"):
        jobs = sorted(
            jobs,
            key=lambda j: (1 if j.is_fresh_24h else 0, j.match_score or 0, -j.age_hours),
            reverse=True
        )
    elif sort_by == "score_desc":
        jobs = sorted(
            jobs,
            key=lambda j: (j.match_score or 0, 1 if j.is_fresh_24h else 0, -j.age_hours),
            reverse=True
        )
    elif sort_by == "newest":
        jobs = sorted(
            jobs,
            key=lambda j: -j.age_hours,
            reverse=True
        )

    total_unseen = len(jobs)
    total_matching = db.count_jobs(
        status=status_filter,
        platform=platform,
        min_match_score=min_score,
        fresh_only=fresh_only
    )

    paged_jobs = jobs[offset:offset + limit]

    output = []
    for j in paged_jobs:
        output.append({
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "platform": j.platform,
            "url": j.url,
            "apply_url": j.apply_url or j.url,
            "salary": j.salary,
            "is_easy_apply": j.is_easy_apply,
            "match_score": j.match_score,
            "match_reasons": j.match_reasons or [],
            "status": j.status.value,
            "posted_at": j.posted_at.isoformat() if j.posted_at else None,
            "discovered_at": j.discovered_at.isoformat() if j.discovered_at else None,
            "is_fresh": j.is_fresh_24h,
            "age_hours": round(j.age_hours, 1),
            "age_display": j.age_display,
            "description_snippet": (j.description or "")[:280]
        })

    return JSONResponse({
        "count": len(output),
        "total_unseen_remaining": max(0, total_unseen - offset - len(output)),
        "total_matching": total_matching,
        "offset": offset,
        "limit": limit,
        "has_more": (offset + len(output)) < total_unseen,
        "fresh_count": sum(1 for item in output if item["is_fresh"]),
        "jobs": output
    })


async def api_refresh_unseen_jobs(request: Request) -> JSONResponse:
    """
    Refresh feed by fetching new unseen jobs, optionally executing a live discovery sweep first.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    exclude_ids = body.get("exclude_ids", [])
    platform = body.get("platform")
    if isinstance(platform, str) and platform.strip().lower() in ["all", "none", "null", ""]:
        platform = None
    fresh_only = bool(body.get("fresh_only", False))
    sort_by = body.get("sort_by", "fresh_first")
    limit = int(body.get("limit", 100))
    run_live_sweep = bool(body.get("run_live_sweep", False))
    search = str(body.get("q", "")).strip().lower()
    min_score = body.get("min_score")
    if min_score is not None:
        try:
            min_score = int(min_score)
        except ValueError:
            min_score = None

    new_swept_count = 0
    sweep_summary = None

    if run_live_sweep:
        profile_mgr.reload()
        roles = body.get("roles") or profile_mgr.preferences.target_roles
        try:
            sweep_summary = await aggregator.run_discovery_cycle(
                roles=roles,
                max_age_hours=24,
                platform=platform
            )
            new_swept_count = sweep_summary.get("new_unique_jobs", 0)
        except Exception as e:
            logger.warning(f"Live sweep during refresh encountered non-fatal error: {e}")

    # Query unseen jobs excluding already-seen IDs
    raw_jobs = db.list_jobs(
        platform=platform,
        limit=1000,
        min_match_score=min_score,
        fresh_only=fresh_only,
        prioritize_fresh=True,
        exclude_ids=exclude_ids
    )

    if search:
        jobs = [j for j in raw_jobs if search in f"{j.title} {j.company} {j.location} {j.salary or ''} {j.description or ''}".lower()]
    else:
        jobs = raw_jobs

    if fresh_only:
        jobs = [j for j in jobs if j.is_fresh_24h]

    if sort_by in ("fresh_first", "fresh_only"):
        jobs = sorted(
            jobs,
            key=lambda j: (1 if j.is_fresh_24h else 0, j.match_score or 0, -j.age_hours),
            reverse=True
        )
    elif sort_by == "score_desc":
        jobs = sorted(
            jobs,
            key=lambda j: (j.match_score or 0, 1 if j.is_fresh_24h else 0, -j.age_hours),
            reverse=True
        )
    elif sort_by == "newest":
        jobs = sorted(jobs, key=lambda j: -j.age_hours, reverse=True)

    total_unseen_count = len(jobs)
    selected_jobs = jobs[:limit]

    output = []
    for j in selected_jobs:
        output.append({
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "platform": j.platform,
            "url": j.url,
            "apply_url": j.apply_url or j.url,
            "salary": j.salary,
            "is_easy_apply": j.is_easy_apply,
            "match_score": j.match_score,
            "match_reasons": j.match_reasons or [],
            "status": j.status.value,
            "posted_at": j.posted_at.isoformat() if j.posted_at else None,
            "discovered_at": j.discovered_at.isoformat() if j.discovered_at else None,
            "is_fresh": j.is_fresh_24h,
            "age_hours": round(j.age_hours, 1),
            "age_display": j.age_display,
            "description_snippet": (j.description or "")[:280]
        })

    return JSONResponse({
        "success": True,
        "new_swept_count": new_swept_count,
        "sweep_summary": sweep_summary,
        "count": len(output),
        "total_unseen_remaining": max(0, total_unseen_count - len(output)),
        "has_more": total_unseen_count > len(output),
        "fresh_count": sum(1 for item in output if item["is_fresh"]),
        "jobs": output
    })


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
        "salary": job.salary,
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
    """Execute automated job application with optional background task resilience."""
    job_id = request.path_params["job_id"]
    job = db.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    try:
        body = await request.json()
    except Exception:
        body = {}

    auto_submit = bool(body.get("auto_submit", False))
    async_mode = bool(body.get("async", False))

    if async_mode:
        # Background mode: start immediately and return status for live polling
        agent._update_task(job.id, "Application queued for execution...", 5, is_active=True)
        asyncio.create_task(agent.apply(job, auto_submit=auto_submit))
        mode_text = "Auto-Submit" if auto_submit else "Pre-fill (Review Mode)"
        return JSONResponse({
            "success": True,
            "job_id": job.id,
            "status": "APPLYING",
            "notes": f"Autonomous agent initiated ({mode_text}).",
            "stage": "Initializing stealth browser session..."
        })

    try:
        record = await agent.apply(job, auto_submit=auto_submit)
        return JSONResponse({
            "job_id": job.id,
            "status": record.status.value,
            "screenshot_path": record.screenshot_path,
            "notes": record.notes or record.error_message or "Application processed."
        })
    except Exception as e:
        logger.error(f"Error applying to job {job_id}: {e}", exc_info=True)
        return JSONResponse({
            "error": f"Application agent error: {str(e)}",
            "job_id": job.id,
            "status": "FAILED"
        }, status_code=500)


async def api_job_apply_status(request: Request) -> JSONResponse:
    """Returns live apply progress, stage, and completion status for a job."""
    job_id = request.path_params["job_id"]
    job = db.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    task_info = agent.active_tasks.get(job_id, {})
    return JSONResponse({
        "job_id": job.id,
        "status": job.status.value,
        "stage": task_info.get("stage", "Idle"),
        "progress": task_info.get("progress", 0),
        "is_active": task_info.get("is_active", False),
        "notes": task_info.get("notes") or "",
        "screenshot_path": task_info.get("screenshot_path"),
        "updated_at": task_info.get("updated_at")
    })


async def api_batch_apply_jobs(request: Request) -> JSONResponse:
    """Execute autonomous batch applications simultaneously across multiple jobs."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    job_ids = body.get("job_ids", [])
    auto_submit = bool(body.get("auto_submit", True))
    max_concurrency = int(body.get("max_concurrency", 3))
    async_mode = bool(body.get("async", False))

    jobs_to_apply = []
    if job_ids:
        for jid in job_ids:
            j = db.get_job(jid)
            if j:
                jobs_to_apply.append(j)
    else:
        all_jobs = db.list_jobs(limit=50)
        jobs_to_apply = [j for j in all_jobs if j.status in (ApplicationStatus.DISCOVERED, ApplicationStatus.EVALUATED, ApplicationStatus.QUEUED, ApplicationStatus.MANUAL_REVIEW)]

    if not jobs_to_apply:
        return JSONResponse({"error": "No eligible jobs found to apply.", "total": 0}, status_code=400)

    # Prioritize fresh jobs (<= 24 hours) on first place
    jobs_to_apply.sort(key=lambda j: (1 if j.is_fresh_24h else 0, j.match_score or 0, -j.age_hours), reverse=True)

    if async_mode:
        asyncio.create_task(agent.batch_apply(jobs_to_apply, auto_submit=auto_submit, max_concurrency=max_concurrency))
        return JSONResponse({
            "success": True,
            "total": len(jobs_to_apply),
            "message": f"Autonomous batch apply initiated for {len(jobs_to_apply)} jobs in background.",
            "auto_submit": auto_submit
        })

    try:
        results = await agent.batch_apply(jobs_to_apply, auto_submit=auto_submit, max_concurrency=max_concurrency)
        applied_count = sum(1 for r in results if r.status in (ApplicationStatus.APPLIED, ApplicationStatus.SUBMITTED))
        review_count = sum(1 for r in results if r.status in (ApplicationStatus.MANUAL_REVIEW, ApplicationStatus.READY_FOR_REVIEW, ApplicationStatus.NEEDS_HUMAN))
        failed_count = sum(1 for r in results if r.status == ApplicationStatus.FAILED)

        return JSONResponse({
            "success": True,
            "total": len(results),
            "applied": applied_count,
            "manual_review": review_count,
            "failed": failed_count,
            "results": [
                {
                    "job_id": r.job_id,
                    "status": r.status.value,
                    "notes": r.notes or r.error_message,
                    "screenshot_path": r.screenshot_path
                }
                for r in results
            ]
        })
    except Exception as e:
        logger.error(f"Batch application error: {e}", exc_info=True)
        return JSONResponse({"error": f"Batch application failed: {str(e)}"}, status_code=500)


async def api_batch_apply_status(request: Request) -> JSONResponse:
    """Returns active batch execution progress and metrics."""
    return JSONResponse(agent.batch_state)


async def api_job_history(request: Request) -> JSONResponse:
    """Returns state transition audit history for a specific job (§1 & §3.3)."""
    job_id = request.path_params["job_id"]
    history = db.get_state_history(job_id)
    return JSONResponse({"job_id": job_id, "history": history})


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


async def api_get_resumes(request: Request) -> JSONResponse:
    """Retrieve all role-mapped resumes."""
    profile_mgr.reload()
    items = []
    for r in profile_mgr.profile.role_resumes:
        path = Path(r.file_path)
        items.append({
            "id": r.id,
            "role_pattern": r.role_pattern,
            "file_name": r.file_name,
            "file_size_kb": r.file_size_kb,
            "uploaded_at": r.uploaded_at,
            "is_default": r.is_default,
            "exists": path.exists()
        })
    return JSONResponse({"resumes": items, "count": len(items)})


async def api_upload_resume(request: Request) -> JSONResponse:
    """Upload and register a role-mapped resume file."""
    import re
    try:
        form = await request.form()
        file_obj = form.get("file")
        role = str(form.get("role", "")).strip()
        is_default = str(form.get("is_default", "false")).lower() in ("true", "1", "yes")

        if not file_obj or not hasattr(file_obj, "filename") or not file_obj.filename:
            return JSONResponse({"error": "No file uploaded"}, status_code=400)

        if not role:
            return JSONResponse({"error": "Designated role pattern is required"}, status_code=400)

        upload_dir = Path("data/resumes")
        upload_dir.mkdir(parents=True, exist_ok=True)

        original_name = Path(file_obj.filename).name
        role_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', role.lower()).strip('_')
        suffix = Path(original_name).suffix.lower() or ".pdf"
        dest_filename = f"resume_{role_slug}{suffix}"
        dest_path = upload_dir / dest_filename

        content = await file_obj.read()
        dest_path.write_bytes(content)

        mapping = profile_mgr.add_role_resume(
            file_path=str(dest_path),
            role_pattern=role,
            original_filename=original_name,
            is_default=is_default
        )

        return JSONResponse({"success": True, "resume": mapping.model_dump()})

    except Exception as e:
        logger.error(f"Resume upload failed: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_delete_resume(request: Request) -> JSONResponse:
    """Delete a role resume mapping."""
    resume_id = request.path_params["resume_id"]
    success = profile_mgr.remove_role_resume(resume_id)
    if success:
        return JSONResponse({"success": True, "message": f"Resume mapping '{resume_id}' removed"})
    return JSONResponse({"error": f"Resume mapping '{resume_id}' not found"}, status_code=404)


async def api_download_resume(request: Request) -> Response:
    """Download or preview a stored resume."""
    resume_id = request.path_params["resume_id"]
    mapping = profile_mgr.get_resume_by_id(resume_id)
    if not mapping:
        return JSONResponse({"error": "Resume not found"}, status_code=404)

    path = Path(mapping.file_path)
    if not path.exists():
        return JSONResponse({"error": "File does not exist on disk"}, status_code=404)

    media_type = "application/pdf" if path.suffix.lower() == ".pdf" else "application/octet-stream"
    return FileResponse(path=str(path), media_type=media_type, filename=mapping.file_name)


async def api_tailor_job_resume(request: Request) -> JSONResponse:
    """Tailor a candidate resume specifically for a discovered job."""
    job_id = request.path_params["job_id"]
    job = db.get_job(job_id)
    if not job:
        return JSONResponse({"error": f"Job '{job_id}' not found."}, status_code=404)

    try:
        body = {}
        if request.headers.get("content-type") == "application/json":
            try:
                body = await request.json()
            except Exception:
                body = {}

        generate_pdf = body.get("generate_pdf", True)
        artifacts = await tailor_agent.tailor_for_job(job, generate_pdf=generate_pdf)

        # Update metadata in database
        meta_updates = {
            "tailored_resume_pdf": artifacts.pdf_path,
            "tailored_resume_docx": artifacts.docx_path,
            "tailored_resume_text": artifacts.text_path,
            "tailored_cover_letter": artifacts.cover_letter,
            "tailored_summary": artifacts.summary,
            "tailored_match_analysis": artifacts.match_analysis,
            "tailored_at": datetime.now(timezone.utc).isoformat()
        }
        db.update_job_metadata(job_id, meta_updates)

        # Update state to TAILORED if currently DISCOVERED or SHORTLISTED
        if job.status in [ApplicationStatus.DISCOVERED, ApplicationStatus.SHORTLISTED]:
            db.update_job_status(
                job_id,
                ApplicationStatus.TAILORED,
                actor="ResumeTailorAgent",
                evidence=artifacts.docx_path or artifacts.pdf_path or artifacts.text_path,
                notes=f"Tailored resume generated. Audit: {'PASSED' if artifacts.audit_passed else 'VIOLATIONS'}"
            )

        return JSONResponse({
            "success": True,
            "artifacts": artifacts.to_dict()
        })
    except Exception as e:
        logger.error(f"Tailoring failed for job '{job_id}': {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_get_template_resume(request: Request) -> JSONResponse:
    """Return the official candidate resume template data and structure."""
    data = docx_renderer.get_default_template_data()
    return JSONResponse({
        "success": True,
        "template_name": "mcp-resume-template.docx",
        "candidate_name": data.get("full_name"),
        "template_data": data
    })


async def api_download_template_resume(request: Request) -> Response:
    """Download the official blank/base candidate Word resume template."""
    tmpl_path = Path("data/templates/mcp-resume-template.docx")
    if not tmpl_path.exists():
        docx_renderer._ensure_template_exists()
    return FileResponse(
        str(tmpl_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="mcp-resume-template.docx"
    )


async def api_get_job_custom_resume(request: Request) -> JSONResponse:
    """Fetch current customized or tailored resume data for a specific job."""
    job_id = request.path_params["job_id"]
    job = db.get_job(job_id)
    if not job:
        return JSONResponse({"error": f"Job '{job_id}' not found."}, status_code=404)

    # 1. Check if previously customized by user
    custom_saved = job.metadata.get("custom_resume") if isinstance(job.metadata, dict) else None
    if custom_saved:
        return JSONResponse({
            "job_id": job.id,
            "job_title": job.title,
            "company": job.company,
            "match_score": job.match_score,
            "is_customized": True,
            "resume_data": custom_saved,
            "docx_url": f"/api/jobs/{job.id}/custom-resume/download",
            "cover_letter": job.metadata.get("tailored_cover_letter", "")
        })

    # 2. Check if already tailored by agent
    tailored_summary = job.metadata.get("tailored_summary") if isinstance(job.metadata, dict) else None
    cover_letter = job.metadata.get("tailored_cover_letter", "") if isinstance(job.metadata, dict) else ""

    if not tailored_summary:
        try:
            artifacts = await tailor_agent.tailor_for_job(job, generate_pdf=False)
            db.update_job_metadata(job.id, {
                "tailored_summary": artifacts.summary,
                "tailored_cover_letter": artifacts.cover_letter,
                "tailored_resume_docx": artifacts.docx_path,
                "tailored_resume_text": artifacts.text_path
            })
            tailored_summary = artifacts.summary
            cover_letter = artifacts.cover_letter
        except Exception as e:
            logger.warning(f"Initial tailoring draft fallback for {job.id}: {e}")
            tailored_summary = None

    base_data = docx_renderer.get_default_template_data()
    if tailored_summary:
        base_data["objective"] = tailored_summary

    return JSONResponse({
        "job_id": job.id,
        "job_title": job.title,
        "company": job.company,
        "match_score": job.match_score,
        "is_customized": False,
        "resume_data": base_data,
        "docx_url": f"/api/jobs/{job.id}/custom-resume/download",
        "cover_letter": cover_letter
    })


async def api_save_job_custom_resume(request: Request) -> JSONResponse:
    """Save user's manual edits to a resume for a specific job and regenerate .docx and .txt."""
    job_id = request.path_params["job_id"]
    job = db.get_job(job_id)
    if not job:
        return JSONResponse({"error": f"Job '{job_id}' not found."}, status_code=404)

    try:
        body = await request.json()
        resume_data = body.get("resume_data") or body
        cover_letter = body.get("cover_letter") or resume_data.get("cover_letter", "")

        safe_comp = re.sub(r'[^a-zA-Z0-9_]', '', job.company.replace(" ", "_"))
        safe_role = re.sub(r'[^a-zA-Z0-9_]', '', job.title.replace(" ", "_"))
        base_name = f"custom_Vedang_Tiwari_{safe_comp}_{safe_role}_{job.id[:8]}"

        docx_path = f"data/artifacts/{base_name}.docx"
        txt_path = f"data/artifacts/{base_name}.txt"

        rendered_docx = docx_renderer.render(resume_data, docx_path)
        plain_text = docx_renderer.render_plain_text(resume_data)
        Path(txt_path).write_text(plain_text, encoding="utf-8")

        meta_updates = {
            "custom_resume": resume_data,
            "custom_resume_docx": rendered_docx,
            "custom_resume_text": txt_path,
            "tailored_summary": resume_data.get("objective", ""),
            "tailored_cover_letter": cover_letter,
            "custom_resume_updated_at": datetime.now(timezone.utc).isoformat()
        }
        db.update_job_metadata(job_id, meta_updates)

        if job.status in [ApplicationStatus.DISCOVERED, ApplicationStatus.SHORTLISTED, ApplicationStatus.FILTERED_OUT]:
            db.update_job_status(
                job_id,
                ApplicationStatus.TAILORED,
                actor="User (Manual Resume Edit)",
                evidence=rendered_docx,
                notes=f"User customized resume for '{job.title}' at '{job.company}'"
            )

        return JSONResponse({
            "success": True,
            "message": f"Custom resume saved and generated for '{job.title}' at '{job.company}'.",
            "docx_url": f"/api/jobs/{job.id}/custom-resume/download",
            "docx_path": rendered_docx,
            "text_path": txt_path
        })
    except Exception as e:
        logger.error(f"Error saving custom resume for {job_id}: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_download_job_custom_resume(request: Request) -> Response:
    """Download the customized Word (.docx) resume for a specific job."""
    job_id = request.path_params["job_id"]
    job = db.get_job(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    docx_path = None
    if isinstance(job.metadata, dict):
        docx_path = job.metadata.get("custom_resume_docx") or job.metadata.get("tailored_resume_docx")

    if not docx_path or not Path(docx_path).exists():
        base_data = docx_renderer.get_default_template_data()
        safe_comp = re.sub(r'[^a-zA-Z0-9_]', '', job.company.replace(" ", "_"))
        safe_role = re.sub(r'[^a-zA-Z0-9_]', '', job.title.replace(" ", "_"))
        docx_path = f"data/artifacts/Vedang_Tiwari_{safe_comp}_{safe_role}.docx"
        docx_renderer.render(base_data, docx_path)

    p = Path(docx_path)
    return FileResponse(
        str(p),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=p.name
    )


async def api_tailor_custom_resume(request: Request) -> JSONResponse:
    """Tailor a candidate resume for an arbitrary role and job description."""
    try:
        data = await request.json()
        role = data.get("role", "").strip()
        company = data.get("company", "Target Company").strip()
        description = data.get("description", "").strip()
        generate_pdf = data.get("generate_pdf", True)

        if not role:
            return JSONResponse({"error": "Role title is required."}, status_code=400)

        artifacts = await tailor_agent.tailor_for_custom_role(
            role_title=role,
            company=company,
            job_description=description,
            generate_pdf=generate_pdf
        )

        return JSONResponse({
            "success": True,
            "artifacts": artifacts.to_dict()
        })
    except Exception as e:
        logger.error(f"Custom resume tailoring failed: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_download_artifact(request: Request) -> Response:
    """Download or preview a generated artifact file (PDF, TXT)."""
    filename = request.path_params["filename"]
    clean_filename = Path(filename).name
    file_path = Path("data/artifacts") / clean_filename

    if not file_path.exists():
        file_path_res = Path("data/resumes") / clean_filename
        if file_path_res.exists():
            file_path = file_path_res
        else:
            return JSONResponse({"error": f"Artifact '{clean_filename}' not found on disk."}, status_code=404)

    media_type = "application/pdf" if file_path.suffix.lower() == ".pdf" else "text/plain; charset=utf-8"
    return FileResponse(
        str(file_path),
        media_type=media_type,
        filename=file_path.name
    )


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
    """Trigger a live multi-platform or platform-targeted discovery sweep."""
    try:
        try:
            body = await request.json()
        except Exception:
            body = {}

        roles = body.get("roles")
        if not roles:
            profile_mgr.reload()
            roles = profile_mgr.preferences.target_roles

        locations = body.get("locations")
        max_age_hours = body.get("max_age_hours", 24)

        # Sanitize platform
        platform = body.get("platform")
        if not isinstance(platform, str) or not platform.strip() or platform.strip().lower() in ["all", "none", "null", "[object pointerevent]", "[object object]"]:
            platform = None
        else:
            platform = platform.strip()

        # Sanitize platforms list
        platforms = body.get("platforms")
        if platforms and isinstance(platforms, list):
            platforms = [
                str(p).strip() for p in platforms
                if str(p).strip() and str(p).strip().lower() not in ["all", "none", "null"]
            ]
            if not platforms:
                platforms = None
        else:
            platforms = None

        summary = await aggregator.run_discovery_cycle(
            roles=roles,
            locations=locations,
            max_age_hours=max_age_hours,
            platform=platform,
            platforms=platforms
        )
        return JSONResponse({
            "success": True,
            "summary": summary,
            "selected_platform": platform
        })
    except Exception as e:
        logger.error(f"Error during scout discovery sweep: {e}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


async def api_get_target_roles(request: Request) -> JSONResponse:
    """Retrieve active target role keywords."""
    profile_mgr.reload()
    return JSONResponse({
        "success": True,
        "target_roles": profile_mgr.preferences.target_roles
    })


async def api_add_target_role(request: Request) -> JSONResponse:
    """Add a new target role keyword and persist it to search preferences."""
    try:
        body = await request.json()
        role = body.get("role", "").strip()
        if not role:
            return JSONResponse({"error": "Role keyword cannot be empty."}, status_code=400)

        added = profile_mgr.add_target_role(role)
        return JSONResponse({
            "success": True,
            "added": added,
            "message": f"Added target role '{role}'." if added else f"Role '{role}' already exists.",
            "target_roles": profile_mgr.preferences.target_roles
        })
    except Exception as e:
        logger.error(f"Error adding target role: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def api_delete_target_role(request: Request) -> JSONResponse:
    """Remove a target role keyword and persist changes to search preferences."""
    import urllib.parse
    raw_role = request.path_params.get("role_name", "")
    decoded_role = urllib.parse.unquote(raw_role).strip()
    if not decoded_role:
        return JSONResponse({"error": "Invalid role specified."}, status_code=400)

    removed = profile_mgr.remove_target_role(decoded_role)
    return JSONResponse({
        "success": removed,
        "message": f"Target role '{decoded_role}' removed." if removed else f"Target role '{decoded_role}' not found.",
        "target_roles": profile_mgr.preferences.target_roles
    })


async def api_purge_ghost_jobs(request: Request) -> JSONResponse:
    """Purge ghost, dummy, and stale job postings from the database."""
    try:
        try:
            body = await request.json()
        except Exception:
            body = {}

        dry_run = bool(body.get("dry_run", False))
        keep_stale = bool(body.get("keep_stale", False))
        hard_delete = bool(body.get("hard_delete", True))

        result = db.purge_ghost_jobs(
            hard_delete=hard_delete,
            dry_run=dry_run,
            purge_stale=not keep_stale
        )
        return JSONResponse({
            "success": True,
            "message": f"Successfully purged {result['purged_count']} ghost jobs." if not dry_run else f"Identified {result['ghost_jobs_found']} ghost jobs.",
            **result
        })
    except Exception as e:
        logger.error(f"Error purging ghost jobs: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


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
    Route("/api/jobs/refresh", api_refresh_unseen_jobs, methods=["POST"]),
    Route("/api/jobs/{job_id}", api_get_job, methods=["GET"]),
    Route("/api/jobs/purge-ghosts", api_purge_ghost_jobs, methods=["POST"]),
    Route("/api/jobs/{job_id}/evaluate", api_evaluate_job, methods=["POST"]),
    Route("/api/jobs/{job_id}/apply", api_apply_job, methods=["POST"]),
    Route("/api/jobs/{job_id}/tailor", api_tailor_job_resume, methods=["POST"]),
    Route("/api/jobs/{job_id}/custom-resume", api_get_job_custom_resume, methods=["GET"]),
    Route("/api/jobs/{job_id}/custom-resume", api_save_job_custom_resume, methods=["POST"]),
    Route("/api/jobs/{job_id}/custom-resume/download", api_download_job_custom_resume, methods=["GET"]),
    Route("/api/template/resume", api_get_template_resume, methods=["GET"]),
    Route("/api/template/resume/download", api_download_template_resume, methods=["GET"]),
    Route("/api/jobs/{job_id}/apply-status", api_job_apply_status, methods=["GET"]),
    Route("/api/jobs/{job_id}/history", api_job_history, methods=["GET"]),
    Route("/api/jobs/batch-apply", api_batch_apply_jobs, methods=["POST"]),
    Route("/api/jobs/batch-status", api_batch_apply_status, methods=["GET"]),
    Route("/api/resume/tailor", api_tailor_custom_resume, methods=["POST"]),
    Route("/api/artifacts/{filename:path}", api_download_artifact, methods=["GET"]),
    Route("/api/profile", api_get_profile, methods=["GET"]),
    Route("/api/profile", api_save_profile, methods=["POST"]),
    Route("/api/resumes", api_get_resumes, methods=["GET"]),
    Route("/api/resumes/upload", api_upload_resume, methods=["POST"]),
    Route("/api/resumes/{resume_id}", api_delete_resume, methods=["DELETE"]),
    Route("/api/resumes/{resume_id}/download", api_download_resume, methods=["GET"]),
    Route("/api/platforms", api_get_platforms, methods=["GET"]),
    Route("/api/platforms", api_add_platform, methods=["POST"]),
    Route("/api/platforms/{name}/toggle", api_toggle_platform, methods=["POST"]),
    Route("/api/target-roles", api_get_target_roles, methods=["GET"]),
    Route("/api/target-roles", api_add_target_role, methods=["POST"]),
    Route("/api/target-roles/{role_name:path}", api_delete_target_role, methods=["DELETE"]),
    Route("/api/scout", api_trigger_scout, methods=["POST"]),
    Route("/api/system", api_system_info, methods=["GET"]),
    Mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True
    )
]

app = Starlette(debug=True, routes=routes, middleware=middleware)


def run_web_server(host: str = "127.0.0.1", port: int = 8000):
    """Launch the uvicorn ASGI web server."""
    logger.info(f"Starting MCP Web Dashboard at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_web_server()
