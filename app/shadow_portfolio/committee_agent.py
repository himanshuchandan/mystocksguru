"""Investment Committee Agent - Reviews and approves/rejects trade recommendations.

Reuses the multi-agent debate architecture (Bull, Bear, Risk Arbiter, Moderator)
but focuses on portfolio-level decisions rather than single-stock analysis.
"""

from app.llm.provider import get_llm
from loguru import logger


COMMITTEE_SYSTEM_PROMPT_TEMPLATE = """You are the AI Investment Committee for a shadow portfolio managing ₹{capital:,.0f} of virtual capital.

Your role is to review trade recommendations and decide which ones to APPROVE or REJECT.

You are NOT a yes-man. You must:
1. Challenge every recommendation
2. Consider portfolio-level risk (concentration, correlation, sector exposure)
3. Reject weak ideas ruthlessly
4. Only approve HIGH CONVICTION trades
5. Consider current market regime
6. Check if existing positions conflict

You have strict rules:
- Max 5 open positions at any time
- Max 10% capital per trade (₹{max_per_trade:,.0f} max per position)
- Stop loss MANDATORY (max 4% from entry)
- Risk-reward minimum 1:2
- No re-entry for 2 days after a stop-loss hit on same stock
- No more than 2 stocks from same sector
- Avoid trading on budget/event days

For each candidate, output EXACTLY this format:

SYMBOL: [stock]
DECISION: APPROVE / REJECT / WAIT
CONFIDENCE: [1-100]
CAPITAL_ALLOCATE: [amount in ₹, 0 if rejected]
ENTRY_PRICE: [price]
STOP_LOSS: [price]
TARGET: [price]
QUANTITY: [number of shares]
REASONING: [2-3 sentences]
---
"""

EXIT_REVIEW_PROMPT = """You are the AI Investment Committee reviewing EXISTING positions for exit decisions.

For each open position, decide:
- HOLD: Keep the position, thesis intact
- EXIT: Close at market, book profit or cut loss
- TRAIL_SL: Move stop loss up to lock profits
- INCREASE: Add more (only if strong momentum and within limits)

Consider:
1. Has the original thesis played out or broken?
2. Is price near target? Book partial/full profit.
3. Is stop loss about to hit? Exit early if momentum reversed.
4. Has market regime changed?
5. Have holding days exceeded reasonable timeframe?

For each position, output EXACTLY:

SYMBOL: [stock]
CURRENT_PNL: [amount]
DECISION: HOLD / EXIT / TRAIL_SL / INCREASE
NEW_STOP_LOSS: [price, if trailing]
EXIT_REASON: [if exiting]
CONFIDENCE: [1-100]
---
"""


async def review_opportunities(
    candidates: list[dict],
    portfolio_state: dict,
    market_context: str,
) -> list[dict]:
    """
    Review candidate stocks and approve/reject for portfolio inclusion.
    
    Args:
        candidates: List of stock opportunities with scores and technical data
        portfolio_state: Current portfolio (cash, positions, etc.)
        market_context: Market regime, macro summary
    
    Returns:
        List of approved trades with entry/sl/target/quantity
    """
    llm = get_llm()
    
    if not candidates:
        return []

    # Build context
    context_lines = [
        "## PORTFOLIO STATE",
        f"Cash Available: ₹{portfolio_state.get('cash_balance', 0):,.0f}",
        f"Portfolio Value: ₹{portfolio_state.get('portfolio_value', 0):,.0f}",
        f"Open Positions: {portfolio_state.get('num_positions', 0)}/5",
        f"Today's P&L: ₹{portfolio_state.get('todays_pnl', 0):,.0f}",
        "",
        "## CURRENT POSITIONS",
    ]
    
    for pos in portfolio_state.get("positions", []):
        context_lines.append(
            f"- {pos['symbol']}: Entry ₹{pos['entry_price']}, "
            f"Current ₹{pos['current_price']}, "
            f"P&L: {pos['pnl_pct']:+.1f}%, "
            f"SL: ₹{pos['stop_loss']}, Target: ₹{pos['target_price']}"
        )
    
    if not portfolio_state.get("positions"):
        context_lines.append("- (No open positions)")
    
    context_lines.extend([
        "",
        "## MARKET CONTEXT",
        market_context,
        "",
        "## CANDIDATES FOR REVIEW",
    ])
    
    for i, c in enumerate(candidates[:5], 1):
        context_lines.append(
            f"\n### Candidate {i}: {c['symbol']}\n"
            f"- Price: ₹{c.get('price', 'N/A')}\n"
            f"- Momentum Score: {c.get('momentum_score', 'N/A')}/5\n"
            f"- RSI: {c.get('rsi', 'N/A')}\n"
            f"- MACD: {'Bullish' if c.get('macd_bullish') else 'Bearish'}\n"
            f"- Above EMA20: {c.get('above_ema20', 'N/A')}\n"
            f"- Above EMA50: {c.get('above_ema50', 'N/A')}\n"
            f"- Volume Ratio: {c.get('volume_ratio', 'N/A')}x\n"
            f"- Signal: {c.get('signal', 'N/A')}\n"
            f"- Change: {c.get('change_pct', 0):+.2f}%"
        )
    
    context = "\n".join(context_lines)
    
    logger.info(f"🏛️ Investment Committee reviewing {len(candidates)} candidates...")
    capital = portfolio_state.get('portfolio_value', 20000)
    system_prompt = COMMITTEE_SYSTEM_PROMPT_TEMPLATE.format(
        capital=capital,
        max_per_trade=capital * 0.10,
    )
    response = await llm.generate(system_prompt, context, temperature=0.2)
    
    # Parse response
    approved = _parse_committee_response(response)
    logger.info(f"🏛️ Committee approved {len(approved)}/{len(candidates)} trades")
    
    return approved


async def review_positions(
    positions: list[dict],
    market_context: str,
) -> list[dict]:
    """
    Review existing positions for exit/hold/trail decisions.
    
    Returns:
        List of position decisions
    """
    llm = get_llm()
    
    if not positions:
        return []
    
    context_lines = [
        "## MARKET CONTEXT",
        market_context,
        "",
        "## POSITIONS TO REVIEW",
    ]
    
    for pos in positions:
        pnl_pct = ((pos['current_price'] - pos['entry_price']) / pos['entry_price']) * 100
        context_lines.append(
            f"\n### {pos['symbol']}\n"
            f"- Entry: ₹{pos['entry_price']} on {pos.get('entry_time', 'N/A')}\n"
            f"- Current: ₹{pos['current_price']}\n"
            f"- P&L: {pnl_pct:+.2f}% (₹{pos.get('unrealized_pnl', 0):+,.0f})\n"
            f"- Stop Loss: ₹{pos['stop_loss']}\n"
            f"- Target: ₹{pos['target_price']}\n"
            f"- Holding Days: {pos.get('holding_days', 0)}\n"
            f"- Entry Reason: {pos.get('entry_reason', 'N/A')}"
        )
    
    context = "\n".join(context_lines)
    
    logger.info(f"🏛️ Committee reviewing {len(positions)} open positions...")
    response = await llm.generate(EXIT_REVIEW_PROMPT, context, temperature=0.2)
    
    decisions = _parse_exit_response(response)
    logger.info(f"🏛️ Exit decisions: {[d.get('decision') for d in decisions]}")
    
    return decisions


def _parse_committee_response(response: str) -> list[dict]:
    """Parse the committee's structured response into trade decisions."""
    approved = []
    blocks = response.split("---")
    
    for block in blocks:
        block = block.strip()
        if not block or "REJECT" in block:
            continue
        if "APPROVE" not in block and "WAIT" not in block:
            continue
        if "APPROVE" not in block:
            continue
            
        trade = {}
        for line in block.split("\n"):
            line = line.strip()
            if line.startswith("SYMBOL:"):
                trade["symbol"] = line.split(":", 1)[1].strip().replace(".NS", "")
            elif line.startswith("DECISION:"):
                trade["decision"] = line.split(":", 1)[1].strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    trade["confidence"] = int(line.split(":", 1)[1].strip())
                except ValueError:
                    trade["confidence"] = 50
            elif line.startswith("CAPITAL_ALLOCATE:"):
                val = line.split(":", 1)[1].strip().replace("₹", "").replace(",", "")
                try:
                    trade["capital_allocate"] = float(val)
                except ValueError:
                    trade["capital_allocate"] = 0
            elif line.startswith("ENTRY_PRICE:"):
                val = line.split(":", 1)[1].strip().replace("₹", "").replace(",", "")
                try:
                    trade["entry_price"] = float(val)
                except ValueError:
                    pass
            elif line.startswith("STOP_LOSS:"):
                val = line.split(":", 1)[1].strip().replace("₹", "").replace(",", "")
                try:
                    trade["stop_loss"] = float(val)
                except ValueError:
                    pass
            elif line.startswith("TARGET:"):
                val = line.split(":", 1)[1].strip().replace("₹", "").replace(",", "")
                try:
                    trade["target"] = float(val)
                except ValueError:
                    pass
            elif line.startswith("QUANTITY:"):
                try:
                    trade["quantity"] = int(line.split(":", 1)[1].strip())
                except ValueError:
                    trade["quantity"] = 0
            elif line.startswith("REASONING:"):
                trade["reasoning"] = line.split(":", 1)[1].strip()
        
        if trade.get("decision") == "APPROVE" and trade.get("symbol") and trade.get("entry_price"):
            approved.append(trade)
    
    return approved


def _parse_exit_response(response: str) -> list[dict]:
    """Parse exit review response."""
    decisions = []
    blocks = response.split("---")
    
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        
        decision = {}
        for line in block.split("\n"):
            line = line.strip()
            if line.startswith("SYMBOL:"):
                decision["symbol"] = line.split(":", 1)[1].strip().replace(".NS", "")
            elif line.startswith("DECISION:"):
                decision["decision"] = line.split(":", 1)[1].strip()
            elif line.startswith("NEW_STOP_LOSS:"):
                val = line.split(":", 1)[1].strip().replace("₹", "").replace(",", "")
                try:
                    decision["new_stop_loss"] = float(val)
                except ValueError:
                    pass
            elif line.startswith("EXIT_REASON:"):
                decision["exit_reason"] = line.split(":", 1)[1].strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    decision["confidence"] = int(line.split(":", 1)[1].strip())
                except ValueError:
                    decision["confidence"] = 50
        
        if decision.get("symbol"):
            decisions.append(decision)
    
    return decisions
