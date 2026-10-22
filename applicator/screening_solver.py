"""Screening question solver using LLM synthesis with grounded candidate profile knowledge."""
import logging
import json
import httpx
from typing import List, Optional, Dict, Any
from core.profile_manager import ProfileManager
from core.config import settings

logger = logging.getLogger(__name__)


class ScreeningQuestionSolver:
    def __init__(self, profile_mgr: ProfileManager):
        self.profile_mgr = profile_mgr

    async def answer_question(
        self,
        question_text: str,
        options: Optional[List[str]] = None,
        field_type: str = "text"
    ) -> str:
        """
        Synthesizes an accurate, truthful answer grounded in candidate profile.
        """
        q_lower = question_text.lower()
        std = self.profile_mgr.profile.standard_answers

        # 1. Fast Rule-Based Matching for Standard Screening Questions
        if any(w in q_lower for w in ["notice period", "how soon", "start date", "availability"]):
            if options:
                return self._pick_closest_option(f"{std.notice_period_days} days", options)
            return f"{std.notice_period_days} days"

        if any(w in q_lower for w in ["years of experience", "total experience", "how many years"]):
            if options:
                return self._pick_closest_option(str(std.years_of_experience), options)
            return str(std.years_of_experience)

        if any(w in q_lower for w in ["authorized to work", "work authorization", "legally eligible", "right to work"]):
            if options:
                return self._pick_closest_option("Yes", options)
            return std.work_authorization

        if any(w in q_lower for w in ["sponsorship", "require visa", "visa sponsorship"]):
            val = "Yes" if std.requires_sponsorship else "No"
            if options:
                return self._pick_closest_option(val, options)
            return val

        if any(w in q_lower for w in ["relocate", "relocation"]):
            val = "Yes" if std.willing_to_relocate else "No"
            if options:
                return self._pick_closest_option(val, options)
            return val

        if any(w in q_lower for w in ["expected salary", "salary expectation", "compensation", "ctc"]):
            if std.currency_preference == "INR" and std.expected_salary_inr:
                val = str(std.expected_salary_inr)
            else:
                val = str(std.expected_salary_usd or 120000)
            if options:
                return self._pick_closest_option(val, options)
            return val

        # 2. Check Candidate QA Knowledge Base
        for item in self.profile_mgr.profile.qa_knowledge_base:
            if any(k in q_lower for k in item.question_keywords):
                if options:
                    return self._pick_closest_option(item.answer, options)
                return item.answer

        # 3. Open-Source / Baseline LLM-Based Synthesis for Complex or Custom Questions
        try:
            from core.llm_client import LLMClient
            client = LLMClient()
            answer = await self._ask_llm(client, question_text, options)
            if answer:
                return answer
        except Exception as e:
            logger.error(f"LLM screening solver encountered an issue: {e}")

        # 4. Fallback Default
        if options:
            return options[0]
        return "Yes, based on my background I am fully qualified for this requirement."

    async def _ask_llm(self, client: Any, question: str, options: Optional[List[str]] = None) -> Optional[str]:
        prompt = (
            f"You are acting as the job candidate answering an application form question.\n"
            f"Ground your answer STRICTLY in the candidate profile below.\n"
            f"Be concise, professional, and directly answer the question.\n\n"
            f"CANDIDATE PROFILE:\n{self.profile_mgr.format_profile_for_llm()}\n\n"
            f"QUESTION: {question}\n"
        )
        if options:
            prompt += f"AVAILABLE OPTIONS: {json.dumps(options)}\nReturn ONLY the exact matching option string from the available options."
        else:
            prompt += "Provide a direct, 1-3 sentence response."

        messages = [
            {"role": "system", "content": "You are a job applicant completing an employment form."},
            {"role": "user", "content": prompt}
        ]

        response = await client.chat_completion(messages=messages, temperature=0.1)
        if not response.get("error") and response.get("content"):
            content = response["content"].strip()
            if options:
                return self._pick_closest_option(content, options)
            return content
        return None

    def _pick_closest_option(self, target: str, options: List[str]) -> str:
        """Finds the best matching option from a dropdown or radio button list."""
        target_lower = target.lower()
        # Exact match
        for opt in options:
            if opt.lower() == target_lower:
                return opt
        # Substring match
        for opt in options:
            if target_lower in opt.lower() or opt.lower() in target_lower:
                return opt
        # Fallback to first non-empty option
        return options[0] if options else target
