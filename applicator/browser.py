"""Stealth browser manager using Playwright with persistent sessions and anti-bot evasions."""
import os
import random
import asyncio
import logging
from typing import Optional
from playwright.async_api import async_playwright, BrowserContext, Page
from core.config import settings

logger = logging.getLogger(__name__)


class BrowserSessionManager:
    def __init__(self, user_data_dir: Optional[str] = None, headless: Optional[bool] = None):
        self.user_data_dir = user_data_dir or settings.BROWSER_USER_DATA_DIR
        self.headless = headless if headless is not None else settings.PLAYWRIGHT_HEADLESS
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        os.makedirs(self.user_data_dir, exist_ok=True)

    async def start(self) -> BrowserContext:
        """Launches a persistent browser session with stealth evasion scripts."""
        self.playwright = await async_playwright().start()

        # Launch persistent context to preserve logged-in cookies and sessions
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            user_agent=settings.USER_AGENT,
            viewport={"width": 1366, "height": 768},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--disable-dev-shm-usage",
                "--disable-extensions"
            ]
        )

        # Inject stealth scripts into all new pages
        await self.context.add_init_script("""
            // Overwrite navigator.webdriver to hide automation
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Mock chrome object
            window.chrome = {
                runtime: {}
            };

            // Mock permissions query
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        logger.info(f"Stealth browser launched (Headless={self.headless}, UserData={self.user_data_dir})")
        return self.context

    async def human_type(self, page: Page, selector: str, text: str):
        """Types text with natural human variance in keystroke timing (40ms - 120ms)."""
        await page.click(selector)
        await page.fill(selector, "")  # Clear existing
        for char in text:
            await page.type(selector, char, delay=random.randint(40, 120))
            if random.random() < 0.05:
                await asyncio.sleep(random.uniform(0.1, 0.3))

    async def close(self):
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser session closed cleanly")
