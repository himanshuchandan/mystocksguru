"""News Agent - fetches and summarizes market news."""

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from typing import List


async def fetch_moneycontrol_headlines() -> List[str]:
    """Scrape top headlines from Moneycontrol."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.moneycontrol.com/news/business/markets/",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            soup = BeautifulSoup(resp.text, "html.parser")
            headlines = []
            for item in soup.select("h2 a")[:10]:
                text = item.get_text(strip=True)
                if text:
                    headlines.append(text)
            return headlines
    except Exception as e:
        logger.warning(f"Failed to fetch Moneycontrol: {e}")
        return []


async def fetch_economic_times_headlines() -> List[str]:
    """Scrape top headlines from Economic Times Markets."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://economictimes.indiatimes.com/markets",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            soup = BeautifulSoup(resp.text, "html.parser")
            headlines = []
            for item in soup.select("h2 a, h3 a")[:10]:
                text = item.get_text(strip=True)
                if text and len(text) > 20:
                    headlines.append(text)
            return headlines
    except Exception as e:
        logger.warning(f"Failed to fetch ET: {e}")
        return []


async def get_news_summary() -> dict:
    """Get aggregated news headlines."""
    mc_headlines = await fetch_moneycontrol_headlines()
    et_headlines = await fetch_economic_times_headlines()

    return {
        "moneycontrol": mc_headlines,
        "economic_times": et_headlines,
        "total_headlines": len(mc_headlines) + len(et_headlines),
    }
