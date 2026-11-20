"""Stealth browser manager using Playwright with persistent sessions, robust lock handling, and anti-bot evasions."""
import os
import random
import asyncio
import logging
import shutil
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, BrowserContext, Page, Browser
from core.config import settings

logger = logging.getLogger(__name__)


class BrowserSessionManager:
    def __init__(self, user_data_dir: Optional[str] = None, headless: Optional[bool] = None):
        self.user_data_dir = user_data_dir or settings.BROWSER_USER_DATA_DIR
        self.headless = headless if headless is not None else settings.PLAYWRIGHT_HEADLESS
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        os.makedirs(self.user_data_dir, exist_ok=True)

    def _cleanup_stale_locks(self, profile_dir: str):
        """Removes stale Chromium Singleton lock files that prevent relaunch on Windows."""
        p = Path(profile_dir)
        if not p.exists():
            return
        lock_patterns = ["*Singleton*", "*lockfile*", "*LOCK*"]
        for pattern in lock_patterns:
            for lock_file in p.glob(pattern):
                try:
                    if lock_file.is_file() or lock_file.is_symlink():
                        lock_file.unlink(missing_ok=True)
                        logger.debug(f"Removed stale Chromium lock file: {lock_file}")
                except Exception:
                    pass

    async def start(self) -> BrowserContext:
        """Launches a persistent browser session with stealth evasion scripts and fallback handling."""
        if self.context:
            try:
                if not self.context.is_closed():
                    # Check responsiveness
                    _ = self.context.pages
                    return self.context
            except Exception:
                pass
            await self.close()

        if not self.playwright:
            self.playwright = await async_playwright().start()

        self._cleanup_stale_locks(self.user_data_dir)

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--start-maximized"
        ]

        # Attempt 1: Launch Persistent Context on primary profile
        try:
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=self.headless,
                user_agent=settings.USER_AGENT,
                viewport=None if not self.headless else {"width": 1366, "height": 768},
                args=launch_args
            )
        except Exception as e:
            logger.warning(f"Persistent browser launch failed on primary profile ({e}). Using isolated runtime profile...")
            fallback_dir = Path("data/browser_profile_fallback")
            fallback_dir.mkdir(parents=True, exist_ok=True)
            self._cleanup_stale_locks(str(fallback_dir))

            try:
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=str(fallback_dir),
                    headless=self.headless,
                    user_agent=settings.USER_AGENT,
                    viewport={"width": 1366, "height": 768},
                    args=launch_args
                )
            except Exception as e2:
                logger.warning(f"Fallback persistent launch failed ({e2}). Launching non-persistent browser context...")
                self.browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                    args=launch_args
                )
                self.context = await self.browser.new_context(
                    user_agent=settings.USER_AGENT,
                    viewport={"width": 1366, "height": 768}
                )

        # Inject stealth evasions into all pages
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            window.chrome = {
                runtime: {}
            };

            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        logger.info(f"Stealth browser launched successfully (Headless={self.headless})")
        return self.context

    async def new_tab(self) -> Page:
        """Acquires a tab in the browser, reusing a blank tab if available."""
        context = await self.start()
        for p in context.pages:
            try:
                if not p.is_closed() and (p.url == "about:blank" or not p.url):
                    await p.bring_to_front()
                    return p
            except Exception:
                pass
        page = await context.new_page()
        try:
            await page.bring_to_front()
        except Exception:
            pass
        return page

    async def human_type(self, page: Page, selector: str, text: str):
        """Types text with natural human variance in keystroke timing (40ms - 120ms)."""
        await page.click(selector)
        await page.fill(selector, "")  # Clear existing
        for char in text:
            await page.type(selector, char, delay=random.randint(40, 110))
            if random.random() < 0.05:
                await asyncio.sleep(random.uniform(0.1, 0.25))

    async def close(self):
        try:
            if self.context:
                await self.context.close()
        except Exception:
            pass
        finally:
            self.context = None

        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass
        finally:
            self.browser = None

        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        finally:
            self.playwright = None
        logger.info("Browser session closed cleanly")
