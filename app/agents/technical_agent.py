"""Technical Analysis Agent - scans stocks for momentum, breakouts, setups."""

import yfinance as yf
import pandas as pd
import pandas_ta as ta
from loguru import logger
from typing import Optional


NSE_TOP_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "ITC.NS",
    "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "MARUTI.NS", "ASIANPAINT.NS",
    "HCLTECH.NS", "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "WIPRO.NS",
    "NESTLEIND.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "POWERGRID.NS", "NTPC.NS",
    "M&M.NS", "TECHM.NS", "INDUSINDBK.NS", "DRREDDY.NS", "CIPLA.NS",
]


def get_stock_data(symbol: str, period: str = "3mo", interval: str = "1d") -> Optional[pd.DataFrame]:
    """Fetch stock data from Yahoo Finance."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return None
        return df
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
        return None


def analyze_stock_technical(symbol: str) -> Optional[dict]:
    """Run technical analysis on a stock."""
    df = get_stock_data(symbol)
    if df is None or len(df) < 20:
        return None

    # Calculate indicators
    df.ta.rsi(length=14, append=True)
    df.ta.macd(append=True)
    df.ta.ema(length=20, append=True)
    df.ta.ema(length=50, append=True)
    df.ta.atr(length=14, append=True)
    
    # Volume analysis
    avg_volume = df["Volume"].rolling(20).mean().iloc[-1]
    current_volume = df["Volume"].iloc[-1]
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    result = {
        "symbol": symbol,
        "price": round(latest["Close"], 2),
        "change_pct": round(((latest["Close"] - prev["Close"]) / prev["Close"]) * 100, 2),
        "rsi": round(latest.get("RSI_14", 0), 2),
        "macd": round(latest.get("MACD_12_26_9", 0), 4),
        "macd_signal": round(latest.get("MACDs_12_26_9", 0), 4),
        "ema_20": round(latest.get("EMA_20", 0), 2),
        "ema_50": round(latest.get("EMA_50", 0), 2),
        "atr": round(latest.get("ATRr_14", 0), 2),
        "volume_ratio": round(volume_ratio, 2),
        "above_ema20": latest["Close"] > latest.get("EMA_20", 0),
        "above_ema50": latest["Close"] > latest.get("EMA_50", 0),
        "macd_bullish": latest.get("MACD_12_26_9", 0) > latest.get("MACDs_12_26_9", 0),
    }

    # Scoring
    score = 0
    if result["rsi"] > 50 and result["rsi"] < 70:
        score += 1
    if result["above_ema20"]:
        score += 1
    if result["above_ema50"]:
        score += 1
    if result["macd_bullish"]:
        score += 1
    if result["volume_ratio"] > 1.5:
        score += 1

    result["momentum_score"] = score
    result["signal"] = "STRONG_BUY" if score >= 4 else "BUY" if score >= 3 else "NEUTRAL" if score >= 2 else "WEAK"

    return result


def scan_market() -> list[dict]:
    """Scan top NSE stocks and return momentum candidates."""
    logger.info("🔍 Scanning market for momentum stocks...")
    results = []

    for symbol in NSE_TOP_STOCKS:
        analysis = analyze_stock_technical(symbol)
        if analysis and analysis["momentum_score"] >= 3:
            results.append(analysis)

    results.sort(key=lambda x: x["momentum_score"], reverse=True)
    logger.info(f"Found {len(results)} momentum candidates")
    return results
