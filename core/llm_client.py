"""Unified LLM Client supporting Open-Source baseline models (Qwen 2.5, Llama 3.3, DeepSeek)
via Ollama (local), Groq (high-speed cloud), vLLM, or any OpenAI-compatible endpoint.
"""
import json
import logging
from typing import List, Dict, Any, Optional
import httpx

from core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Open-Source friendly LLM interface with native tool calling and function calling support.
    
    Recommended Baseline Models:
    - Groq: 'llama-3.3-70b-versatile' or 'qwen-2.5-32b' (Ultra-fast 300+ tok/s, native tool calling)
    - Ollama: 'qwen2.5:14b' or 'llama3.1:8b' (100% free, runs locally, zero API keys required)
    - DeepSeek: 'deepseek-chat' (State of the art reasoning & tool calling)
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.provider = provider or settings.LLM_PROVIDER.lower()
        self.model = model or settings.LLM_MODEL
        self._configure_endpoints(api_key, base_url)

    def _configure_endpoints(self, api_key: Optional[str], base_url: Optional[str]):
        if self.provider == "ollama":
            self.base_url = base_url or settings.OLLAMA_BASE_URL.rstrip("/")
            self.api_key = "ollama"  # Ollama doesn't require an API key
            if not self.model or self.model == "gpt-4o-mini":
                self.model = "qwen2.5:14b"
        elif self.provider == "groq":
            self.base_url = base_url or "https://api.groq.com/openai/v1"
            self.api_key = api_key or settings.GROQ_API_KEY
            if not self.model or self.model == "gpt-4o-mini":
                self.model = "llama-3.3-70b-versatile"
        elif self.provider == "deepseek":
            self.base_url = base_url or "https://api.deepseek.com/v1"
            self.api_key = api_key or settings.DEEPSEEK_API_KEY
            if not self.model or self.model == "gpt-4o-mini":
                self.model = "deepseek-chat"
        elif self.provider == "openai":
            self.base_url = base_url or "https://api.openai.com/v1"
            self.api_key = api_key or settings.OPENAI_API_KEY
        else:
            # Custom OpenAI-compatible endpoint (vLLM, LM Studio, LocalAI)
            self.base_url = base_url or settings.LLM_BASE_URL.rstrip("/")
            self.api_key = api_key or settings.LLM_API_KEY or "not-needed"

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.2,
        max_tokens: int = 1500
    ) -> Dict[str, Any]:
        """
        Executes a chat completion with optional tool/function calling definitions.
        Works across Ollama, Groq, DeepSeek, and OpenAI endpoints.
        """
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key and self.api_key != "not-needed":
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                response = await client.post(endpoint, headers=headers, json=payload)
                if response.status_code != 200:
                    logger.error(f"LLM API error ({self.provider}/{self.model}): {response.status_code} - {response.text}")
                    return {
                        "error": True,
                        "status_code": response.status_code,
                        "message": response.text,
                        "content": None,
                        "tool_calls": []
                    }

                data = response.json()
                choice = data["choices"][0]
                message = choice.get("message", {})

                return {
                    "error": False,
                    "content": message.get("content", ""),
                    "tool_calls": message.get("tool_calls", []),
                    "role": message.get("role", "assistant")
                }
            except Exception as e:
                logger.error(f"Failed to communicate with LLM provider '{self.provider}': {e}")
                return {
                    "error": True,
                    "message": str(e),
                    "content": None,
                    "tool_calls": []
                }
