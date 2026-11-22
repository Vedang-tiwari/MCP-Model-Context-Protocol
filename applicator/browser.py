"""Stealth browser manager using Playwright with persistent sessions, CDP connection to existing Chrome, and zero-test-flags operation."""
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
    def __init__(
        self,
        user_data_dir: Optional[str] = None,
        headless: Optional[bool] = None,
        channel: Optional[str] = None,
        cdp_url: Optional[str] = None,
        remote_debugging_port: Optional[int] = None
    ):
        self.user_data_dir = user_data_dir or settings.BROWSER_USER_DATA_DIR
        self.headless = headless if headless is not None else settings.PLAYWRIGHT_HEADLESS
        self.channel = channel or getattr(settings, "CHROME_CHANNEL", "chrome")
        self.cdp_url = cdp_url or getattr(settings, "CDP_URL", "http://127.0.0.1:9222")
        self.remote_debugging_port = remote_debugging_port or getattr(settings, "BROWSER_REMOTE_DEBUGGING_PORT", 9222)
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self._is_cdp: bool = False
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

    async def _inject_stealth_scripts(self, context: BrowserContext):
        """Injects stealth evasions into context to prevent automation detection."""
        try:
            await context.add_init_script("""
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
        except Exception as e:
            logger.debug(f"Stealth init script skipped: {e}")

    async def start(self) -> BrowserContext:
        """
        Connects to the user's existing Google Chrome browser or launches a persistent Chrome session.
        Avoids test banners ('Chrome is being controlled by automated test software') and opens all tabs in the same browser.
        """
        # Step 0: Check if existing context is still alive and responsive
        if self.context:
            try:
                if not self.context.is_closed():
                    _ = self.context.pages
                    return self.context
            except Exception:
                pass
            await self.close()

        if not self.playwright:
            self.playwright = await async_playwright().start()

        # Step 1: If user already has Chrome running with remote debugging port, connect directly to it!
        if self.cdp_url:
            try:
                cdp_browser = await self.playwright.chromium.connect_over_cdp(
                    self.cdp_url,
                    timeout=1500
                )
                self.browser = cdp_browser
                self.context = cdp_browser.contexts[0] if cdp_browser.contexts else await cdp_browser.new_context()
                self._is_cdp = True
                logger.info(f"Connected to existing Google Chrome browser via CDP at {self.cdp_url} (reusing user's active browser).")
                await self._inject_stealth_scripts(self.context)
                return self.context
            except Exception as cdp_err:
                logger.debug(f"CDP connection to existing Chrome not active ({cdp_err}). Launching official Chrome channel...")

        # Step 2: Launch official Google Chrome with no automation bar and remote debugging port enabled
        self._cleanup_stale_locks(self.user_data_dir)

        launch_args = [
            f"--remote-debugging-port={self.remote_debugging_port}",
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--start-maximized",
            "--no-first-run",
            "--no-default-browser-check"
        ]

        # Try official Chrome first; fallback to Chromium if official Chrome is not installed
        channels_to_try = [self.channel, None] if self.channel else [None]

        for ch in channels_to_try:
            try:
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    channel=ch,
                    headless=self.headless,
                    user_agent=settings.USER_AGENT,
                    viewport=None if not self.headless else {"width": 1366, "height": 768},
                    ignore_default_args=["--enable-automation"],
                    args=launch_args
                )
                self._is_cdp = False
                logger.info(f"Official Chrome browser launched successfully (channel={ch}, Headless={self.headless}, Port={self.remote_debugging_port})")
                break
            except Exception as launch_err:
                logger.warning(f"Persistent launch with channel='{ch}' failed ({launch_err}). Trying fallback...")

        # Step 3: Fallback handling if primary profile directory had lock contention
        if not self.context:
            fallback_dir = Path("data/browser_profile_fallback")
            fallback_dir.mkdir(parents=True, exist_ok=True)
            self._cleanup_stale_locks(str(fallback_dir))

            try:
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=str(fallback_dir),
                    channel=self.channel,
                    headless=self.headless,
                    user_agent=settings.USER_AGENT,
                    viewport={"width": 1366, "height": 768},
                    ignore_default_args=["--enable-automation"],
                    args=launch_args
                )
                self._is_cdp = False
            except Exception as e2:
                logger.warning(f"Fallback persistent launch failed ({e2}). Launching non-persistent browser context...")
                self.browser = await self.playwright.chromium.launch(
                    channel=self.channel,
                    headless=self.headless,
                    ignore_default_args=["--enable-automation"],
                    args=launch_args
                )
                self.context = await self.browser.new_context(
                    user_agent=settings.USER_AGENT,
                    viewport={"width": 1366, "height": 768}
                )
                self._is_cdp = False

        await self._inject_stealth_scripts(self.context)
        return self.context

    async def new_tab(self) -> Page:
        """
        Acquires a tab in the active browser, reusing a blank tab if available or opening a new tab
        in the SAME browser window.
        """
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
        """Closes browser session or disconnects from CDP cleanly."""
        if self._is_cdp:
            # For CDP, disconnect without terminating user's active Chrome process
            try:
                if self.browser:
                    await self.browser.close()
            except Exception:
                pass
            finally:
                self.browser = None
                self.context = None
                self._is_cdp = False
            logger.info("Disconnected from existing Chrome CDP session cleanly.")
            return

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
