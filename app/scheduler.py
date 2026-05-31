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


async def scheduled_shadow_cycle():
    """Shadow portfolio cycle - runs every 2 hours during market hours."""
    from datetime import datetime
    now = datetime.now()

    # Only during market hours
    if now.hour < settings.market_open_hour or now.hour >= settings.market_close_hour:
        return
    if now.weekday() >= 5:
        return

    from app.shadow_portfolio.engine import run_shadow_cycle
    try:
        await run_shadow_cycle()
    except Exception as e:
        logger.error(f"Shadow portfolio cycle failed: {e}")


async def scheduled_daily_snapshot():
    """Take daily snapshot at market close."""
    from datetime import datetime
    now = datetime.now()
    if now.weekday() >= 5:
        return

    from app.shadow_portfolio.engine import take_daily_snapshot
    try:
        await take_daily_snapshot()
    except Exception as e:
        logger.error(f"Daily snapshot failed: {e}")


def start_scheduler():
    """Start the background scheduler."""
    if not settings.scan_enabled:
        logger.info("⏸️ Scheduled scans disabled (SCAN_ENABLED=false)")
        return

    scheduler.add_job(
        scheduled_scan,
        "interval",
        minutes=settings.scan_interval_minutes,
        id="market_scan",
        replace_existing=True,
    )

    # Shadow portfolio: every 2 hours during market hours (9:30, 11:30, 13:30, 15:30)
    scheduler.add_job(
        scheduled_shadow_cycle,
        "cron",
        hour="9,11,13,15",
        minute=30,
        id="shadow_portfolio_cycle",
        replace_existing=True,
    )

    # Daily snapshot at 15:45 (after market close)
    scheduler.add_job(
        scheduled_daily_snapshot,
        "cron",
        hour=15,
        minute=45,
        id="shadow_daily_snapshot",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f"⏰ Scheduler started - scanning every {settings.scan_interval_minutes} minutes")
    logger.info("⏰ Shadow Portfolio: cycles at 9:30, 11:30, 13:30, 15:30 | snapshot at 15:45")


def stop_scheduler():
    """Stop the scheduler."""
    scheduler.shutdown()
