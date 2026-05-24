"""Macro Agent - tracks global/Indian macro signals."""

import yfinance as yf
from loguru import logger


MACRO_TICKERS = {
    "nifty": "^NSEI",
    "sensex": "^BSESN",
    "bank_nifty": "^NSEBANK",
    "usd_inr": "INR=X",
    "crude_oil": "CL=F",
    "gold": "GC=F",
    "us_10y": "^TNX",
    "vix_india": "^INDIAVIX",
    "sp500": "^GSPC",
    "nasdaq": "^IXIC",
    "dxy": "DX-Y.NYB",
}


def get_macro_snapshot() -> dict:
    """Get current macro indicators snapshot."""
    logger.info("📊 Fetching macro snapshot...")
    snapshot = {}

    for name, ticker in MACRO_TICKERS.items():
        try:
            data = yf.Ticker(ticker).history(period="5d")
            if not data.empty:
                current = data["Close"].iloc[-1]
                prev = data["Close"].iloc[-2] if len(data) > 1 else current
                change_pct = ((current - prev) / prev) * 100
                snapshot[name] = {
                    "value": round(current, 2),
                    "change_pct": round(change_pct, 2),
                }
        except Exception as e:
            logger.warning(f"Failed to fetch {name}: {e}")

    return snapshot


def get_market_regime(snapshot: dict) -> str:
    """Determine current market regime from macro data."""
    signals = []

    vix = snapshot.get("vix_india", {}).get("value", 15)
    nifty_change = snapshot.get("nifty", {}).get("change_pct", 0)
    crude_change = snapshot.get("crude_oil", {}).get("change_pct", 0)
    dxy_change = snapshot.get("dxy", {}).get("change_pct", 0)

    if vix > 20:
        signals.append("HIGH_VOLATILITY")
    if nifty_change > 0.5:
        signals.append("BULLISH_TREND")
    elif nifty_change < -0.5:
        signals.append("BEARISH_TREND")
    if crude_change > 2:
        signals.append("CRUDE_SPIKE")
    if dxy_change > 0.5:
        signals.append("USD_STRONG")

    if "HIGH_VOLATILITY" in signals and "BEARISH_TREND" in signals:
        return "RISK_OFF"
    elif "BULLISH_TREND" in signals:
        return "RISK_ON"
    else:
        return "NEUTRAL"
