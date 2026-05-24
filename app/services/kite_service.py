"""Zerodha Kite integration service (read-only mode)."""

from loguru import logger
from app.config import settings


def _get_kite_client():
    """Get authenticated Kite client."""
    if not settings.kite_api_key or not settings.kite_access_token:
        return None

    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=settings.kite_api_key)
        kite.set_access_token(settings.kite_access_token)
        return kite
    except Exception as e:
        logger.error(f"Kite connection failed: {e}")
        return None


async def get_holdings() -> dict:
    """Fetch current holdings from Kite."""
    kite = _get_kite_client()
    if not kite:
        return {"holdings": [], "status": "not_connected"}

    try:
        holdings = kite.holdings()
        return {"holdings": holdings, "status": "connected"}
    except Exception as e:
        logger.error(f"Failed to fetch holdings: {e}")
        return {"holdings": [], "status": "error", "error": str(e)}


async def get_positions() -> dict:
    """Fetch current positions from Kite."""
    kite = _get_kite_client()
    if not kite:
        return {"positions": [], "status": "not_connected"}

    try:
        positions = kite.positions()
        return {"positions": positions, "status": "connected"}
    except Exception as e:
        logger.error(f"Failed to fetch positions: {e}")
        return {"positions": [], "status": "error", "error": str(e)}


async def get_margins() -> dict:
    """Fetch account margins from Kite."""
    kite = _get_kite_client()
    if not kite:
        return {"margins": {}, "status": "not_connected"}

    try:
        margins = kite.margins()
        return {"margins": margins, "status": "connected"}
    except Exception as e:
        logger.error(f"Failed to fetch margins: {e}")
        return {"margins": {}, "status": "error", "error": str(e)}
