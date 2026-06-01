"""API Router for AI Shadow Portfolio."""

from fastapi import APIRouter
from loguru import logger

router = APIRouter()


@router.get("/summary")
async def get_summary():
    """Get complete shadow portfolio summary."""
    from app.shadow_portfolio.engine import get_portfolio_summary
    return await get_portfolio_summary()


@router.post("/run-cycle")
async def run_cycle():
    """Manually trigger a shadow portfolio cycle."""
    from app.shadow_portfolio.engine import run_shadow_cycle
    try:
        result = await run_shadow_cycle()
        return {"status": "cycle_complete", "result": result}
    except Exception as e:
        logger.error(f"Shadow cycle error: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/initialize")
async def initialize(capital: float = 20000.0):
    """Initialize shadow portfolio with given capital."""
    from app.shadow_portfolio.engine import initialize_portfolio
    result = await initialize_portfolio(capital)
    return {"status": "initialized", "portfolio": result}


@router.post("/reset")
async def reset(capital: float = 20000.0):
    """Reset the entire shadow portfolio (deletes all data)."""
    from app.shadow_portfolio.engine import reset_portfolio
    result = await reset_portfolio(capital)
    return {"status": "reset", "portfolio": result}


@router.post("/snapshot")
async def take_snapshot():
    """Manually take a daily snapshot."""
    from app.shadow_portfolio.engine import take_daily_snapshot
    await take_daily_snapshot()
    return {"status": "snapshot_taken"}


@router.get("/cycle-history")
async def cycle_history(limit: int = 20):
    """Get history of all shadow portfolio cycle runs."""
    from app.shadow_portfolio.engine import get_cycle_history
    cycles = await get_cycle_history(limit)
    return {"cycles": cycles}
