"""News Service — fetches and caches news for portfolio holdings."""

import logging

from finapp.domain.models.market import NewsArticle
from finapp.domain.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


class NewsService:
    """Application-layer wrapper around the news-mcp tools."""

    async def get_portfolio_news(
        self,
        portfolio: Portfolio,
        max_articles: int = 20,
    ) -> list[NewsArticle]:
        """Fetch news for all holdings in the portfolio.

        GRD-SEC-005: Only ticker symbols sent to news API — no portfolio values.

        Args:
            portfolio: Portfolio to fetch news for.
            max_articles: Max total articles across all holdings.

        Returns:
            List of NewsArticle domain models sorted by published_at descending.
        """
        tickers: list[str] = []
        for account in portfolio.accounts:
            for holding in account.holdings:
                if holding.is_open:
                    tickers.append(holding.ticker)

        if not tickers:
            return []

        query = " OR ".join(tickers[:5])  # NewsAPI supports OR queries
        from finapp.mcp_servers.news_server import search_news
        raw_articles = await search_news(query=query, tickers=tickers, max_articles=max_articles)

        articles = []
        for a in raw_articles:
            try:
                from datetime import datetime, timezone
                from decimal import Decimal
                articles.append(NewsArticle(
                    title=a.get("title", ""),
                    source=a.get("source", "Unknown"),
                    url=a.get("url", ""),
                    published_at=datetime.fromisoformat(
                        a.get("published_at", datetime.now(timezone.utc).isoformat())
                    ),
                    description=a.get("description"),
                    sentiment_score=Decimal(str(a.get("sentiment_score", 0))),
                    sentiment_label=a.get("sentiment_label", "neutral"),
                    relevant_tickers=a.get("relevant_tickers", []),
                    summary=a.get("summary"),
                ))
            except Exception as exc:
                logger.warning("Failed to parse article: %s", exc)

        return sorted(articles, key=lambda x: x.published_at, reverse=True)

    async def get_ticker_news(self, ticker: str, max_articles: int = 10) -> list[NewsArticle]:
        """Fetch news for a single ticker."""
        from finapp.domain.models.portfolio import Portfolio
        dummy = Portfolio(user_id="")
        # Directly call news server
        from finapp.mcp_servers.news_server import search_news
        from datetime import datetime, timezone
        from decimal import Decimal
        raw = await search_news(query=ticker, tickers=[ticker], max_articles=max_articles)
        articles = []
        for a in raw:
            try:
                articles.append(NewsArticle(
                    title=a.get("title", ""),
                    source=a.get("source", ""),
                    url=a.get("url", ""),
                    published_at=datetime.fromisoformat(
                        a.get("published_at", datetime.now(timezone.utc).isoformat())
                    ),
                    description=a.get("description"),
                    sentiment_score=Decimal(str(a.get("sentiment_score", 0))),
                    sentiment_label=a.get("sentiment_label", "neutral"),
                    relevant_tickers=a.get("relevant_tickers", [ticker]),
                ))
            except Exception as exc:
                logger.warning("Failed to parse article for %s: %s", ticker, exc)
        return articles
