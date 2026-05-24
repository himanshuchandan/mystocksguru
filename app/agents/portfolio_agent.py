"""Portfolio Agent - analyzes current holdings via Kite."""

from loguru import logger
from app.services.kite_service import get_holdings


async def analyze_portfolio() -> dict:
    """Analyze current portfolio for risk and opportunities."""
    holdings = await get_holdings()

    if not holdings.get("holdings"):
        return {"status": "no_holdings", "message": "No holdings found or Kite not connected."}

    total_invested = 0
    total_current = 0
    sector_exposure = {}
    alerts = []

    for h in holdings["holdings"]:
        invested = h.get("average_price", 0) * h.get("quantity", 0)
        current = h.get("last_price", 0) * h.get("quantity", 0)
        total_invested += invested
        total_current += current

        pnl_pct = ((current - invested) / invested * 100) if invested > 0 else 0

        # Flag high loss positions
        if pnl_pct < -10:
            alerts.append(f"⚠️ {h['tradingsymbol']} down {pnl_pct:.1f}% - review stop loss")

        # Flag concentrated positions
        if total_current > 0 and current / total_current > 0.25:
            alerts.append(f"⚠️ {h['tradingsymbol']} is {current/total_current*100:.0f}% of portfolio - consider rebalancing")

    return {
        "total_invested": round(total_invested, 2),
        "total_current": round(total_current, 2),
        "overall_pnl_pct": round(((total_current - total_invested) / total_invested * 100), 2) if total_invested > 0 else 0,
        "num_holdings": len(holdings["holdings"]),
        "risk_alerts": alerts,
        "holdings": holdings["holdings"],
    }
