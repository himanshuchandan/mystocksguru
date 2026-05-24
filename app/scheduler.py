"""APScheduler setup for periodic market scans."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from app.config import settings

scheduler = AsyncIOScheduler()


async def scheduled_scan():
    """Periodic market scan job."""
    from datetime import datetime
    now = datetime.now()

    # Only run during market hours (IST)
    if now.hour < settings.market_open_hour or now.hour >= settings.market_close_hour:
        logger.info("Outside market hours, skipping scan.")
        return

    # Weekday check (Mon=0, Sun=6)
    if now.weekday() >= 5:
        logger.info("Weekend, skipping scan.")
        return

    from app.agents.orchestrator import run_market_scan
    await run_market_scan()


def start_scheduler():
    """Start the background scheduler."""
    scheduler.add_job(
        scheduled_scan,
        "interval",
        minutes=settings.scan_interval_minutes,
        id="market_scan",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"⏰ Scheduler started - scanning every {settings.scan_interval_minutes} minutes")


def stop_scheduler():
    """Stop the scheduler."""
    scheduler.shutdown()
