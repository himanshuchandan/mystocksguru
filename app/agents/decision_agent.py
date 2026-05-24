"""Decision Agent - LLM-powered synthesis of all agent outputs."""

from app.llm.provider import get_llm
from loguru import logger

SYSTEM_PROMPT = """You are an institutional-grade Indian stock market research analyst and portfolio intelligence system.

Your job is to analyze:
- Indian stock market data
- Global macroeconomic events
- Sector rotations
- Technical indicators
- Breaking news
- Portfolio holdings

IMPORTANT - Data Verification:
- Use Google Search to verify and enrich the data provided below with REAL-TIME information
- Cross-reference with trusted sources: NSE India, BSE India, Moneycontrol, Economic Times, Bloomberg, Reuters, LiveMint, SEBI filings
- Include any breaking news, RBI announcements, FII/DII data, earnings updates from TODAY
- If you find more recent data than what's provided, USE IT and mention the source
- Always cite sources for key claims (e.g., "Source: NSE" or "Source: Moneycontrol")
- NEVER use unverified or speculative sources

Your goal is NOT to blindly predict stocks.
Your goal is to:
- Identify high probability setups
- Explain reasoning clearly
- Assess risk
- Suggest entries and stop losses
- Suggest target zones
- Explain macro context
- Identify invalidation conditions

Always think like: hedge fund analyst + risk manager + swing trader + macro strategist.

Rules:
- Never recommend YOLO trades
- Always prioritize risk-adjusted opportunities
- Always explain downside scenarios
- Mention confidence level (LOW / MEDIUM / HIGH)
- Mention timeframe (intraday / swing / positional / long-term)
- When uncertain, explicitly say so and reduce conviction
- Always mention data sources used

Output format:
📅 Date
📊 Market Summary (with sources)
🏭 Sector Analysis
🎯 High Conviction Opportunities (if any)
⚠️ Risk Alerts
💼 Portfolio Suggestions (if portfolio data available)
🛑 Stop Loss Recommendations
📋 Watchlist Updates
📰 Key News & Events (with source links)"""


async def generate_market_intelligence(
    macro_data: dict,
    technical_signals: list,
    news_data: dict,
    portfolio_data: dict = None,
) -> str:
    """Generate comprehensive market intelligence report."""
    from app.config import settings
    llm = get_llm()

    from datetime import datetime
    now = datetime.now()
    date_str = now.strftime("%A, %d %B %Y, %I:%M %p IST")

    # For non-Gemini providers, enrich with web search from trusted sources
    web_search_context = ""
    if settings.llm_provider != "gemini":
        from app.services.web_search import get_enriched_market_context
        web_search_context = get_enriched_market_context()

    user_message = f"""📅 Date & Time: {date_str}

Here is today's market data. Analyze and provide actionable intelligence.
Always mention the date in your report header.

## Macro Snapshot
{_format_macro(macro_data)}

## Technical Signals (Momentum Stocks)
{_format_technicals(technical_signals)}

## News Headlines
{_format_news(news_data)}

{web_search_context}

## Portfolio
{_format_portfolio(portfolio_data)}

## Data Sources Used
- Macro: Yahoo Finance (Nifty, Sensex, VIX, Crude, Gold, USD/INR, US indices)
- Technical: Yahoo Finance OHLCV → RSI, MACD, EMA, ATR, Volume analysis
- News: Moneycontrol, Economic Times headlines
- Web Search: DuckDuckGo (targeted at Moneycontrol, LiveMint, ET, NSE, RBI, SEBI, Reuters)

Provide your analysis now. Start with the date."""

    logger.info("🧠 Generating AI market intelligence...")
    response = await llm.generate(SYSTEM_PROMPT, user_message)
    return response


async def analyze_stock_detail(symbol: str, technical_data: dict, timeframe: str) -> str:
    """Get detailed AI analysis for a single stock."""
    from app.config import settings
    llm = get_llm()

    # For non-Gemini, enrich with stock-specific web search
    web_context = ""
    if settings.llm_provider != "gemini":
        from app.services.web_search import get_enriched_stock_context
        web_context = "\n" + get_enriched_stock_context(symbol)

    user_message = f"""Analyze this stock for a {timeframe} trade setup:

Symbol: {symbol}
Price: ₹{technical_data.get('price', 'N/A')}
RSI: {technical_data.get('rsi', 'N/A')}
MACD Bullish: {technical_data.get('macd_bullish', 'N/A')}
Above EMA20: {technical_data.get('above_ema20', 'N/A')}
Above EMA50: {technical_data.get('above_ema50', 'N/A')}
Volume Ratio: {technical_data.get('volume_ratio', 'N/A')}x
ATR: ₹{technical_data.get('atr', 'N/A')}
Momentum Score: {technical_data.get('momentum_score', 'N/A')}/5
{web_context}
Provide: Entry zone, Stop loss, Targets, Risk-reward, Confidence level, and Reasoning."""

    return await llm.generate(SYSTEM_PROMPT, user_message)


def _format_macro(data: dict) -> str:
    if not data:
        return "No macro data available."
    lines = []
    for key, val in data.items():
        lines.append(f"- {key}: {val.get('value', 'N/A')} ({val.get('change_pct', 0):+.2f}%)")
    return "\n".join(lines)


def _format_technicals(signals: list) -> str:
    if not signals:
        return "No strong momentum signals detected."
    lines = []
    for s in signals[:10]:
        lines.append(f"- {s['symbol']}: ₹{s['price']} | RSI:{s['rsi']} | Score:{s['momentum_score']}/5 | Signal:{s['signal']}")
    return "\n".join(lines)


def _format_news(data: dict) -> str:
    if not data:
        return "No news data available."
    headlines = data.get("moneycontrol", []) + data.get("economic_times", [])
    return "\n".join(f"- {h}" for h in headlines[:15])


def _format_portfolio(data: dict) -> str:
    if not data or data.get("status") == "no_holdings":
        return "Portfolio not connected."
    return f"Holdings: {data.get('num_holdings', 0)} | P&L: {data.get('overall_pnl_pct', 0):.2f}% | Alerts: {data.get('risk_alerts', [])}"
