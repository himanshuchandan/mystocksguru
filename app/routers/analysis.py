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


@router.get("/search")
async def search_stocks(q: str = ""):
    """Autocomplete search for stock symbols."""
    from app.agents.technical_agent import NIFTY_100, NIFTY_200
    all_stocks = list(set(NIFTY_200))  # Use largest universe
    # Strip .NS for matching
    query = q.strip().upper()
    if not query:
        return []
    results = []
    for s in all_stocks:
        name = s.replace(".NS", "")
        if query in name:
            results.append({"symbol": name, "full": s})
    # Sort: starts-with first, then contains
    results.sort(key=lambda x: (0 if x["symbol"].startswith(query) else 1, x["symbol"]))
    return results[:10]


@router.get("/overview/{symbol}")
async def stock_overview(symbol: str):
    """Get quick technical overview for a stock (no LLM call)."""
    try:
        from app.agents.technical_agent import analyze_stock_technical
        symbol = symbol.strip().upper()
        if not symbol.endswith(".NS"):
            symbol = f"{symbol}.NS"
        data = analyze_stock_technical(symbol)
        if not data:
            return JSONResponse(status_code=404, content={"error": f"Could not fetch data for {symbol}. Use NSE symbols like RELIANCE, TCS, INFY."})
        return data
    except Exception as e:
        logger.error(f"Overview failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/chart/{symbol}")
async def get_chart_data(symbol: str, period: str = "6mo", interval: str = "1d"):
    """Get OHLCV chart data for a stock.

    Args:
        symbol: Stock symbol (e.g. RELIANCE, TCS)
        period: Data period (1mo, 3mo, 6mo, 1y, 2y, 5y)
        interval: Candle interval (1m, 5m, 15m, 1h, 1d, 1wk)
    """
    try:
        import yfinance as yf
        import numpy as np

        if not symbol.endswith(".NS"):
            symbol = f"{symbol}.NS"

        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)

        if df.empty:
            return JSONResponse(status_code=404, content={"error": f"No data for {symbol}"})

        # Convert to list of OHLCV candles for lightweight-charts
        candles = []
        volumes = []
        use_date_string = interval in ("1d", "1wk", "1mo")
        for idx, row in df.iterrows():
            ts = idx.strftime("%Y-%m-%d") if use_date_string else int(idx.timestamp())
            candles.append({
                "time": ts,
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
            })
            volumes.append({
                "time": ts,
                "value": int(row["Volume"]),
                "color": "rgba(38, 166, 154, 0.5)" if row["Close"] >= row["Open"] else "rgba(239, 83, 80, 0.5)",
            })

        return {
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "candles": candles,
            "volumes": volumes,
        }
    except Exception as e:
        logger.error(f"Chart data failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
