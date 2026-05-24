from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from loguru import logger

router = APIRouter()


class StockQuery(BaseModel):
    symbol: str
    timeframe: str = "swing"  # intraday, swing, positional, long-term


@router.post("/stock")
async def analyze_stock(query: StockQuery):
    """Get AI analysis for a specific stock."""
    try:
        from app.agents.orchestrator import analyze_single_stock
        return await analyze_single_stock(query.symbol, query.timeframe)
    except Exception as e:
        logger.error(f"Stock analysis failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/debate")
async def debate_stock(query: StockQuery):
    """Run multi-agent debate (Bull vs Bear vs Risk) on a stock."""
    try:
        from app.agents.orchestrator import run_stock_debate
        return await run_stock_debate(query.symbol)
    except Exception as e:
        logger.error(f"Debate failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/market-summary")
async def market_summary():
    """Get today's market summary."""
    from app.agents.orchestrator import get_market_summary
    return await get_market_summary()
