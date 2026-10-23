"""Command Line Interface (CLI) for MCP Autonomous Job Application Agent."""
import sys
import asyncio
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Reconfigure stdout/stderr on Windows to avoid cp1252 UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.database import DatabaseManager
from core.profile_manager import ProfileManager
from core.models import ApplicationStatus
from discovery.aggregator import JobAggregator
from applicator.browser import BrowserSessionManager
from applicator.form_filler import ApplicationAgent
from applicator.hitl import HITLNotifier
from worker.scheduler import AutonomousWorker

console = Console(force_terminal=True)


@click.group()
def cli():
    """MCP: 24/7/365 Autonomous Job Scout & Application System."""
    pass


@cli.command()
@click.option("--roles", "-r", multiple=True, help="Override target roles for this sweep")
@click.option("--age", "-a", default=24, help="Max job age in hours (default 24)")
def scout(roles, age):
    """Run an instant live discovery sweep across all enabled career platforms."""
    db = DatabaseManager()
    profile_mgr = ProfileManager()
    aggregator = JobAggregator(db, profile_mgr)

    target_roles = list(roles) if roles else None

    console.print(Panel.fit(
        f"[bold cyan]🔍 Initiating Real-Time Job Discovery Sweep[/bold cyan]\n"
        f"Target Roles: {target_roles or profile_mgr.preferences.target_roles}\n"
        f"Platforms: {list(profile_mgr.preferences.platforms.keys())}",
        border_style="cyan"
    ))

    async def _run():
        with console.status("[bold green]Scouting platforms...[/bold green]"):
            summary = await aggregator.run_discovery_cycle(roles=target_roles, max_age_hours=age)
        return summary

    summary = asyncio.run(_run())

    console.print(f"\n[bold green][+] Discovery Sweep Completed![/bold green]")
    console.print(f"Total Postings Inspected: [bold]{summary['total_fetched']}[/bold]")
    console.print(f"New Unique Postings Saved: [bold cyan]{summary['new_unique_jobs']}[/bold cyan]")
    console.print(f"Qualified Matches (Score >= {summary['threshold']}%): [bold yellow]{summary['qualified_matches']}[/bold yellow]\n")


@cli.command(name="list")
@click.option("--limit", "-l", default=20, help="Number of jobs to list")
@click.option("--status", "-s", type=click.Choice([e.value for e in ApplicationStatus]), help="Filter by status")
@click.option("--platform", "-p", help="Filter by platform")
@click.option("--min-score", "-m", type=int, help="Filter by minimum match score")
def list_jobs(limit, status, platform, min_score):
    """Display discovered jobs in a formatted table."""
    db = DatabaseManager()
    status_filter = ApplicationStatus(status) if status else None
    jobs = db.list_jobs(status=status_filter, platform=platform, limit=limit, min_match_score=min_score)

    if not jobs:
        console.print("[yellow]No jobs found matching criteria.[/yellow]")
        return

    table = Table(title=f"Discovered Jobs ({len(jobs)} shown)", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=12)
    table.add_column("Role", style="bold white")
    table.add_column("Company", style="cyan")
    table.add_column("Platform", style="green")
    table.add_column("Match", justify="right")
    table.add_column("Status", style="yellow")
    table.add_column("Apply URL")

    for j in jobs:
        score_display = f"{j.match_score}%" if j.match_score is not None else "-"
        score_color = "green" if (j.match_score or 0) >= 75 else ("yellow" if (j.match_score or 0) >= 50 else "red")
        table.add_row(
            j.id[:10],
            j.title[:30],
            j.company[:20],
            j.platform,
            f"[{score_color}]{score_display}[/{score_color}]",
            j.status.value,
            j.url[:40] + "..." if len(j.url) > 40 else j.url
        )

    console.print(table)


@cli.command()
@click.argument("job_id")
def evaluate(job_id):
    """Run candidate fit evaluation on a specific job."""
    db = DatabaseManager()
    profile_mgr = ProfileManager()
    job = db.get_job(job_id)

    if not job:
        console.print(f"[red]Error: Job with ID '{job_id}' not found.[/red]")
        return

    score, reasons = profile_mgr.evaluate_fit(job)
    db.update_job_status(job_id, job.status, match_score=score, match_reasons=reasons)

    color = "green" if score >= 75 else ("yellow" if score >= 50 else "red")
    console.print(Panel.fit(
        f"[bold]Role:[/bold] {job.title}\n"
        f"[bold]Company:[/bold] {job.company}\n"
        f"[bold]Platform:[/bold] {job.platform}\n"
        f"[bold]Location:[/bold] {job.location}\n"
        f"[bold]Fit Score:[/bold] [{color}]{score} / 100[/{color}]\n\n"
        f"[bold]Reasons & Criteria:[/bold]\n" + "\n".join([f"  • {r}" for r in reasons]),
        title=f"Job Evaluation: {job.id}",
        border_style=color
    ))


@cli.command()
@click.argument("job_id")
@click.option("--auto-submit", is_flag=True, help="Automatically click final submit button")
def apply(job_id, auto_submit):
    """Trigger automated browser application workflow for a specific job."""
    db = DatabaseManager()
    profile_mgr = ProfileManager()
    hitl = HITLNotifier()
    session_mgr = BrowserSessionManager()
    agent = ApplicationAgent(db, profile_mgr, session_mgr, hitl)

    job = db.get_job(job_id)
    if not job:
        console.print(f"[red]Error: Job with ID '{job_id}' not found.[/red]")
        return

    console.print(f"[bold cyan]Launching stealth browser to apply for '{job.title}' at '{job.company}'...[/bold cyan]")

    async def _run():
        return await agent.apply(job, auto_submit=auto_submit)

    record = asyncio.run(_run())

    if record.status == ApplicationStatus.APPLIED:
        console.print(f"[bold green][+] Successfully applied to {job.title} at {job.company}![/bold green]")
    elif record.status == ApplicationStatus.MANUAL_REVIEW:
        console.print(f"[bold yellow]Application pre-filled. Please review and confirm in the browser.[/bold yellow]")
    else:
        console.print(f"[bold red]Application failed: {record.error_message}[/bold red]")

    if record.screenshot_path:
        console.print(f"Evidence Screenshot saved at: [bold]{record.screenshot_path}[/bold]")


@cli.command()
def worker():
    """Start the 24/7/365 continuous autonomous background daemon."""
    daemon = AutonomousWorker()
    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        console.print("\n[yellow]Worker terminated by user.[/yellow]")


@cli.command()
@click.option("--transport", "-t", type=click.Choice(["stdio", "sse"]), default="stdio", help="MCP transport protocol (stdio or sse)")
def mcp(transport):
    """Launch the Model Context Protocol (MCP) server."""
    from mcp_server.server import mcp as mcp_instance
    mcp_instance.run(transport=transport)


@cli.command()
def stats():
    """Display discovery & application metrics dashboard."""
    db = DatabaseManager()
    metrics = db.get_stats()

    console.print(Panel.fit(
        f"[bold]Total Discovered Jobs:[/bold] {metrics['total_discovered']}\n"
        f"[bold]Total Applications Submitted:[/bold] {metrics['total_applied']}\n\n"
        f"[bold cyan]Status Breakdown:[/bold cyan]\n" +
        "\n".join([f"  • {k}: {v}" for k, v in metrics.get('status_breakdown', {}).items()]) +
        f"\n\n[bold green]Platform Breakdown:[/bold green]\n" +
        "\n".join([f"  • {k}: {v}" for k, v in metrics.get('platform_breakdown', {}).items()]),
        title="MCP Job Application Metrics",
        border_style="blue"
    ))


@cli.command()
@click.argument("goal")
def agent(goal):
    """Run autonomous open-source tool-calling orchestrator with a natural language goal."""
    from core.orchestrator import AgentOrchestrator
    from core.config import settings
    orchestrator = AgentOrchestrator()

    console.print(Panel.fit(
        f"[bold cyan]🤖 Open-Source Agentic Orchestrator[/bold cyan]\n"
        f"Provider: [bold green]{settings.LLM_PROVIDER}[/bold green] | Model: [bold yellow]{settings.LLM_MODEL}[/bold yellow]\n"
        f"Goal: [white]{goal}[/white]",
        border_style="cyan"
    ))

    async def _run():
        with console.status("[bold green]Agent reasoning and calling tools...[/bold green]"):
            return await orchestrator.run_goal(goal)

    result = asyncio.run(_run())
    console.print("\n[bold green][+] Agent Execution Summary:[/bold green]\n")
    console.print(result)


@cli.group()
def platform():
    """Manage dynamic job platforms (RSS, JSON API, Web Scrapers, Plugins)."""
    pass


@platform.command(name="list")
def list_platforms_cmd():
    """List all configured platforms and their active status."""
    from discovery.registry import PlatformRegistry
    registry = PlatformRegistry()
    platforms = registry.list_platforms()

    table = Table(title="Configured Job Platforms", show_header=True, header_style="bold magenta")
    table.add_column("Status", width=8, justify="center")
    table.add_column("Slug", style="cyan")
    table.add_column("Display Name", style="bold white")
    table.add_column("Type", style="green")
    table.add_column("Source", style="dim")

    for p in platforms:
        status_icon = "[green]Active[/green]" if p["enabled"] else "[red]Disabled[/red]"
        table.add_row(
            status_icon,
            p["name"],
            p["display_name"],
            p["type"],
            p["source"]
        )

    console.print(table)


@platform.command(name="add")
@click.option("--name", "-n", required=True, help="Unique slug identifier (e.g. 'remoteok', 'weworkremotely')")
@click.option("--type", "-t", "ptype", type=click.Choice(["rss", "json_api", "html_scraper"]), required=True, help="Platform provider type")
@click.option("--url", "-u", required=True, help="URL or endpoint template (can include {role} and {location})")
@click.option("--display", "-d", help="Display name for platform")
def add_platform_cmd(name, ptype, url, display):
    """Register a new job platform dynamically."""
    from discovery.registry import PlatformRegistry
    from core.models import CustomPlatformConfig, PlatformType

    registry = PlatformRegistry()
    cfg = CustomPlatformConfig(
        name=name.lower().strip(),
        display_name=display or name.capitalize(),
        platform_type=PlatformType(ptype),
        enabled=True,
        url_template=url
    )

    registry.add_custom_platform(cfg)
    console.print(f"[bold green][+] Successfully added job platform '{cfg.display_name}' ({cfg.platform_type.value})![/bold green]")
    console.print(f"URL: [dim]{url}[/dim]")


@platform.command(name="toggle")
@click.argument("name")
@click.option("--enable/--disable", default=True, help="Enable or disable the platform")
def toggle_platform_cmd(name, enable):
    """Enable or disable a specific job platform."""
    from discovery.registry import PlatformRegistry
    registry = PlatformRegistry()
    success = registry.toggle_platform(name.lower().strip(), enable)
    if success:
        state = "[green]enabled[/green]" if enable else "[yellow]disabled[/yellow]"
        console.print(f"Platform '{name}' is now {state}.")
    else:
        console.print(f"[red]Error: Platform '{name}' not found.[/red]")


@platform.command(name="remove")
@click.argument("name")
def remove_platform_cmd(name):
    """Remove a custom job platform from registry."""
    from discovery.registry import PlatformRegistry
    registry = PlatformRegistry()
    success = registry.remove_custom_platform(name.lower().strip())
    if success:
        console.print(f"[bold green][+] Removed custom platform '{name}' successfully.[/bold green]")
    else:
        console.print(f"[red]Error: Cannot remove platform '{name}' (may be built-in or not found).[/red]")


@cli.group()
def resume():
    """Manage multi-resume mappings for automatic role-tailored applications."""
    pass


@resume.command(name="list")
def list_resumes_cmd():
    """List all mapped resumes and their designated roles."""
    profile_mgr = ProfileManager()
    resumes = profile_mgr.profile.role_resumes

    if not resumes:
        console.print("[yellow]No role-mapped resumes configured yet. Use 'python cli.py resume upload' to register one.[/yellow]")
        return

    table = Table(title="Role-Tailored Resume Matrix", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=10)
    table.add_column("Designated Role / Pattern", style="bold cyan")
    table.add_column("File Name", style="white")
    table.add_column("Size", justify="right")
    table.add_column("Default", justify="center")
    table.add_column("Status", width=10)

    for r in resumes:
        path = Path(r.file_path)
        status = "[green]Ready[/green]" if path.exists() else "[red]Missing[/red]"
        default_str = "[yellow]Yes (★)[/yellow]" if r.is_default else "[dim]No[/dim]"
        size_str = f"{r.file_size_kb:.1f} KB" if r.file_size_kb else "-"
        table.add_row(
            r.id,
            r.role_pattern,
            r.file_name,
            size_str,
            default_str,
            status
        )

    console.print(table)


@resume.command(name="upload")
@click.option("--file", "-f", required=True, type=click.Path(exists=True), help="Path to resume file (.pdf, .docx)")
@click.option("--role", "-r", required=True, help="Designated role (e.g. 'AI Engineer', 'SWE', 'FDE', 'Full Stack', '*')")
@click.option("--default", "-d", is_flag=True, help="Set as default fallback resume")
def upload_resume_cmd(file, role, default):
    """Upload and map a resume to a specific job role."""
    import shutil
    import re
    profile_mgr = ProfileManager()
    src_path = Path(file)

    # Destination directory
    dest_dir = Path("data/resumes")
    dest_dir.mkdir(parents=True, exist_ok=True)

    role_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', role.lower()).strip('_')
    dest_filename = f"resume_{role_slug}{src_path.suffix.lower()}"
    dest_path = dest_dir / dest_filename

    shutil.copyfile(src_path, dest_path)

    mapping = profile_mgr.add_role_resume(
        file_path=str(dest_path),
        role_pattern=role,
        original_filename=src_path.name,
        is_default=default
    )

    console.print(Panel.fit(
        f"[bold green][+] Successfully Uploaded & Mapped Resume![/bold green]\n\n"
        f"Designated Role: [bold cyan]{mapping.role_pattern}[/bold cyan]\n"
        f"File: [white]{src_path.name}[/white] ({mapping.file_size_kb:.1f} KB)\n"
        f"Stored At: [dim]{dest_path}[/dim]\n"
        f"Default Fallback: [bold yellow]{'Yes' if mapping.is_default else 'No'}[/bold yellow]",
        border_style="green"
    ))


@resume.command(name="delete")
@click.argument("identifier")
def delete_resume_cmd(identifier):
    """Remove a resume mapping by its ID or role pattern."""
    profile_mgr = ProfileManager()
    success = profile_mgr.remove_role_resume(identifier)
    if success:
        console.print(f"[bold green][+] Removed resume mapping for '{identifier}'.[/bold green]")
    else:
        console.print(f"[red]Error: Resume mapping '{identifier}' not found.[/red]")


@resume.command(name="test")
@click.argument("job_title")
def test_resume_matching_cmd(job_title):
    """Simulate which resume would be dynamically chosen for a given job title."""
    from core.models import JobListing
    profile_mgr = ProfileManager()
    dummy_job = JobListing(
        id="test",
        platform="cli_test",
        title=job_title,
        company="Test Corp",
        location="Remote",
        url="https://example.com"
    )
    selected = profile_mgr.get_resume_for_job(dummy_job)

    if selected:
        console.print(Panel.fit(
            f"Job Title Query: [bold white]'{job_title}'[/bold white]\n"
            f"Selected Resume: [bold green]{selected.name}[/bold green]\n"
            f"Path: [dim]{selected}[/dim]",
            title="Resume Routing Resolution",
            border_style="cyan"
        ))
    else:
        console.print(f"[yellow]No resume resolved for '{job_title}'.[/yellow]")


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host address to bind to (default 127.0.0.1)")
@click.option("--port", "-p", default=8000, type=int, help="Port to listen on (default 8000)")
def web(host, port):
    """Launch the local web dashboard interface."""
    from web.server import run_web_server
    console.print(Panel.fit(
        f"[bold cyan]🌐 Starting MCP Local Host Web Dashboard[/bold cyan]\n"
        f"URL: [bold underline green]http://{host}:{port}[/bold underline green]\n"
        f"API: [dim]http://{host}:{port}/api/stats[/dim]\n"
        f"Press [bold red]Ctrl+C[/bold red] to terminate the server.",
        border_style="green"
    ))
    run_web_server(host=host, port=port)


if __name__ == "__main__":
    cli()
