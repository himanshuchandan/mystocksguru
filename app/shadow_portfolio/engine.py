"""Shadow Portfolio Engine - Core trading logic.

Handles:
- Portfolio initialization
- Position opening/closing
- Price updates
- Stop loss/target monitoring
- Performance calculations
- Daily snapshots
"""

from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.shadow_portfolio.models import (
    Portfolio, Position, Trade, AnalysisLog, DailySnapshot, CycleLog,
    get_session_factory, init_db,
)
import json
from app.shadow_portfolio.committee_agent import review_opportunities, review_positions
from app.agents.technical_agent import scan_market, analyze_stock_technical
from app.agents.macro_agent import get_macro_snapshot, get_market_regime
from app.agents.news_agent import get_news_summary


# Configuration
MAX_POSITIONS = 5
MAX_POSITION_PCT = 0.10  # 10% per position
MAX_STOP_LOSS_PCT = 0.04  # 4% max stop loss
MIN_RISK_REWARD = 2.0  # Minimum 1:2 risk-reward
COOLING_PERIOD_DAYS = 2  # Days to wait after stop-loss


async def initialize_portfolio(capital: float = 20000.0) -> dict:
    """Initialize or get the shadow portfolio."""
    await init_db()
    factory = get_session_factory()
    
    async with factory() as session:
        result = await session.execute(select(Portfolio).limit(1))
        portfolio = result.scalar_one_or_none()
        
        if portfolio is None:
            # Get Nifty starting value for benchmark
            nifty_start = await _get_nifty_value()
            
            portfolio = Portfolio(
                initial_capital=capital,
                cash_balance=capital,
                portfolio_value=capital,
                peak_value=capital,
                benchmark_start_value=nifty_start,
            )
            session.add(portfolio)
            await session.commit()
            await session.refresh(portfolio)
            logger.info(f"🏦 Shadow Portfolio initialized with ₹{capital:,.0f}")
        
        return _portfolio_to_dict(portfolio)


async def run_shadow_cycle():
    """
    Main cycle - called every 2 hours during market hours.
    
    1. Update prices for open positions
    2. Check stop losses and targets
    3. Review existing positions (exit decisions)
    4. Scan for new opportunities
    5. Run Investment Committee
    6. Execute approved trades (virtual)
    7. Log everything
    """
    await init_db()
    factory = get_session_factory()
    
    async with factory() as session:
        # Get portfolio
        result = await session.execute(select(Portfolio).limit(1))
        portfolio = result.scalar_one_or_none()
        
        if portfolio is None:
            await initialize_portfolio()
            result = await session.execute(select(Portfolio).limit(1))
            portfolio = result.scalar_one_or_none()
        
        logger.info("=" * 60)
        logger.info("🤖 AI SHADOW PORTFOLIO - Running Cycle")
        logger.info(f"💰 Portfolio: ₹{portfolio.portfolio_value:,.0f} | Cash: ₹{portfolio.cash_balance:,.0f}")
        logger.info("=" * 60)
        
        # Step 1: Update all open position prices
        open_positions = await _get_open_positions(session)
        await _update_position_prices(session, open_positions)
        
        # Step 2: Check stop losses and targets (auto-execute)
        await _check_sl_target(session, portfolio, open_positions)
        
        # Refresh positions after SL/Target exits
        open_positions = await _get_open_positions(session)
        
        # Step 3: Get market context
        macro = get_macro_snapshot()
        regime = get_market_regime(macro)
        news = await get_news_summary()
        
        market_context = (
            f"Regime: {regime}\n"
            f"Nifty: {macro.get('nifty_50', {}).get('value', 'N/A')} "
            f"({macro.get('nifty_50', {}).get('change_pct', 0):+.2f}%)\n"
            f"VIX: {macro.get('india_vix', {}).get('value', 'N/A')}"
        )
        
        # Step 4: Review existing positions
        if open_positions:
            pos_data = [_position_to_dict(p) for p in open_positions]
            exit_decisions = await review_positions(pos_data, market_context)
            await _execute_exit_decisions(session, portfolio, open_positions, exit_decisions)
        
        # Refresh after exits
        open_positions = await _get_open_positions(session)
        
        # Track cycle data
        cycle_candidates = []
        cycle_approved = []
        cycle_rejected = []
        cycle_exit_decisions_log = []
        portfolio_value_before = portfolio.portfolio_value
        
        # Step 5: If room for new positions, scan opportunities
        num_open = len(open_positions)
        if num_open < MAX_POSITIONS and portfolio.cash_balance > 1000:
            logger.info(f"🔍 Scanning for opportunities (slots: {MAX_POSITIONS - num_open})...")
            
            # Get momentum stocks
            momentum_stocks = scan_market()
            momentum_stocks = sorted(
                momentum_stocks,
                key=lambda x: x.get("momentum_score", 0),
                reverse=True,
            )
            
            # Filter out stocks we already hold or recently stopped out of
            held_symbols = {p.symbol for p in open_positions}
            cooled_symbols = await _get_cooling_symbols(session)
            candidates = [
                s for s in momentum_stocks
                if s["symbol"].replace(".NS", "") not in held_symbols
                and s["symbol"].replace(".NS", "") not in cooled_symbols
                and s.get("momentum_score", 0) >= 3
            ][:5]
            
            # Track all candidates considered
            cycle_candidates = [
                {"symbol": s["symbol"].replace(".NS", ""), "momentum_score": s.get("momentum_score", 0), "price": s.get("price", 0)}
                for s in candidates
            ]
            
            if candidates:
                # Step 6: Investment Committee reviews
                portfolio_state = {
                    "cash_balance": portfolio.cash_balance,
                    "portfolio_value": portfolio.portfolio_value,
                    "num_positions": num_open,
                    "todays_pnl": sum(p.unrealized_pnl for p in open_positions),
                    "positions": [_position_to_dict(p) for p in open_positions],
                }
                
                approved_trades = await review_opportunities(
                    candidates, portfolio_state, market_context
                )
                
                # Track approved/rejected
                approved_symbols = {t["symbol"].replace(".NS", "") for t in approved_trades}
                cycle_approved = [
                    {"symbol": t["symbol"].replace(".NS", ""), "entry_price": t.get("entry_price"), "stop_loss": t.get("stop_loss"), "target": t.get("target"), "reasoning": t.get("reasoning", "")}
                    for t in approved_trades
                ]
                cycle_rejected = [
                    {"symbol": c["symbol"].replace(".NS", ""), "momentum_score": c.get("momentum_score", 0), "reason": "Rejected by Investment Committee"}
                    for c in candidates
                    if c["symbol"].replace(".NS", "") not in approved_symbols
                ]
                
                # Step 7: Execute approved trades
                for trade in approved_trades:
                    await _execute_virtual_buy(session, portfolio, trade, market_context)
            else:
                logger.info("📭 No suitable candidates found")
        else:
            logger.info(f"⏸️ Portfolio full ({num_open}/{MAX_POSITIONS}) or low cash")
        
        # Update portfolio value
        await _recalculate_portfolio(session, portfolio)
        await session.commit()
        
        # Get cycle number
        result2 = await session.execute(select(func.count(CycleLog.id)))
        cycle_number = (result2.scalar() or 0) + 1
        
        # Save cycle log
        open_positions_final = await _get_open_positions(session)
        cycle_log = CycleLog(
            cycle_number=cycle_number,
            market_context=market_context,
            candidates_considered=json.dumps(cycle_candidates),
            candidates_approved=json.dumps(cycle_approved),
            candidates_rejected=json.dumps(cycle_rejected),
            exit_decisions=json.dumps(cycle_exit_decisions_log),
            portfolio_value_before=portfolio_value_before,
            portfolio_value_after=portfolio.portfolio_value,
            num_positions_after=len(open_positions_final),
            summary=f"Considered {len(cycle_candidates)}, Approved {len(cycle_approved)}, Rejected {len(cycle_rejected)}",
        )
        session.add(cycle_log)
        await session.commit()
        
        # Send Telegram notification
        await _send_cycle_notification(cycle_number, cycle_candidates, cycle_approved, cycle_rejected, portfolio)
        
        logger.info(f"✅ Cycle #{cycle_number} complete. Portfolio: ₹{portfolio.portfolio_value:,.0f}")
        logger.info("=" * 60)
        
        return await get_portfolio_summary()


async def get_portfolio_summary() -> dict:
    """Get complete portfolio summary for dashboard."""
    await init_db()
    factory = get_session_factory()
    
    async with factory() as session:
        result = await session.execute(select(Portfolio).limit(1))
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            return {"status": "not_initialized", "message": "Run a shadow cycle first."}
        
        # Open positions
        positions = await _get_open_positions(session)
        pos_list = [_position_to_dict(p) for p in positions]
        
        # Recent trades
        result = await session.execute(
            select(Trade).order_by(Trade.trade_date.desc()).limit(20)
        )
        trades = [_trade_to_dict(t) for t in result.scalars().all()]
        
        # Recent analysis logs
        result = await session.execute(
            select(AnalysisLog).order_by(AnalysisLog.analysis_time.desc()).limit(10)
        )
        logs = [_log_to_dict(l) for l in result.scalars().all()]
        
        # Performance metrics
        total_return_pct = ((portfolio.portfolio_value - portfolio.initial_capital) / portfolio.initial_capital) * 100
        win_rate = (portfolio.winning_trades / portfolio.total_trades * 100) if portfolio.total_trades > 0 else 0
        
        # Benchmark comparison
        nifty_return_pct = 0
        if portfolio.benchmark_start_value:
            current_nifty = await _get_nifty_value()
            if current_nifty and portfolio.benchmark_start_value > 0:
                nifty_return_pct = ((current_nifty - portfolio.benchmark_start_value) / portfolio.benchmark_start_value) * 100
        
        # Daily snapshots for chart
        result = await session.execute(
            select(DailySnapshot).order_by(DailySnapshot.date.desc()).limit(60)
        )
        snapshots = result.scalars().all()
        chart_data = [
            {
                "date": s.date.strftime("%Y-%m-%d"),
                "portfolio_value": s.portfolio_value,
                "nifty_value": s.nifty_value,
                "daily_return": s.daily_return_pct,
                "cumulative_return": s.cumulative_return_pct,
                "nifty_cumulative": s.nifty_cumulative_return_pct,
            }
            for s in reversed(list(snapshots))
        ]
        
        return {
            "status": "active",
            "portfolio": {
                "initial_capital": portfolio.initial_capital,
                "current_value": portfolio.portfolio_value,
                "cash_balance": portfolio.cash_balance,
                "invested": portfolio.portfolio_value - portfolio.cash_balance,
                "total_return_pct": round(total_return_pct, 2),
                "total_realized_pnl": portfolio.total_realized_pnl,
                "unrealized_pnl": sum(p.unrealized_pnl for p in positions),
                "max_drawdown_pct": portfolio.max_drawdown_pct,
                "peak_value": portfolio.peak_value,
            },
            "performance": {
                "total_trades": portfolio.total_trades,
                "winning_trades": portfolio.winning_trades,
                "losing_trades": portfolio.losing_trades,
                "win_rate": round(win_rate, 1),
                "total_return_pct": round(total_return_pct, 2),
                "nifty_return_pct": round(nifty_return_pct, 2),
                "alpha": round(total_return_pct - nifty_return_pct, 2),
                "max_drawdown_pct": portfolio.max_drawdown_pct,
            },
            "positions": pos_list,
            "recent_trades": trades,
            "ai_decisions": logs,
            "chart_data": chart_data,
            "created_at": portfolio.created_at.isoformat() if portfolio.created_at else None,
        }


async def take_daily_snapshot():
    """Record end-of-day portfolio snapshot for performance tracking."""
    await init_db()
    factory = get_session_factory()
    
    async with factory() as session:
        result = await session.execute(select(Portfolio).limit(1))
        portfolio = result.scalar_one_or_none()
        if not portfolio:
            return
        
        positions = await _get_open_positions(session)
        nifty = await _get_nifty_value()
        
        # Check if we already have today's snapshot
        today = datetime.utcnow().date()
        result = await session.execute(
            select(DailySnapshot).where(
                func.date(DailySnapshot.date) == today
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return  # Already snapshotted today
        
        # Calculate returns
        invested = sum(p.quantity * (p.current_price or p.entry_price) for p in positions)
        cumulative_return = ((portfolio.portfolio_value - portfolio.initial_capital) / portfolio.initial_capital) * 100
        
        nifty_cumulative = 0
        if portfolio.benchmark_start_value and nifty:
            nifty_cumulative = ((nifty - portfolio.benchmark_start_value) / portfolio.benchmark_start_value) * 100
        
        # Get yesterday's value for daily return
        result = await session.execute(
            select(DailySnapshot).order_by(DailySnapshot.date.desc()).limit(1)
        )
        prev = result.scalar_one_or_none()
        daily_return = 0
        if prev and prev.portfolio_value > 0:
            daily_return = ((portfolio.portfolio_value - prev.portfolio_value) / prev.portfolio_value) * 100
        
        snapshot = DailySnapshot(
            date=datetime.utcnow(),
            portfolio_value=portfolio.portfolio_value,
            cash_balance=portfolio.cash_balance,
            invested_value=invested,
            num_positions=len(positions),
            nifty_value=nifty,
            daily_return_pct=round(daily_return, 2),
            cumulative_return_pct=round(cumulative_return, 2),
            nifty_cumulative_return_pct=round(nifty_cumulative, 2),
        )
        session.add(snapshot)
        await session.commit()
        logger.info(f"📸 Daily snapshot: ₹{portfolio.portfolio_value:,.0f} ({cumulative_return:+.2f}%)")


async def reset_portfolio(capital: float = 20000.0) -> dict:
    """Reset the entire shadow portfolio (for testing)."""
    await init_db()
    factory = get_session_factory()
    
    async with factory() as session:
        # Delete all data
        await session.execute(select(Portfolio))  # just to ensure table exists
        from sqlalchemy import delete
        await session.execute(delete(Portfolio))
        await session.execute(delete(Position))
        await session.execute(delete(Trade))
        await session.execute(delete(AnalysisLog))
        await session.execute(delete(DailySnapshot))
        await session.execute(delete(CycleLog))
        await session.commit()
    
    return await initialize_portfolio(capital)


# ─── Internal helpers ─────────────────────────────────────────────────────────

async def _get_open_positions(session: AsyncSession) -> list[Position]:
    result = await session.execute(
        select(Position).where(Position.status == "OPEN")
    )
    return list(result.scalars().all())


async def _update_position_prices(session: AsyncSession, positions: list[Position]):
    """Update current prices for all open positions."""
    for pos in positions:
        try:
            import yfinance as yf
            symbol = pos.symbol if ".NS" in pos.symbol else f"{pos.symbol}.NS"
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                current = round(hist["Close"].iloc[-1], 2)
                pos.current_price = current
                pos.unrealized_pnl = round((current - pos.entry_price) * pos.quantity, 2)
                pos.holding_days = (datetime.utcnow() - pos.entry_time).days
        except Exception as e:
            logger.warning(f"Failed to update price for {pos.symbol}: {e}")


async def _check_sl_target(session: AsyncSession, portfolio: Portfolio, positions: list[Position]):
    """Auto-execute stop losses and targets."""
    for pos in positions:
        if pos.current_price is None:
            continue
        
        # Stop loss hit
        if pos.current_price <= pos.stop_loss:
            logger.info(f"🛑 STOP LOSS HIT: {pos.symbol} at ₹{pos.current_price} (SL: ₹{pos.stop_loss})")
            await _close_position(session, portfolio, pos, "STOPPED_OUT", f"Stop loss hit at ₹{pos.current_price}")
        
        # Target hit
        elif pos.current_price >= pos.target_price:
            logger.info(f"🎯 TARGET HIT: {pos.symbol} at ₹{pos.current_price} (Target: ₹{pos.target_price})")
            await _close_position(session, portfolio, pos, "CLOSED", f"Target reached at ₹{pos.current_price}")


async def _execute_exit_decisions(
    session: AsyncSession, portfolio: Portfolio,
    positions: list[Position], decisions: list[dict]
):
    """Execute committee exit decisions."""
    decision_map = {d["symbol"]: d for d in decisions}
    
    for pos in positions:
        symbol = pos.symbol.replace(".NS", "")
        decision = decision_map.get(symbol)
        if not decision:
            continue
        
        if decision.get("decision") == "EXIT":
            reason = decision.get("exit_reason", "Committee decided to exit")
            await _close_position(session, portfolio, pos, "CLOSED", reason)
        
        elif decision.get("decision") == "TRAIL_SL":
            new_sl = decision.get("new_stop_loss")
            if new_sl and new_sl > pos.stop_loss:
                pos.stop_loss = new_sl
                logger.info(f"📈 Trailing SL for {pos.symbol}: ₹{new_sl}")


async def _close_position(session: AsyncSession, portfolio: Portfolio, pos: Position, status: str, reason: str):
    """Close a position and record the trade."""
    sell_price = pos.current_price or pos.entry_price
    pnl = round((sell_price - pos.entry_price) * pos.quantity, 2)
    pnl_pct = round(((sell_price - pos.entry_price) / pos.entry_price) * 100, 2)
    
    # Update position
    pos.status = status
    pos.realized_pnl = pnl
    pos.exit_time = datetime.utcnow()
    pos.exit_reason = reason
    
    # Record trade
    trade = Trade(
        symbol=pos.symbol,
        direction="BUY",
        quantity=pos.quantity,
        buy_price=pos.entry_price,
        sell_price=sell_price,
        profit_loss=pnl,
        profit_loss_pct=pnl_pct,
        capital_used=pos.capital_allocated,
        confidence_score=pos.confidence_score,
        reason=pos.entry_reason,
        exit_reason=reason,
        holding_days=pos.holding_days,
        trade_date=pos.entry_time,
        exit_date=datetime.utcnow(),
    )
    session.add(trade)
    
    # Update portfolio
    portfolio.cash_balance += pos.capital_allocated + pnl
    portfolio.total_realized_pnl += pnl
    portfolio.total_trades += 1
    if pnl > 0:
        portfolio.winning_trades += 1
    else:
        portfolio.losing_trades += 1
    
    logger.info(f"{'✅' if pnl > 0 else '❌'} Closed {pos.symbol}: P&L ₹{pnl:+,.0f} ({pnl_pct:+.1f}%) | {reason}")


async def _execute_virtual_buy(session: AsyncSession, portfolio: Portfolio, trade: dict, market_context: str):
    """Execute a virtual buy trade."""
    symbol = trade["symbol"].replace(".NS", "")
    entry_price = trade.get("entry_price", 0)
    stop_loss = trade.get("stop_loss", 0)
    target = trade.get("target", 0)
    quantity = trade.get("quantity", 0)
    confidence = trade.get("confidence", 0)
    reasoning = trade.get("reasoning", "")
    capital = trade.get("capital_allocate", entry_price * quantity)
    
    # Validation
    if entry_price <= 0 or quantity <= 0:
        logger.warning(f"⚠️ Invalid trade params for {symbol}, skipping")
        return
    
    # Check capital
    required = entry_price * quantity
    if required > portfolio.cash_balance:
        logger.warning(f"⚠️ Insufficient cash for {symbol}: need ₹{required:,.0f}, have ₹{portfolio.cash_balance:,.0f}")
        return
    
    # Check max position size
    max_allowed = portfolio.portfolio_value * MAX_POSITION_PCT
    if required > max_allowed * 1.5:  # Allow slight flexibility
        logger.warning(f"⚠️ Position too large for {symbol}: ₹{required:,.0f} > max ₹{max_allowed:,.0f}")
        return
    
    # Create position
    position = Position(
        symbol=symbol,
        quantity=quantity,
        entry_price=entry_price,
        current_price=entry_price,
        stop_loss=stop_loss,
        target_price=target,
        capital_allocated=required,
        confidence_score=confidence,
        entry_reason=reasoning,
        entry_time=datetime.utcnow(),
    )
    session.add(position)
    
    # Deduct cash
    portfolio.cash_balance -= required
    
    # Log the decision
    log = AnalysisLog(
        symbol=symbol,
        decision="BUY",
        confidence=confidence,
        reasoning=reasoning,
        market_context=market_context,
        committee_verdict=f"APPROVED: {quantity} @ ₹{entry_price}, SL ₹{stop_loss}, Target ₹{target}",
    )
    session.add(log)
    
    logger.info(
        f"🛒 VIRTUAL BUY: {symbol} | {quantity} shares @ ₹{entry_price} | "
        f"SL: ₹{stop_loss} | Target: ₹{target} | Confidence: {confidence}%"
    )


async def _recalculate_portfolio(session: AsyncSession, portfolio: Portfolio):
    """Recalculate total portfolio value."""
    positions = await _get_open_positions(session)
    invested_value = sum(
        p.quantity * (p.current_price or p.entry_price) for p in positions
    )
    portfolio.portfolio_value = round(portfolio.cash_balance + invested_value, 2)
    
    # Update peak and drawdown
    if portfolio.portfolio_value > portfolio.peak_value:
        portfolio.peak_value = portfolio.portfolio_value
    
    if portfolio.peak_value > 0:
        drawdown = ((portfolio.peak_value - portfolio.portfolio_value) / portfolio.peak_value) * 100
        if drawdown > portfolio.max_drawdown_pct:
            portfolio.max_drawdown_pct = round(drawdown, 2)
    
    portfolio.updated_at = datetime.utcnow()


async def _get_cooling_symbols(session: AsyncSession) -> set:
    """Get symbols that recently hit stop loss (cooling period)."""
    cutoff = datetime.utcnow() - timedelta(days=COOLING_PERIOD_DAYS)
    result = await session.execute(
        select(Position.symbol).where(
            Position.status == "STOPPED_OUT",
            Position.exit_time >= cutoff,
        )
    )
    return {row[0].replace(".NS", "") for row in result.all()}


async def _get_nifty_value() -> float | None:
    """Get current Nifty 50 value."""
    try:
        import yfinance as yf
        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(period="1d")
        if not hist.empty:
            return round(hist["Close"].iloc[-1], 2)
    except Exception as e:
        logger.warning(f"Failed to get Nifty value: {e}")
    return None


def _portfolio_to_dict(p: Portfolio) -> dict:
    return {
        "initial_capital": p.initial_capital,
        "cash_balance": p.cash_balance,
        "portfolio_value": p.portfolio_value,
        "total_realized_pnl": p.total_realized_pnl,
        "total_trades": p.total_trades,
        "winning_trades": p.winning_trades,
        "losing_trades": p.losing_trades,
        "max_drawdown_pct": p.max_drawdown_pct,
        "peak_value": p.peak_value,
    }


def _position_to_dict(p: Position) -> dict:
    pnl_pct = 0
    if p.entry_price and p.current_price:
        pnl_pct = round(((p.current_price - p.entry_price) / p.entry_price) * 100, 2)
    return {
        "id": p.id,
        "symbol": p.symbol,
        "quantity": p.quantity,
        "entry_price": p.entry_price,
        "current_price": p.current_price or p.entry_price,
        "stop_loss": p.stop_loss,
        "target_price": p.target_price,
        "unrealized_pnl": p.unrealized_pnl,
        "pnl_pct": pnl_pct,
        "confidence_score": p.confidence_score,
        "entry_reason": p.entry_reason,
        "entry_time": p.entry_time.isoformat() if p.entry_time else None,
        "holding_days": p.holding_days,
    }


def _trade_to_dict(t: Trade) -> dict:
    return {
        "symbol": t.symbol,
        "quantity": t.quantity,
        "buy_price": t.buy_price,
        "sell_price": t.sell_price,
        "profit_loss": t.profit_loss,
        "profit_loss_pct": t.profit_loss_pct,
        "confidence_score": t.confidence_score,
        "reason": t.reason,
        "exit_reason": t.exit_reason,
        "holding_days": t.holding_days,
        "trade_date": t.trade_date.isoformat() if t.trade_date else None,
        "exit_date": t.exit_date.isoformat() if t.exit_date else None,
    }


def _log_to_dict(l: AnalysisLog) -> dict:
    return {
        "symbol": l.symbol,
        "decision": l.decision,
        "confidence": l.confidence,
        "reasoning": l.reasoning,
        "market_context": l.market_context,
        "committee_verdict": l.committee_verdict,
        "time": l.analysis_time.isoformat() if l.analysis_time else None,
    }


async def _send_cycle_notification(cycle_number: int, candidates: list, approved: list, rejected: list, portfolio: Portfolio):
    """Send Telegram notification for cycle completion."""
    try:
        from app.services.telegram_service import send_telegram_alert
        
        msg = f"🤖 *Shadow Portfolio — Cycle #{cycle_number}*\n\n"
        msg += f"💰 Portfolio: ₹{portfolio.portfolio_value:,.0f}\n"
        msg += f"💵 Cash: ₹{portfolio.cash_balance:,.0f}\n\n"
        
        if candidates:
            msg += f"📋 *Candidates Considered:* {len(candidates)}\n"
            for c in candidates:
                msg += f"  • {c['symbol']} (Score: {c.get('momentum_score', '?')})\n"
        else:
            msg += "📋 No candidates scanned this cycle\n"
        
        if approved:
            msg += f"\n✅ *Approved:* {len(approved)}\n"
            for a in approved:
                msg += f"  • {a['symbol']} @ ₹{a.get('entry_price', '?')}\n"
        
        if rejected:
            msg += f"\n❌ *Rejected:* {len(rejected)}\n"
            for r in rejected:
                msg += f"  • {r['symbol']} — {r.get('reason', 'N/A')}\n"
        
        if not candidates and not approved and not rejected:
            msg += "\n⏸️ No new opportunities (portfolio full or low cash)"
        
        await send_telegram_alert(msg)
    except Exception as e:
        logger.warning(f"Failed to send cycle notification: {e}")


async def get_cycle_history(limit: int = 20) -> list[dict]:
    """Get history of all cycle runs."""
    await init_db()
    factory = get_session_factory()
    
    async with factory() as session:
        result = await session.execute(
            select(CycleLog).order_by(CycleLog.cycle_time.desc()).limit(limit)
        )
        cycles = result.scalars().all()
        return [
            {
                "cycle_number": c.cycle_number,
                "cycle_time": c.cycle_time.isoformat() if c.cycle_time else None,
                "market_context": c.market_context,
                "candidates_considered": json.loads(c.candidates_considered) if c.candidates_considered else [],
                "candidates_approved": json.loads(c.candidates_approved) if c.candidates_approved else [],
                "candidates_rejected": json.loads(c.candidates_rejected) if c.candidates_rejected else [],
                "exit_decisions": json.loads(c.exit_decisions) if c.exit_decisions else [],
                "portfolio_value_before": c.portfolio_value_before,
                "portfolio_value_after": c.portfolio_value_after,
                "num_positions_after": c.num_positions_after,
                "summary": c.summary,
            }
            for c in cycles
        ]
