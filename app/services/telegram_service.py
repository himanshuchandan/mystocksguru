"""Telegram notification service."""

import re
import httpx
from loguru import logger
from app.config import settings


def _markdown_to_html(text: str) -> str:
    """Convert basic Markdown formatting to Telegram HTML."""
    # Bold: *text* or **text** → <b>text</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<b>\1</b>', text)
    # Italic: _text_ → <i>text</i>
    text = re.sub(r'(?<![a-zA-Z])_(.+?)_(?![a-zA-Z])', r'<i>\1</i>', text)
    # Code: `text` → <code>text</code>
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    # Escape remaining HTML special chars (but not our tags)
    # Remove any stray asterisks/underscores that weren't matched
    return text


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
                html_chunk = _markdown_to_html(chunk)
                # Try HTML parse mode first
                resp = await client.post(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                    json={
                        "chat_id": settings.telegram_chat_id,
                        "text": html_chunk,
                        "parse_mode": "HTML",
                    },
                    timeout=10,
                )
                if resp.status_code != 200:
                    # Fallback: strip all formatting and send plain text
                    plain = re.sub(r'[*_`]', '', chunk)
                    await client.post(
                        f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                        json={
                            "chat_id": settings.telegram_chat_id,
                            "text": plain,
                        },
                        timeout=10,
                    )
        logger.info("✅ Telegram alert sent successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")
        return False
