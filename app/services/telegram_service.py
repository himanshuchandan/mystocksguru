"""Telegram notification service."""

import httpx
from loguru import logger
from app.config import settings


async def send_telegram_alert(message: str) -> bool:
    """Send a message via Telegram bot."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("Telegram not configured, skipping notification.")
        return False

    # Telegram has a 4096 char limit per message
    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]

    try:
        async with httpx.AsyncClient() as client:
            for chunk in chunks:
                # Try Markdown first, fallback to plain text
                resp = await client.post(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                    json={
                        "chat_id": settings.telegram_chat_id,
                        "text": chunk,
                        "parse_mode": "Markdown",
                    },
                    timeout=10,
                )
                if resp.status_code != 200:
                    # Retry without parse_mode
                    await client.post(
                        f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                        json={
                            "chat_id": settings.telegram_chat_id,
                            "text": chunk,
                        },
                        timeout=10,
                    )
        logger.info("✅ Telegram alert sent successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
        return False
