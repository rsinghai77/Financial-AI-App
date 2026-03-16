"""Market Data Service — fetches and caches market data for the application layer.

GRD-OPS-002: Returns cached data with staleness warning when APIs are unavailable.
GRD-OPS-003: Always surfaces data freshness to the caller.
GRD-SEC-005: Only ticker symbols sent to external APIs.
"""

import logging
from decimal import Decimal
from typing import Any

from finapp.domain.models.market import FundamentalData, MarketQuote, OHLCVBar

logger = logging.getLogger(__name__)


class MarketDataService:
    """Application-layer wrapper around the market-data-mcp tools."""

    async def get_quotes(self, tickers: list[str]) -> dict[str, MarketQuote]:
        """Fetch current quotes for a list of tickers.

        Args:
            tickers: List of ticker symbols.

        Returns:
            Dict mapping ticker -> MarketQuote domain model.
        """
        if not tickers:
            return {}

        from finapp.mcp_servers.market_data_server import get_quote
        raw_quotes = await get_quote(tickers)

        result: dict[str, MarketQuote] = {}
        for q in raw_quotes:
            if "error" in q:
                logger.warning("Quote error for %s: %s", q.get("ticker"), q.get("error"))
                continue
            try:
                from datetime import datetime, timezone
                result[q["ticker"]] = MarketQuote(
                    ticker=q["ticker"],
                    price=Decimal(str(q.get("price", 0))),
                    change=Decimal(str(q.get("change", 0))),
                    change_pct=Decimal(str(q.get("change_pct", 0))),
                    volume=int(q.get("volume", 0)),
                    market_cap=Decimal(str(q.get("market_cap", 0))) if q.get("market_cap") else None,
                    high_52w=Decimal(str(q.get("high_52w", 0))) if q.get("high_52w") else None,
                    low_52w=Decimal(str(q.get("low_52w", 0))) if q.get("low_52w") else None,
                    data_timestamp=datetime.fromisoformat(q.get("data_timestamp", datetime.now(timezone.utc).isoformat())),
                    is_cached=q.get("is_cached", False),
                    cache_age_seconds=q.get("cache_age_seconds", 0),
                )
            except Exception as exc:
                logger.warning("Failed to parse quote for %s: %s", q.get("ticker"), exc)
        return result

    async def get_prices_map(self, tickers: list[str]) -> dict[str, Decimal]:
        """Return ticker -> price mapping for portfolio valuation."""
        quotes = await self.get_quotes(tickers)
        return {ticker: quote.price for ticker, quote in quotes.items()}

    async def get_historical_prices(
        self, ticker: str, period: str = "1y", interval: str = "1d"
    ) -> list[OHLCVBar]:
        """Fetch historical OHLCV data for a ticker."""
        from finapp.mcp_servers.market_data_server import get_historical_prices
        raw = await get_historical_prices(ticker, period, interval)
        bars = []
        for b in raw.get("bars", []):
            try:
                from datetime import date
                bars.append(OHLCVBar(
                    date=date.fromisoformat(b["date"]),
                    open=Decimal(str(b["open"])),
                    high=Decimal(str(b["high"])),
                    low=Decimal(str(b["low"])),
                    close=Decimal(str(b["close"])),
                    volume=int(b["volume"]),
                    adj_close=Decimal(str(b.get("adj_close", b["close"]))),
                ))
            except Exception as exc:
                logger.warning("Failed to parse bar: %s", exc)
        return bars

    async def get_daily_returns(self, ticker: str, period: str = "1y") -> list[float]:
        """Compute daily percentage returns from historical prices."""
        bars = await self.get_historical_prices(ticker, period)
        if len(bars) < 2:
            return []
        closes = [float(b.close) for b in bars]
        return [
            (closes[i] - closes[i - 1]) / closes[i - 1]
            for i in range(1, len(closes))
            if closes[i - 1] != 0
        ]

    async def get_fundamentals(self, ticker: str) -> FundamentalData:
        """Fetch fundamental financial data for a company."""
        from finapp.mcp_servers.market_data_server import get_fundamentals
        raw = await get_fundamentals(ticker)
        from datetime import datetime, timezone

        def _dec(val: Any) -> Decimal | None:
            return Decimal(str(val)) if val is not None else None

        return FundamentalData(
            ticker=ticker,
            pe_ratio=_dec(raw.get("pe_ratio")),
            pb_ratio=_dec(raw.get("pb_ratio")),
            ps_ratio=_dec(raw.get("ps_ratio")),
            ev_ebitda=_dec(raw.get("ev_ebitda")),
            dividend_yield=_dec(raw.get("dividend_yield")),
            payout_ratio=_dec(raw.get("payout_ratio")),
            eps_ttm=_dec(raw.get("eps_ttm")),
            revenue_ttm=_dec(raw.get("revenue_ttm")),
            net_income_ttm=_dec(raw.get("net_income_ttm")),
            debt_to_equity=_dec(raw.get("debt_to_equity")),
            return_on_equity=_dec(raw.get("return_on_equity")),
            profit_margin=_dec(raw.get("profit_margin")),
            earnings_growth_yoy=_dec(raw.get("earnings_growth_yoy")),
        )
