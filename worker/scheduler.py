"""24/7/365 Autonomous Worker Daemon & Polling Scheduler."""
import asyncio
import logging
import signal
from typing import Optional

from core.database import DatabaseManager
from core.profile_manager import ProfileManager
from core.models import ApplicationStatus
from discovery.aggregator import JobAggregator
from applicator.browser import BrowserSessionManager
from applicator.form_filler import ApplicationAgent
from applicator.hitl import HITLNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("MCPWorker")


class AutonomousWorker:
    def __init__(
        self,
        db_path: str = "data/mcp_jobs.db",
        poll_interval_seconds: Optional[int] = None
    ):
        self.db = DatabaseManager(db_path)
        self.profile_mgr = ProfileManager()
        self.hitl = HITLNotifier()
        self.session_mgr = BrowserSessionManager()
        self.aggregator = JobAggregator(self.db, self.profile_mgr)
        self.agent = ApplicationAgent(self.db, self.profile_mgr, self.session_mgr, self.hitl)

        self.poll_interval = poll_interval_seconds or (self.profile_mgr.preferences.polling_interval_minutes * 60)
        self.is_running = False

    async def start(self):
        """Starts the 24/7 continuous discovery and application loop."""
        self.is_running = True
        logger.info("=" * 60)
        logger.info("🚀 MCP Autonomous Job Scout & Applicator Started")
        logger.info(f"Target Roles: {self.profile_mgr.preferences.target_roles}")
        logger.info(f"Poll Interval: {self.poll_interval // 60} minutes")
        logger.info(f"Auto-Apply Mode: {self.profile_mgr.preferences.auto_apply}")
        logger.info("=" * 60)

        cycle_count = 0
        try:
            while self.is_running:
                cycle_count += 1
                logger.info(f"\n--- Starting Discovery Cycle #{cycle_count} ---")

                # 1. Run live discovery across all enabled platforms
                summary = await self.aggregator.run_discovery_cycle()
                logger.info(f"Cycle #{cycle_count} Summary: {summary}")

                # 2. Process Queued Applications (if auto_apply is on)
                if self.profile_mgr.preferences.auto_apply:
                    queued_jobs = self.db.list_jobs(status=ApplicationStatus.QUEUED, limit=5)
                    if queued_jobs:
                        logger.info(f"Processing {len(queued_jobs)} queued jobs for automated application...")
                        for job in queued_jobs:
                            if not self.is_running:
                                break
                            await self.agent.apply(job, auto_submit=True)
                            await asyncio.sleep(5)  # Human cool-down between applications

                # Sleep until next scheduled interval
                logger.info(f"Sleeping for {self.poll_interval} seconds until next cycle...")
                await asyncio.sleep(self.poll_interval)

        except asyncio.CancelledError:
            logger.info("Worker received cancel signal, shutting down...")
        finally:
            await self.shutdown()

    async def shutdown(self):
        self.is_running = False
        await self.session_mgr.close()
        logger.info("MCP Autonomous Worker stopped successfully.")


if __name__ == "__main__":
    worker = AutonomousWorker()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(worker.start())
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Exiting...")
