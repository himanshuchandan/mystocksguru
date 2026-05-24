"""Risk Management Agent - position sizing, stop losses, drawdown."""


def calculate_position_size(
    capital: float,
    risk_per_trade_pct: float = 2.0,
    entry_price: float = 0,
    stop_loss_price: float = 0,
) -> dict:
    """Calculate position size based on risk management rules."""
    risk_amount = capital * (risk_per_trade_pct / 100)

    if entry_price <= 0 or stop_loss_price <= 0:
        return {"error": "Invalid entry/stop loss prices"}

    risk_per_share = abs(entry_price - stop_loss_price)
    if risk_per_share == 0:
        return {"error": "Entry and stop loss are the same"}

    shares = int(risk_amount / risk_per_share)
    position_value = shares * entry_price
    max_allocation_pct = (position_value / capital) * 100

    return {
        "shares": shares,
        "position_value": round(position_value, 2),
        "risk_amount": round(risk_amount, 2),
        "risk_per_share": round(risk_per_share, 2),
        "max_allocation_pct": round(max_allocation_pct, 2),
        "stop_loss": round(stop_loss_price, 2),
    }


def suggest_stop_loss(entry_price: float, atr: float, multiplier: float = 1.5) -> dict:
    """Suggest stop loss based on ATR."""
    sl = entry_price - (atr * multiplier)
    risk_pct = ((entry_price - sl) / entry_price) * 100

    return {
        "entry": round(entry_price, 2),
        "stop_loss": round(sl, 2),
        "risk_pct": round(risk_pct, 2),
        "atr_used": round(atr, 2),
        "multiplier": multiplier,
    }


def calculate_risk_reward(entry: float, stop_loss: float, target: float) -> dict:
    """Calculate risk-reward ratio."""
    risk = abs(entry - stop_loss)
    reward = abs(target - entry)
    ratio = reward / risk if risk > 0 else 0

    return {
        "entry": entry,
        "stop_loss": stop_loss,
        "target": target,
        "risk": round(risk, 2),
        "reward": round(reward, 2),
        "risk_reward_ratio": f"1:{round(ratio, 1)}",
        "favorable": ratio >= 2,
    }
