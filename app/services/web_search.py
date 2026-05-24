"""Web Search Service - Targeted financial data search using DuckDuckGo.

Strategy:
- Searches are targeted at TRUSTED financial sources only
- Site-specific queries ensure quality data from known platforms
- Used as context enrichment for non-Gemini LLMs (Anthropic/OpenAI)
- Gemini uses its own Google Search grounding instead
"""

from ddgs import DDGS
from loguru import logger
from typing import List


# Trusted Indian financial sources - prioritized
TRUSTED_SOURCES = [
    "moneycontrol.com",
    "economictimes.indiatimes.com",
    "livemint.com",
    "ndtvprofit.com",
    "rbi.org.in",
    "nseindia.com",
    "bseindia.com",
    "sebi.gov.in",
    "reuters.com",
    "bloomberg.com",
    "tickertape.in",
    "screener.in",
    "trendlyne.com",
    "valueresearchonline.com",
]


def search_market_news() -> List[dict]:
    """Search for latest Indian market news from trusted sources."""
    queries = [
        "Nifty Sensex market today 2026 site:moneycontrol.com",
        "Indian stock market FII DII today site:economictimes.indiatimes.com",
        "India market news today site:livemint.com",
        "NSE BSE market update site:ndtvprofit.com",
    ]
    return _run_searches(queries, max_results_per_query=4)


def search_stock_news(symbol: str) -> List[dict]:
    """Search for news about a specific stock from trusted sources."""
    # Clean symbol
    clean_symbol = symbol.replace(".NS", "").replace(".BO", "")

    queries = [
        f"{clean_symbol} stock news site:moneycontrol.com OR site:economictimes.indiatimes.com OR site:livemint.com",
        f"{clean_symbol} earnings quarterly results site:moneycontrol.com OR site:screener.in OR site:tickertape.in",
        f"{clean_symbol} analyst target price site:trendlyne.com OR site:moneycontrol.com",
    ]
    return _run_searches(queries, max_results_per_query=3)


def search_macro_events() -> List[dict]:
    """Search for macro events affecting Indian markets."""
    queries = [
        "RBI interest rate policy 2026 site:rbi.org.in OR site:livemint.com",
        "crude oil gold impact Indian market site:moneycontrol.com",
        "FII selling buying India site:moneycontrol.com OR site:economictimes.indiatimes.com",
    ]
    return _run_searches(queries, max_results_per_query=3)


def search_sector_news(sector: str) -> List[dict]:
    """Search for sector-specific news."""
    queries = [
        f"{sector} sector India stocks site:moneycontrol.com OR site:economictimes.indiatimes.com",
    ]
    return _run_searches(queries, max_results_per_query=3)


def _run_searches(queries: List[str], max_results_per_query: int = 5) -> List[dict]:
    """Execute multiple searches and deduplicate results."""
    results = []
    seen_urls = set()

    with DDGS() as ddgs:
        for query in queries:
            try:
                hits = ddgs.text(query, max_results=max_results_per_query)
                for hit in hits:
                    url = hit.get("href", "")
                    if url not in seen_urls:
                        seen_urls.add(url)
                        results.append({
                            "title": hit.get("title", ""),
                            "snippet": hit.get("body", ""),
                            "source": url,
                        })
            except Exception as e:
                logger.warning(f"Search failed for query '{query[:50]}...': {e}")

    logger.info(f"🔍 Web search: found {len(results)} results from trusted sources")
    return results


def format_search_results(results: List[dict]) -> str:
    """Format search results as context for LLM."""
    if not results:
        return "No additional web search results available."

    lines = ["## Live Web Search Results (from trusted financial sources)\n"]
    for r in results[:15]:  # Cap at 15 to avoid token overload
        source_domain = r["source"].split("/")[2] if "/" in r["source"] else r["source"]
        lines.append(f"**[{source_domain}]** {r['title']}")
        lines.append(f"  {r['snippet'][:200]}")
        lines.append("")

    return "\n".join(lines)


def get_enriched_market_context() -> str:
    """Get full enriched context from web search - for non-Gemini providers."""
    logger.info("🌐 Fetching live market data from trusted sources...")

    market_news = search_market_news()
    macro_events = search_macro_events()

    all_results = market_news + macro_events
    return format_search_results(all_results)


def get_enriched_stock_context(symbol: str) -> str:
    """Get enriched context for a specific stock - for non-Gemini providers."""
    results = search_stock_news(symbol)
    return format_search_results(results)
