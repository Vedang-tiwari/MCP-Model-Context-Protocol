"""Human-In-The-Loop (HITL) Alerting Module.
Dispatches high-priority notifications when an OTP, 2FA, or CAPTCHA is encountered.
Supports Telegram, Discord Webhook, and Terminal Audio/Visual alerts.
"""
import logging
import httpx
from typing import Optional
from core.config import settings

logger = logging.getLogger(__name__)


class HITLNotifier:
    def __init__(self):
        self.telegram_token = settings.TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = settings.TELEGRAM_CHAT_ID
        self.discord_webhook = settings.DISCORD_WEBHOOK_URL

    async def notify_human_action_required(
        self,
        reason: str,
        job_title: str,
        company: str,
        url: str,
        screenshot_path: Optional[str] = None
    ):
        """Notifies user that human intervention (CAPTCHA / OTP / 2FA) is needed."""
        msg = (
            f"⚠️ **ACTION REQUIRED: Job Application Paused**\n"
            f"**Reason**: {reason}\n"
            f"**Role**: {job_title}\n"
            f"**Company**: {company}\n"
            f"**URL**: {url}\n\n"
            f"Please check the active browser window to solve the challenge within 60 seconds."
        )

        logger.warning(f"\n{'='*60}\n{msg}\n{'='*60}\n")
        print("\a")  # System terminal bell

        await self._send_telegram(msg)
        await self._send_discord(msg)

    async def notify_application_submitted(
        self,
        job_title: str,
        company: str,
        url: str,
        screenshot_path: Optional[str] = None
    ):
        """Notifies user of a successful automated application."""
        msg = (
            f"✅ **Application Successfully Submitted!**\n"
            f"**Role**: {job_title}\n"
            f"**Company**: {company}\n"
            f"**URL**: {url}"
        )
        logger.info(msg)
        await self._send_telegram(msg)
        await self._send_discord(msg)

    async def _send_telegram(self, message: str):
        if not (self.telegram_token and self.telegram_chat_id):
            return
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                await client.post(url, json={
                    "chat_id": self.telegram_chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                })
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")

    async def _send_discord(self, message: str):
        if not self.discord_webhook:
            return
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                await client.post(self.discord_webhook, json={"content": message})
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
