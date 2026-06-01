"""Database models for AI Shadow Portfolio."""

from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime

Base = declarative_base()


class Portfolio(Base):
    """Shadow portfolio state."""
    __tablename__ = "shadow_portfolio"

    id = Column(Integer, primary_key=True)
    initial_capital = Column(Float, nullable=False, default=20000.0)
    cash_balance = Column(Float, nullable=False, default=20000.0)
    portfolio_value = Column(Float, nullable=False, default=20000.0)
    total_realized_pnl = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    max_drawdown_pct = Column(Float, default=0.0)
    peak_value = Column(Float, default=20000.0)
    benchmark_start_value = Column(Float, nullable=True)  # Nifty50 at start
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Position(Base):
    """Open and closed positions."""
    __tablename__ = "shadow_positions"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=False)
    target_price = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    capital_allocated = Column(Float, nullable=False)
    confidence_score = Column(Integer, default=0)  # 1-100
    status = Column(String(10), default="OPEN")  # OPEN, CLOSED, STOPPED_OUT
    entry_reason = Column(Text, nullable=True)
    exit_reason = Column(Text, nullable=True)
    entry_time = Column(DateTime, default=datetime.utcnow)
    exit_time = Column(DateTime, nullable=True)
    holding_days = Column(Integer, default=0)


class Trade(Base):
    """Completed trade history."""
    __tablename__ = "shadow_trades"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    direction = Column(String(4), default="BUY")  # BUY/SELL
    quantity = Column(Integer, nullable=False)
    buy_price = Column(Float, nullable=False)
    sell_price = Column(Float, nullable=True)
    profit_loss = Column(Float, default=0.0)
    profit_loss_pct = Column(Float, default=0.0)
    capital_used = Column(Float, nullable=False)
    confidence_score = Column(Integer, default=0)
    reason = Column(Text, nullable=True)
    exit_reason = Column(Text, nullable=True)
    market_context = Column(Text, nullable=True)
    holding_days = Column(Integer, default=0)
    trade_date = Column(DateTime, default=datetime.utcnow)
    exit_date = Column(DateTime, nullable=True)


class AnalysisLog(Base):
    """AI decision audit trail."""
    __tablename__ = "shadow_analysis_log"

    id = Column(Integer, primary_key=True)
    analysis_time = Column(DateTime, default=datetime.utcnow)
    symbol = Column(String(20), nullable=False)
    decision = Column(String(20), nullable=False)  # BUY, HOLD, SELL, SKIP, INCREASE, DECREASE
    confidence = Column(Integer, default=0)  # 1-100
    reasoning = Column(Text, nullable=True)
    market_context = Column(Text, nullable=True)
    technical_summary = Column(Text, nullable=True)
    committee_verdict = Column(Text, nullable=True)


class DailySnapshot(Base):
    """Daily portfolio value for charting/benchmarking."""
    __tablename__ = "shadow_daily_snapshots"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    portfolio_value = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    invested_value = Column(Float, nullable=False)
    num_positions = Column(Integer, default=0)
    nifty_value = Column(Float, nullable=True)  # Benchmark
    daily_return_pct = Column(Float, default=0.0)
    cumulative_return_pct = Column(Float, default=0.0)
    nifty_cumulative_return_pct = Column(Float, default=0.0)


class CycleLog(Base):
    """Log of each shadow portfolio cycle run."""
    __tablename__ = "shadow_cycle_logs"

    id = Column(Integer, primary_key=True)
    cycle_time = Column(DateTime, default=datetime.utcnow)
    cycle_number = Column(Integer, nullable=False)
    market_context = Column(Text, nullable=True)
    candidates_considered = Column(Text, nullable=True)  # JSON list
    candidates_approved = Column(Text, nullable=True)  # JSON list
    candidates_rejected = Column(Text, nullable=True)  # JSON list
    exit_decisions = Column(Text, nullable=True)  # JSON list
    portfolio_value_before = Column(Float, nullable=True)
    portfolio_value_after = Column(Float, nullable=True)
    num_positions_after = Column(Integer, default=0)
    summary = Column(Text, nullable=True)


# Database setup
_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine("sqlite+aiosqlite:///./shadow_portfolio.db", echo=False)
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        from sqlalchemy.ext.asyncio import async_sessionmaker
        _session_factory = async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _session_factory


async def init_db():
    """Create all tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    factory = get_session_factory()
    async with factory() as session:
        yield session
