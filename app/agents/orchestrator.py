"""Orchestrator - coordinates all agents and triggers notifications."""

from loguru import logger
from app.agents.macro_agent import get_macro_snapshot, get_market_regime
from app.agents.technical_agent import scan_market, analyze_stock_technical
from app.agents.news_agent import get_news_summary
from app.agents.portfolio_agent import analyze_portfolio
from app.agents.decision_agent import generate_market_intelligence, analyze_stock_detail
from app.services.telegram_service import send_telegram_alert


async def run_market_scan() -> dict:
    """Run full market scan - called by scheduler or manually."""
    logger.info("🚀 Running full market scan...")

    # 1. Macro snapshot
    macro = get_macro_snapshot()
    regime = get_market_regime(macro)
    logger.info(f"Market regime: {regime}")

    # 2. Technical scan
    momentum_stocks = scan_market()

    # 3. News
    news = await get_news_summary()

    # 4. Portfolio (if connected)
    portfolio = await analyze_portfolio()

    # 5. AI Decision Agent (graceful fallback if LLM not configured)
    intelligence = None
    try:
        intelligence = await generate_market_intelligence(
            macro_data=macro,
            technical_signals=momentum_stocks,
            news_data=news,
            portfolio_data=portfolio,
        )
    except Exception as e:
        logger.warning(f"LLM analysis failed (check API key): {e}")
        # Build a basic report without LLM
        intelligence = _build_basic_report(regime, macro, momentum_stocks, news)

    # 6. Send Telegram alert
    await send_telegram_alert(intelligence)

    return {
        "regime": regime,
        "momentum_stocks": len(momentum_stocks),
        "intelligence_preview": intelligence[:500] + "..." if len(intelligence) > 500 else intelligence,
    }


def _build_basic_report(regime: str, macro: dict, momentum_stocks: list, news: dict) -> str:
    """Build a basic report when LLM is unavailable."""
    lines = ["🤖 *AI Market Copilot - Scan Report*\n"]
    lines.append(f"📊 *Market Regime:* {regime}\n")

    lines.append("*Macro Snapshot:*")
    for key, val in list(macro.items())[:8]:
        lines.append(f"  • {key.replace('_', ' ').title()}: {val.get('value', 'N/A')} ({val.get('change_pct', 0):+.2f}%)")

    if momentum_stocks:
        lines.append(f"\n🎯 *Momentum Stocks ({len(momentum_stocks)}):*")
        for s in momentum_stocks[:5]:
            lines.append(f"  • {s['symbol'].replace('.NS', '')}: ₹{s['price']} | RSI:{s['rsi']} | Score:{s['momentum_score']}/5 | {s['signal']}")

    headlines = news.get("moneycontrol", [])[:5] + news.get("economic_times", [])[:5]
    if headlines:
        lines.append("\n📰 *Top Headlines:*")
        for h in headlines[:5]:
            lines.append(f"  • {h}")

    lines.append("\n⚠️ _LLM not configured - showing raw signals only_")
    return "\n".join(lines)


async def analyze_single_stock(symbol: str, timeframe: str = "swing") -> dict:
    """Analyze a single stock with AI."""
    # Ensure .NS suffix
    if not symbol.endswith(".NS"):
        symbol = f"{symbol}.NS"

    technical = analyze_stock_technical(symbol)
    if not technical:
        return {"error": f"Could not fetch data for {symbol}. Use NSE symbols like RELIANCE, TCS, INFY."}

    try:
        analysis = await analyze_stock_detail(symbol, technical, timeframe)
    except Exception as e:
        logger.warning(f"LLM failed: {e}")
        analysis = f"Technical Data (LLM unavailable):\nPrice: ₹{technical['price']}\nRSI: {technical['rsi']}\nMACD Bullish: {technical['macd_bullish']}\nAbove EMA20: {technical['above_ema20']}\nAbove EMA50: {technical['above_ema50']}\nVolume Ratio: {technical['volume_ratio']}x\nMomentum Score: {technical['momentum_score']}/5\nSignal: {technical['signal']}"

    return {
        "symbol": symbol,
        "technical": technical,
        "ai_analysis": analysis,
    }


async def get_market_summary() -> dict:
    """Quick market summary."""
    macro = get_macro_snapshot()
    regime = get_market_regime(macro)
    return {"macro": macro, "regime": regime}


async def run_stock_debate(symbol: str) -> dict:
    """Run multi-agent debate on a stock."""
    from app.agents.debate_agent import run_debate

    if not symbol.endswith(".NS"):
        symbol = f"{symbol}.NS"

    technical = analyze_stock_technical(symbol)
    if not technical:
        return {"error": f"Could not fetch data for {symbol}. Use NSE symbols like RELIANCE, TCS, INFY."}

    macro = get_macro_snapshot()
    news = await get_news_summary()

    try:
        result = await run_debate(
            stock_symbol=symbol,
            technical_data=technical,
            macro_data=macro,
            news_data=news,
        )
        # Send full debate to Telegram
        await send_telegram_alert(f"🗣️ Debate: {symbol}\n\n{result['final_verdict']}")
        return result
    except Exception as e:
        logger.warning(f"Debate failed: {e}")
        return {"error": f"Debate failed (check LLM API key): {str(e)}", "technical": technical}
