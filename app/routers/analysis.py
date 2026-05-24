from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class StockQuery(BaseModel):
    symbol: str
    timeframe: str = "swing"  # intraday, swing, positional, long-term


@router.post("/stock")
async def analyze_stock(query: StockQuery):
    """Get AI analysis for a specific stock."""
    from app.agents.orchestrator import analyze_single_stock
    return await analyze_single_stock(query.symbol, query.timeframe)


@router.post("/debate")
async def debate_stock(query: StockQuery):
    """Run multi-agent debate (Bull vs Bear vs Risk) on a stock.
    
    Multiple agents argue for and against the trade,
    then a moderator gives the final verdict.
    """
    from app.agents.orchestrator import run_stock_debate
    return await run_stock_debate(query.symbol)


@router.get("/market-summary")
async def market_summary():
    """Get today's market summary."""
    from app.agents.orchestrator import get_market_summary
    return await get_market_summary()
