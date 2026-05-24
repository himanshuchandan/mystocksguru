"""Technical Analysis Agent - scans stocks for momentum, breakouts, setups."""

import yfinance as yf
import pandas as pd
import pandas_ta as ta
from loguru import logger
from typing import Optional


# Stock universes - Yahoo Finance symbols
NIFTY_30 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "ITC.NS",
    "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "MARUTI.NS", "ASIANPAINT.NS",
    "HCLTECH.NS", "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "WIPRO.NS",
    "NESTLEIND.NS", "TATASTEEL.NS", "POWERGRID.NS", "NTPC.NS",
    "M&M.NS", "TECHM.NS", "INDUSINDBK.NS", "DRREDDY.NS", "CIPLA.NS", "BAJAJFINSV.NS",
]

NIFTY_50 = NIFTY_30 + [
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "BPCL.NS", "BRITANNIA.NS",
    "COALINDIA.NS", "DIVISLAB.NS", "EICHERMOT.NS", "GRASIM.NS", "HEROMOTOCO.NS",
    "HINDALCO.NS", "JSWSTEEL.NS", "ONGC.NS", "SBILIFE.NS", "SHRIRAMFIN.NS",
    "TATACONSUM.NS", "TATAMOTORS.NS", "TRENT.NS", "VEDL.NS", "WIPRO.NS",
]

NIFTY_100 = NIFTY_50 + [
    "ABB.NS", "ADANIGREEN.NS", "AMBUJACEM.NS", "AUROPHARMA.NS", "BAJAJ-AUTO.NS",
    "BANKBARODA.NS", "BEL.NS", "BERGEPAINT.NS", "BOSCHLTD.NS", "CANBK.NS",
    "CHOLAFIN.NS", "COLPAL.NS", "DABUR.NS", "DLF.NS", "GAIL.NS",
    "GODREJCP.NS", "HAVELLS.NS", "HDFCAMC.NS", "HDFCLIFE.NS", "ICICIPRULI.NS",
    "IDEA.NS", "IGL.NS", "INDHOTEL.NS", "INDIGO.NS", "IOC.NS",
    "IRCTC.NS", "JINDALSTEL.NS", "JSWENERGY.NS", "JUBLFOOD.NS", "LTF.NS",
    "LTIM.NS", "LUPIN.NS", "MARICO.NS", "MOTHERSON.NS", "MUTHOOTFIN.NS",
    "NAUKRI.NS", "NHPC.NS", "PIDILITIND.NS", "PNB.NS", "POLYCAB.NS",
    "RECLTD.NS", "SAIL.NS", "SIEMENS.NS", "SRF.NS", "TORNTPHARM.NS",
    "TVSMOTOR.NS", "UNIONBANK.NS", "UNITDSPR.NS", "ZOMATO.NS", "ZYDUSLIFE.NS",
]

NIFTY_200 = NIFTY_100 + [
    "ACC.NS", "ALKEM.NS", "ASHOKLEY.NS", "ASTRAL.NS", "ATUL.NS",
    "AUBANK.NS", "BALKRISIND.NS", "BANDHANBNK.NS", "BATAINDIA.NS", "BHARATFORG.NS",
    "BIOCON.NS", "BSE.NS", "CANFINHOME.NS", "CGPOWER.NS", "CHAMBALFER.NS",
    "COFORGE.NS", "CONCOR.NS", "CROMPTON.NS", "CUB.NS", "CUMMINSIND.NS",
    "DEEPAKNTR.NS", "DELHIVERY.NS", "DIXON.NS", "ESCORTS.NS", "EXIDEIND.NS",
    "FEDERALBNK.NS", "GLENMARK.NS", "GMRINFRA.NS", "GNFC.NS", "GODREJPROP.NS",
    "GRANULES.NS", "HAL.NS", "IDFCFIRSTB.NS", "IEX.NS", "IIFL.NS",
    "INDUSTOWER.NS", "IRFC.NS", "KAJARIACER.NS", "KEI.NS", "LALPATHLAB.NS",
    "LICHSGFIN.NS", "LTTS.NS", "M&MFIN.NS", "MANAPPURAM.NS", "MAXHEALTH.NS",
    "MCX.NS", "METROPOLIS.NS", "MFSL.NS", "MGL.NS", "MPHASIS.NS",
    "NAM-INDIA.NS", "NATIONALUM.NS", "NAVINFLUOR.NS", "NMDC.NS", "OBEROIRLTY.NS",
    "OFSS.NS", "PAGEIND.NS", "PATANJALI.NS", "PERSISTENT.NS", "PETRONET.NS",
    "PFC.NS", "PIIND.NS", "PRESTIGE.NS", "PVRINOX.NS", "RAMCOCEM.NS",
    "RELAXO.NS", "SJVN.NS", "SOLARINDS.NS", "SONACOMS.NS", "STARHEALTH.NS",
    "SUNDARMFIN.NS", "SUNTV.NS", "SUPREMEIND.NS", "SYNGENE.NS", "TATACHEM.NS",
    "TATACOMM.NS", "TATAELXSI.NS", "TATAPOWER.NS", "THERMAX.NS", "TIINDIA.NS",
    "TORNTPOWER.NS", "TRENT.NS", "TRIDENT.NS", "UBL.NS", "UPL.NS",
    "VBL.NS", "VOLTAS.NS", "WHIRLPOOL.NS", "YESBANK.NS", "ZEEL.NS",
]

UNIVERSE_MAP = {
    "nifty30": NIFTY_30,
    "nifty50": NIFTY_50,
    "nifty100": NIFTY_100,
    "nifty200": NIFTY_200,
}


def get_scan_universe() -> list:
    """Get the stock list based on config."""
    from app.config import settings
    return UNIVERSE_MAP.get(settings.scan_universe, NIFTY_50)


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

    # Convert numpy types to native Python types for JSON serialization
    import numpy as np
    for k, v in result.items():
        if isinstance(v, (np.bool_, np.generic)):
            result[k] = v.item()

    return result


def scan_market() -> list[dict]:
    """Scan NSE stocks and return momentum candidates based on config."""
    from app.config import settings

    universe = get_scan_universe()
    threshold = settings.momentum_threshold

    logger.info(f"🔍 Scanning {settings.scan_universe} ({len(universe)} stocks), threshold={threshold}...")
    results = []

    for symbol in universe:
        analysis = analyze_stock_technical(symbol)
        if analysis and analysis["momentum_score"] >= threshold:
            results.append(analysis)

    results.sort(key=lambda x: x["momentum_score"], reverse=True)
    logger.info(f"Found {len(results)} momentum candidates (score >= {threshold})")
    return results
