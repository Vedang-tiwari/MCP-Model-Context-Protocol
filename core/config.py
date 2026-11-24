"""Configuration loader and environment manager."""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Base paths
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Load .env file if it exists
env_path = ROOT_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)


class Settings:
    # LLM Settings (Defaults to Google Gemini API: gemini-2.0-flash or gemini-1.5-flash)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.0-flash")

    # API Keys & Custom Base URLs
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")

    # Storage
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(DATA_DIR / "mcp_jobs.db"))

    # Browser
    PLAYWRIGHT_HEADLESS: bool = os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"
    BROWSER_USER_DATA_DIR: str = os.getenv("BROWSER_USER_DATA_DIR", str(DATA_DIR / "browser_profile"))
    CHROME_CHANNEL: str = os.getenv("CHROME_CHANNEL", "chrome")
    CDP_URL: str = os.getenv("CDP_URL", "http://127.0.0.1:9222")
    BROWSER_REMOTE_DEBUGGING_PORT: int = int(os.getenv("BROWSER_REMOTE_DEBUGGING_PORT", "9222"))
    USER_AGENT: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )

    # Alerts
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")

    # MCP Server
    MCP_SERVER_HOST: str = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    MCP_SERVER_PORT: int = int(os.getenv("MCP_SERVER_PORT", "8000"))

    # Config files (JSON legacy & YAML Blueprint §3)
    PROFILE_PATH: Path = CONFIG_DIR / "candidate_profile.json"
    SEARCH_PREFS_PATH: Path = CONFIG_DIR / "search_preferences.json"
    PROFILE_YAML_PATH: Path = CONFIG_DIR / "profile.yaml"
    QA_BANK_YAML_PATH: Path = CONFIG_DIR / "qa_bank.yaml"
    COMPANIES_YAML_PATH: Path = CONFIG_DIR / "companies.yaml"


settings = Settings()
