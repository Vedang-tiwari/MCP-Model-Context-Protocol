"""Unit tests for BrowserSessionManager with real Chrome channel, CDP integration, and tab reuse."""
import sys
import os
sys.path.insert(0, os.path.abspath("."))
import unittest
import asyncio
from pathlib import Path
from applicator.browser import BrowserSessionManager
from core.config import settings


class TestBrowserSessionManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path("data/test_browser_unit")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.session_mgr = BrowserSessionManager(
            user_data_dir=str(self.temp_dir),
            headless=True,
            channel="chrome"
        )

    def tearDown(self):
        asyncio.run(self.session_mgr.close())

    def test_browser_initialization_defaults(self):
        self.assertEqual(self.session_mgr.channel, "chrome")
        self.assertEqual(self.session_mgr.remote_debugging_port, 9222)
        self.assertEqual(self.session_mgr.cdp_url, "http://127.0.0.1:9222")

    def test_browser_launch_and_tab_reuse(self):
        async def _run():
            # 1. Start browser
            ctx = await self.session_mgr.start()
            self.assertIsNotNone(ctx)

            # 2. Acquire first tab
            page1 = await self.session_mgr.new_tab()
            await page1.goto("https://example.com")
            title1 = await page1.title()
            self.assertEqual(title1, "Example Domain")

            # 3. Acquire second tab (must be in the SAME context/browser)
            page2 = await self.session_mgr.new_tab()
            await page2.goto("https://example.org")
            title2 = await page2.title()
            self.assertEqual(title2, "Example Domain")

            # Both pages must reside in the same browser context
            self.assertIn(page1, ctx.pages)
            self.assertIn(page2, ctx.pages)
            self.assertGreaterEqual(len(ctx.pages), 2)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
