"""News & Sentiment MCP Server — MCP-002.

Fetches financial news, computes basic sentiment, and retrieves SEC filings.
GRD-SEC-005: Only ticker symbols sent to external APIs — no portfolio data.
GRD-OPS-001: Caches aggressively (100 req/day limit on NewsAPI free tier).
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from mcp.server import FastMCP

from finapp.config import settings
from finapp.infrastructure.cache.market_data_cache import get_cache

logger = logging.getLogger(__name__)
mcp = FastMCP("news-mcp")
cache = get_cache()

# Simple keyword-based sentiment lexicon
_POSITIVE_WORDS = {
    "beat", "beats", "surpass", "record", "growth", "profit", "gain", "rally",
    "upgrade", "outperform", "strong", "exceed", "positive", "bullish", "surge",
    "jump", "rise", "soar", "boost", "opportunity", "expansion",
}
_NEGATIVE_WORDS = {
    "miss", "misses", "decline", "loss", "drop", "fall", "cut", "downgrade",
    "underperform", "weak", "below", "negative", "bearish", "plunge", "crash",
    "risk", "concern", "warning", "lawsuit", "investigation", "default",
}


def _score_sentiment(text: str) -> tuple[float, str]:
    """Simple keyword-based sentiment scorer. Returns (score, label)."""
    words = re.findall(r"\b\w+\b", text.lower())
    pos = sum(1 for w in words if w in _POSITIVE_WORDS)
    neg = sum(1 for w in words if w in _NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.0, "neutral"
    score = (pos - neg) / total  # -1 to +1
    if score > 0.2:
        label = "positive"
    elif score < -0.2:
        label = "negative"
    else:
        label = "neutral"
    return round(score, 3), label


@mcp.tool()
async def search_news(
    query: str,
    tickers: Optional[list[str]] = None,
    from_date: Optional[str] = None,
    max_articles: int = 10,
) -> list[dict[str, Any]]:
    """Search for financial news articles.

    GRD-SEC-005: Only query strings and tickers are sent to external APIs.

    Args:
        query: Search query (company name, ticker, or topic).
        tickers: Optional list of tickers to include in query.
        from_date: ISO date to start search from (default: 7 days ago).
        max_articles: Maximum articles to return (max 50).

    Returns:
        List of article dicts with title, source, sentiment, URL.
    """
    max_articles = min(max_articles, 50)
    if tickers:
        query = f"{query} {' '.join(t.upper() for t in tickers)}"

    cache_key = f"{query}:{from_date}:{max_articles}"
    cached = cache.get_news(cache_key)
    if cached and "articles" in cached:
        return cached["articles"]

    from_dt = (
        datetime.fromisoformat(from_date)
        if from_date
        else datetime.now(timezone.utc) - timedelta(days=7)
    )

    articles: list[dict[str, Any]] = []

    if settings.news_api_key:
        articles = await _fetch_newsapi(query, from_dt, max_articles)

    if not articles:
        articles = _fallback_placeholder_news(query, tickers or [])

    result = {"articles": articles}
    cache.set_news(cache_key, result)
    return articles


async def _fetch_newsapi(
    query: str,
    from_dt: datetime,
    max_articles: int,
) -> list[dict[str, Any]]:
    """Fetch news from NewsAPI.org."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                settings.news_api_base_url + "/everything",
                params={
                    "q": query,
                    "from": from_dt.strftime("%Y-%m-%d"),
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": max_articles,
                    "apiKey": settings.news_api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("NewsAPI request failed: %s", exc)
        return []

    articles = []
    for art in data.get("articles", []):
        title = art.get("title", "")
        description = art.get("description", "")
        text = f"{title} {description}"
        score, label = _score_sentiment(text)
        articles.append({
            "title": title,
            "source": art.get("source", {}).get("name", "Unknown"),
            "url": art.get("url", ""),
            "published_at": art.get("publishedAt", ""),
            "description": description,
            "sentiment_score": score,
            "sentiment_label": label,
            "relevant_tickers": [],
        })
    return articles


def _fallback_placeholder_news(query: str, tickers: list[str]) -> list[dict[str, Any]]:
    """Return an empty list with a note when no API key is configured."""
    return [{
        "title": "News API not configured",
        "source": "System",
        "url": "",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "description": (
            f"Configure NEWS_API_KEY in .env to fetch real news for: {query}. "
            "See .env.example for setup instructions."
        ),
        "sentiment_score": 0.0,
        "sentiment_label": "neutral",
        "relevant_tickers": tickers,
    }]


@mcp.tool()
async def get_sentiment_score(
    text: Optional[str] = None,
    ticker: Optional[str] = None,
    lookback_days: int = 7,
) -> dict[str, Any]:
    """Analyze sentiment of text or aggregate news sentiment for a ticker.

    Args:
        text: Free text to score (optional — uses recent news if not provided).
        ticker: Ticker for news aggregation (optional).
        lookback_days: Days to look back for ticker news (default 7).

    Returns:
        Dict with score, label, article_count, confidence.
    """
    if text:
        score, label = _score_sentiment(text)
        return {
            "score": score,
            "label": label,
            "article_count": 1,
            "confidence": 0.6,
            "method": "keyword_analysis",
        }

    if ticker:
        articles = await search_news(query=ticker, tickers=[ticker], max_articles=20)
        if not articles:
            return {"score": 0.0, "label": "neutral", "article_count": 0, "confidence": 0.0}
        scores = [a["sentiment_score"] for a in articles if "sentiment_score" in a]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        if avg_score > 0.1:
            label = "positive"
        elif avg_score < -0.1:
            label = "negative"
        else:
            label = "neutral"
        return {
            "score": round(avg_score, 3),
            "label": label,
            "article_count": len(scores),
            "confidence": min(len(scores) / 10, 1.0),
        }

    return {"error": "Provide either 'text' or 'ticker'"}


@mcp.tool()
async def get_sec_filings(
    ticker: str,
    filing_types: Optional[list[str]] = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Get recent SEC filings for a company from EDGAR.

    Args:
        ticker: Ticker symbol.
        filing_types: List of form types to filter (default: 10-K, 10-Q, 8-K).
        limit: Maximum filings to return.

    Returns:
        List of filing dicts with form_type, filed_date, description, URL.
    """
    if filing_types is None:
        filing_types = ["10-K", "10-Q", "8-K"]

    cache_key = f"sec:{ticker.upper()}:{','.join(sorted(filing_types))}"
    cached = cache.get_news(cache_key)
    if cached and "filings" in cached:
        return cached["filings"][:limit]

    try:
        # EDGAR full-text search — public, no key required
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://efts.sec.gov/LATEST/search-index",
                params={
                    "q": ticker.upper(),
                    "dateRange": "custom",
                    "startdt": "2022-01-01",
                    "forms": ",".join(filing_types),
                    "hits.hits.total.value": limit,
                },
                headers={"User-Agent": "FinApp research@finapp.local"},
            )
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])
    except Exception as exc:
        logger.warning("SEC EDGAR request failed: %s", exc)
        return []

    filings = []
    for hit in hits[:limit]:
        src = hit.get("_source", {})
        filings.append({
            "form_type": src.get("form_type", ""),
            "filed_date": src.get("file_date", ""),
            "description": src.get("display_names", [""])[0] if src.get("display_names") else "",
            "url": f"https://www.sec.gov/Archives/edgar/data/{src.get('entity_id', '')}/{src.get('file_name', '')}",
        })

    cache.set_news(cache_key, {"filings": filings})
    return filings


@mcp.tool()
async def summarize_article(url: str) -> dict[str, Any]:
    """Generate a short summary of a news article by fetching its text.

    Note: This performs best-effort extraction. Some sites block scraping.

    Args:
        url: Article URL.

    Returns:
        Dict with summary, key_entities, sentiment.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "FinApp/0.1 research"})
            resp.raise_for_status()
            text = resp.text[:3000]  # First 3000 chars only
    except Exception as exc:
        return {"error": f"Could not fetch article: {exc}", "summary": "", "key_entities": [], "sentiment": "neutral"}

    # Strip HTML tags
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    snippet = clean[:800]

    score, label = _score_sentiment(snippet)

    # Extract potential ticker-like entities (2-5 uppercase letters)
    entities = list(set(re.findall(r"\b[A-Z]{2,5}\b", text)))[:10]

    return {
        "summary": snippet[:300] + "..." if len(snippet) > 300 else snippet,
        "key_entities": entities,
        "sentiment": label,
        "sentiment_score": score,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
