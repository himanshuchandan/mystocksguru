from fastapi import APIRouter

router = APIRouter()


@router.get("/holdings")
async def get_holdings():
    """Get current portfolio holdings from Kite."""
    from app.services.kite_service import get_holdings
    return await get_holdings()


@router.get("/analysis")
async def get_portfolio_analysis():
    """Get AI-powered portfolio analysis."""
    from app.agents.portfolio_agent import analyze_portfolio
    return await analyze_portfolio()
