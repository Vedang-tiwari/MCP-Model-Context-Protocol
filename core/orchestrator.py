"""Autonomous Agentic Orchestrator powered by Open-Source Baseline Models (Llama 3.3 / Qwen 2.5).
Executes multi-step tool-calling workflows to discover, evaluate, and apply for jobs based on natural language goals.
"""
import json
import logging
from typing import List, Dict, Any, Optional

from core.database import DatabaseManager
from core.profile_manager import ProfileManager
from core.llm_client import LLMClient
from core.models import ApplicationStatus
from discovery.aggregator import JobAggregator
from applicator.browser import BrowserSessionManager
from applicator.form_filler import ApplicationAgent
from applicator.hitl import HITLNotifier

logger = logging.getLogger(__name__)


# Standard Tool Schemas exposed to the Open-Source LLM
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_recent_jobs",
            "description": "Searches for recently posted jobs matching target roles. Can optionally trigger a live web crawl across LinkedIn, Indeed, ATS boards, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "roles": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of role keywords to search for e.g. ['AI Engineer', 'Python Developer']"
                    },
                    "trigger_live_crawl": {
                        "type": "boolean",
                        "description": "If true, executes a live web discovery sweep across all enabled platforms right now."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of jobs to retrieve from database."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_job_fit",
            "description": "Evaluates compatibility between candidate profile and a specific job listing. Returns match score (0-100) and detailed criteria.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Unique ID of the job to evaluate."
                    }
                },
                "required": ["job_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "apply_to_job",
            "description": "Launches stealth browser agent to submit or pre-fill job application using candidate credentials and LLM screening answers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Unique ID of the job to apply to."
                    },
                    "auto_submit": {
                        "type": "boolean",
                        "description": "If true, clicks final submit button. If false, fills the form and pauses for user review."
                    }
                },
                "required": ["job_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_application_status",
            "description": "Retrieves statistical dashboard of total jobs discovered, applied, queued, and platform breakdowns.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_candidate_profile",
            "description": "Returns candidate personal info, skills, education, target roles, and standard compensation answers.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_job_platforms",
            "description": "Lists all active job platforms, including built-ins (LinkedIn, Indeed, ATS Direct), custom platforms (RemoteOK, WeWorkRemotely), and plugins.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_custom_job_platform",
            "description": "Dynamically registers a new job platform (RSS, JSON API, or HTML scraper) to scan for jobs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Unique slug for the platform (e.g. 'simplyhired')"},
                    "platform_type": {"type": "string", "enum": ["rss", "json_api", "html_scraper"], "description": "Type of platform"},
                    "url_template": {"type": "string", "description": "Feed or endpoint URL (can include {role})"},
                    "display_name": {"type": "string", "description": "Human readable name"}
                },
                "required": ["name", "platform_type", "url_template"]
            }
        }
    }
]


class AgentOrchestrator:
    def __init__(
        self,
        db: Optional[DatabaseManager] = None,
        profile_mgr: Optional[ProfileManager] = None,
        llm: Optional[LLMClient] = None
    ):
        self.db = db or DatabaseManager()
        self.profile_mgr = profile_mgr or ProfileManager()
        self.llm = llm or LLMClient()
        self.hitl = HITLNotifier()
        self.session_mgr = BrowserSessionManager()
        self.aggregator = JobAggregator(self.db, self.profile_mgr)
        self.agent = ApplicationAgent(self.db, self.profile_mgr, self.session_mgr, self.hitl)

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Dispatches tool execution to the underlying systems."""
        logger.info(f"Executing tool: {tool_name} with arguments: {arguments}")

        if tool_name == "search_recent_jobs":
            roles = arguments.get("roles")
            trigger_live = arguments.get("trigger_live_crawl", False)
            limit = arguments.get("limit", 10)

            crawl_summary = ""
            if trigger_live:
                summary = await self.aggregator.run_discovery_cycle(roles=roles)
                crawl_summary = f"Live crawl completed: {summary['new_unique_jobs']} new jobs discovered.\n"

            jobs = self.db.list_jobs(limit=limit)
            job_list = []
            for j in jobs:
                job_list.append({
                    "id": j.id,
                    "title": j.title,
                    "company": j.company,
                    "platform": j.platform,
                    "location": j.location,
                    "match_score": j.match_score,
                    "status": j.status.value,
                    "url": j.url
                })
            return crawl_summary + json.dumps(job_list, indent=2)

        elif tool_name == "evaluate_job_fit":
            job_id = arguments.get("job_id", "")
            job = self.db.get_job(job_id)
            if not job:
                return f"Error: Job ID '{job_id}' not found."
            score, reasons = self.profile_mgr.evaluate_fit(job)
            self.db.update_job_status(job_id, job.status, match_score=score, match_reasons=reasons)
            return json.dumps({
                "job_id": job_id,
                "title": job.title,
                "company": job.company,
                "match_score": score,
                "reasons": reasons
            }, indent=2)

        elif tool_name == "apply_to_job":
            job_id = arguments.get("job_id", "")
            auto_submit = arguments.get("auto_submit", False)
            job = self.db.get_job(job_id)
            if not job:
                return f"Error: Job ID '{job_id}' not found."
            record = await self.agent.apply(job, auto_submit=auto_submit)
            return json.dumps({
                "job_id": job_id,
                "status": record.status.value,
                "screenshot": record.screenshot_path,
                "notes": record.notes or record.error_message or "Success"
            }, indent=2)

        elif tool_name == "get_application_status":
            stats = self.db.get_stats()
            return json.dumps(stats, indent=2)

        elif tool_name == "get_candidate_profile":
            p = self.profile_mgr.profile
            prefs = self.profile_mgr.preferences
            return json.dumps({
                "name": p.personal_info.full_name,
                "email": p.personal_info.email,
                "skills": p.skills,
                "target_roles": prefs.target_roles,
                "locations": prefs.locations
            }, indent=2)

        elif tool_name == "list_job_platforms":
            platforms = self.aggregator.registry.list_platforms()
            return json.dumps(platforms, indent=2)

        elif tool_name == "add_custom_job_platform":
            from core.models import CustomPlatformConfig, PlatformType
            name = arguments.get("name", "").strip()
            ptype_str = arguments.get("platform_type", "rss")
            url = arguments.get("url_template", "")
            display = arguments.get("display_name")
            cfg = CustomPlatformConfig(
                name=name,
                display_name=display or name.capitalize(),
                platform_type=PlatformType(ptype_str),
                enabled=True,
                url_template=url
            )
            success = self.aggregator.registry.add_custom_platform(cfg)
            return f"Platform '{name}' added successfully: {success}"

        return f"Unknown tool: {tool_name}"

    async def run_goal(self, goal: str, max_turns: int = 8) -> str:
        """
        Multi-turn autonomous tool-calling loop using the open-source baseline model.
        """
        system_prompt = (
            "You are an autonomous AI Job Application Agent powered by an open-source model.\n"
            "Your objective is to accomplish the user's job search, evaluation, and application goals.\n"
            "You have access to tools to search for fresh jobs, evaluate fit against the candidate's profile, and submit applications.\n"
            "Follow these guidelines:\n"
            "1. When searching for new jobs, consider setting trigger_live_crawl=True if current results are empty or the user asks for newly posted jobs.\n"
            "2. Always evaluate candidate fit before applying.\n"
            "3. Conclude with a clear summary of actions taken, jobs evaluated, and applications submitted.\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": goal}
        ]

        logger.info(f"Starting orchestration goal with model [{self.llm.provider}/{self.llm.model}]: '{goal}'")

        for turn in range(max_turns):
            response = await self.llm.chat_completion(
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.1
            )

            if response.get("error"):
                logger.error(f"Turn {turn + 1} failed: {response.get('message')}")
                return f"Orchestration Error: {response.get('message')}"

            content = response.get("content")
            tool_calls = response.get("tool_calls", [])

            # Append assistant message to history
            assistant_msg: Dict[str, Any] = {"role": "assistant"}
            if content:
                assistant_msg["content"] = content
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)

            # If no tool calls were requested, the model is finished and has formulated its final response
            if not tool_calls:
                logger.info(f"Orchestration completed in {turn + 1} turns.")
                return content or "Task completed."

            # Execute tool calls
            for tool_call in tool_calls:
                call_id = tool_call.get("id", "call_1")
                func = tool_call.get("function", {})
                name = func.get("name", "")
                raw_args = func.get("arguments", "{}")

                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    args = {}

                result_str = await self.execute_tool(name, args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": result_str
                })

        return "Orchestration reached maximum turns limit."
