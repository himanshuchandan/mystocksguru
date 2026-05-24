"""Debate Agent - Multi-agent adversarial discussion for trade decisions.

Architecture:
  1. Bull Agent - argues FOR the trade (finds reasons to buy)
  2. Bear Agent - argues AGAINST the trade (finds risks, red flags)
  3. Risk Arbiter - evaluates if risk is acceptable
  4. Moderator - synthesizes debate, gives final verdict with confidence

This ensures no trade is recommended without rigorous opposing analysis.
"""

from app.llm.provider import get_llm
from loguru import logger


BULL_PROMPT = """You are a BULLISH stock market analyst. Your job is to make the STRONGEST possible case FOR taking this trade.

Find every reason to be optimistic:
- Technical momentum signals
- Macro tailwinds
- Sector strength
- Volume confirmation
- Historical patterns
- Institutional interest

Be specific. Use the data provided. Give concrete entry, target, and reasoning.
But be honest — don't fabricate data. Only argue based on what's given.

Output format:
🟢 BULL CASE
- Key arguments (numbered)
- Entry zone
- Targets
- Catalysts
- Confidence: HIGH/MEDIUM/LOW"""

BEAR_PROMPT = """You are a BEARISH stock market analyst and devil's advocate. Your job is to make the STRONGEST possible case AGAINST this trade.

Find every reason to be cautious:
- Overbought signals
- Macro headwinds
- Sector weakness
- Volume divergence
- Resistance levels
- Risk of drawdown
- What could go wrong
- Historical failures in similar setups

Be ruthless. Challenge every bullish assumption. Think about what retail traders miss.
But be honest — don't fabricate data. Only argue based on what's given.

Output format:
🔴 BEAR CASE
- Key arguments (numbered)
- Risk factors
- Invalidation scenarios
- What could go wrong
- Confidence in bearish case: HIGH/MEDIUM/LOW"""

RISK_ARBITER_PROMPT = """You are a RISK MANAGER. You've heard both bull and bear cases for a trade.

Your job is NOT to pick a side. Your job is to:
1. Assess if the RISK is acceptable regardless of direction
2. Calculate if position sizing makes sense
3. Determine if stop loss is logical
4. Check if risk-reward ratio is favorable (minimum 1:2)
5. Flag if this trade violates any risk management rules

Rules you enforce:
- Never risk more than 2% of capital per trade
- Risk-reward must be at least 1:2
- Don't trade against the primary trend
- Avoid trades before major events (earnings, policy)
- If both bull and bear have strong cases → STAY OUT

Output format:
⚖️ RISK VERDICT
- Risk acceptable: YES/NO
- Position size recommendation
- Stop loss validation
- Risk-reward assessment
- Final risk score: 1-10 (10 = extremely risky)"""

MODERATOR_PROMPT = """You are the FINAL DECISION MAKER — a senior portfolio manager who has heard:
1. The Bull Case (reasons to buy)
2. The Bear Case (reasons to avoid)
3. The Risk Arbiter's assessment

Your job is to synthesize everything and give a FINAL VERDICT.

You must be:
- Balanced
- Honest about uncertainty
- Clear about action items
- Specific about conditions

Output format:
📋 FINAL VERDICT

🎯 Decision: BUY / AVOID / WAIT FOR BETTER ENTRY / REDUCE POSITION
📊 Confidence: HIGH / MEDIUM / LOW
⏱️ Timeframe: Intraday / Swing / Positional / Long-term

📝 Reasoning:
(2-3 sentences explaining the decision considering both sides)

✅ Action Plan (if BUY):
- Entry zone
- Stop loss
- Target 1
- Target 2
- Position size suggestion
- Review trigger (when to reassess)

⚠️ Conditions to Watch:
- What would change this view
- Key levels to monitor

🚫 What NOT to do:
- Common mistakes to avoid with this trade"""


async def run_debate(
    stock_symbol: str,
    technical_data: dict,
    macro_data: dict = None,
    news_data: dict = None,
    portfolio_context: str = None,
) -> dict:
    """Run a multi-agent debate on a trade idea."""
    llm = get_llm()

    # Build context that all agents see
    context = _build_shared_context(stock_symbol, technical_data, macro_data, news_data, portfolio_context)

    logger.info(f"🗣️ Starting debate for {stock_symbol}...")

    # Step 1: Bull makes the case
    logger.info("  🟢 Bull Agent arguing...")
    bull_case = await llm.generate(BULL_PROMPT, context, temperature=0.4)

    # Step 2: Bear counters (sees bull's argument too)
    logger.info("  🔴 Bear Agent countering...")
    bear_context = f"{context}\n\n--- BULL'S ARGUMENT (counter this) ---\n{bull_case}"
    bear_case = await llm.generate(BEAR_PROMPT, bear_context, temperature=0.4)

    # Step 3: Risk Arbiter evaluates both
    logger.info("  ⚖️ Risk Arbiter evaluating...")
    risk_context = f"{context}\n\n--- BULL CASE ---\n{bull_case}\n\n--- BEAR CASE ---\n{bear_case}"
    risk_verdict = await llm.generate(RISK_ARBITER_PROMPT, risk_context, temperature=0.2)

    # Step 4: Moderator gives final verdict
    logger.info("  📋 Moderator deciding...")
    moderator_context = (
        f"{context}\n\n"
        f"--- BULL CASE ---\n{bull_case}\n\n"
        f"--- BEAR CASE ---\n{bear_case}\n\n"
        f"--- RISK ASSESSMENT ---\n{risk_verdict}"
    )
    final_verdict = await llm.generate(MODERATOR_PROMPT, moderator_context, temperature=0.2)

    logger.info(f"✅ Debate complete for {stock_symbol}")

    return {
        "symbol": stock_symbol,
        "bull_case": bull_case,
        "bear_case": bear_case,
        "risk_verdict": risk_verdict,
        "final_verdict": final_verdict,
        "full_debate": (
            f"{'='*50}\n"
            f"🗣️ MULTI-AGENT DEBATE: {stock_symbol}\n"
            f"{'='*50}\n\n"
            f"{bull_case}\n\n"
            f"{'─'*50}\n\n"
            f"{bear_case}\n\n"
            f"{'─'*50}\n\n"
            f"{risk_verdict}\n\n"
            f"{'═'*50}\n\n"
            f"{final_verdict}"
        ),
    }


def _build_shared_context(
    symbol: str,
    technical: dict,
    macro: dict = None,
    news: dict = None,
    portfolio: str = None,
) -> str:
    """Build the shared context all agents see."""
    lines = [f"## Stock Under Analysis: {symbol}\n"]

    # Technical data
    lines.append("### Technical Indicators:")
    lines.append(f"- Price: ₹{technical.get('price', 'N/A')}")
    lines.append(f"- Change: {technical.get('change_pct', 0)}%")
    lines.append(f"- RSI(14): {technical.get('rsi', 'N/A')}")
    lines.append(f"- MACD Bullish: {technical.get('macd_bullish', 'N/A')}")
    lines.append(f"- Above EMA20: {technical.get('above_ema20', 'N/A')}")
    lines.append(f"- Above EMA50: {technical.get('above_ema50', 'N/A')}")
    lines.append(f"- Volume Ratio (vs 20d avg): {technical.get('volume_ratio', 'N/A')}x")
    lines.append(f"- ATR(14): ₹{technical.get('atr', 'N/A')}")
    lines.append(f"- Momentum Score: {technical.get('momentum_score', 'N/A')}/5")
    lines.append(f"- Signal: {technical.get('signal', 'N/A')}")

    # Macro context
    if macro:
        lines.append("\n### Macro Context:")
        for key, val in list(macro.items())[:8]:
            lines.append(f"- {key.replace('_', ' ').title()}: {val.get('value', 'N/A')} ({val.get('change_pct', 0):+.2f}%)")

    # News
    if news:
        headlines = news.get("moneycontrol", [])[:5] + news.get("economic_times", [])[:5]
        if headlines:
            lines.append("\n### Recent News:")
            for h in headlines[:8]:
                lines.append(f"- {h}")

    # Portfolio context
    if portfolio:
        lines.append(f"\n### Portfolio Context:\n{portfolio}")

    return "\n".join(lines)
