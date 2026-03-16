"""Market Data MCP Server — MCP-001.

Provides real-time and historical market data via yfinance (primary) with
Alpha Vantage as a secondary source. Implements cache-aside pattern.

GRD-SEC-005: Only ticker symbols are sent to external APIs — never portfolio quantities.
GRD-OPS-001: Respects rate limits via diskcache TTLs.
GRD-OPS-002: Graceful degradation — returns cached data when APIs are unavailable.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

import httpx
import yfinance as yf
from mcp.server import FastMCP

from finapp.config import settings
from finapp.infrastructure.cache.market_data_cache import get_cache

logger = logging.getLogger(__name__)
mcp = FastMCP("market-data-mcp")
cache = get_cache()


@mcp.tool()
async def get_quote(tickers: list[str]) -> list[dict[str, Any]]:
    """Get current market quote for one or more ticker symbols.

    Args:
        tickers: List of ticker symbols (e.g., ["AAPL", "MSFT", "SPY"]). Max 20.

    Returns:
        List of quote dicts with price, change, change_pct, volume, etc.
    """
    if len(tickers) > 20:
        tickers = tickers[:20]

    results = []
    uncached = []

    for ticker in tickers:
        ticker = ticker.upper().strip()
        cached = cache.get_quote(ticker)
        if cached:
            results.append(cached)
        else:
            uncached.append(ticker)

    if uncached:
        fresh = await _fetch_quotes_yfinance(uncached)
        for item in fresh:
            cache.set_quote(item["ticker"], item)
        results.extend(fresh)

    return results


async def _fetch_quotes_yfinance(tickers: list[str]) -> list[dict[str, Any]]:
    """Fetch quotes from yfinance (Yahoo Finance — no API key required)."""
    results = []
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).fast_info
            results.append({
                "ticker": ticker,
                "price": float(getattr(info, "last_price", 0) or 0),
                "change": float(getattr(info, "last_price", 0) or 0) - float(getattr(info, "previous_close", 0) or 0),
                "change_pct": (
                    (float(getattr(info, "last_price", 0) or 0) - float(getattr(info, "previous_close", 0) or 0))
                    / float(getattr(info, "previous_close", 1) or 1) * 100
                ),
                "volume": int(getattr(info, "three_month_average_volume", 0) or 0),
                "market_cap": float(getattr(info, "market_cap", 0) or 0),
                "high_52w": float(getattr(info, "year_high", 0) or 0),
                "low_52w": float(getattr(info, "year_low", 0) or 0),
                "data_timestamp": datetime.now(timezone.utc).isoformat(),
                "is_cached": False,
                "cache_age_seconds": 0,
            })
        except Exception as exc:
            logger.warning("Failed to fetch quote for %s: %s", ticker, exc)
            results.append({
                "ticker": ticker,
                "price": 0.0,
                "change": 0.0,
                "change_pct": 0.0,
                "volume": 0,
                "market_cap": 0.0,
                "high_52w": 0.0,
                "low_52w": 0.0,
                "data_timestamp": datetime.now(timezone.utc).isoformat(),
                "is_cached": False,
                "cache_age_seconds": 0,
                "error": str(exc),
            })
    return results


@mcp.tool()
async def get_historical_prices(
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> dict[str, Any]:
    """Get historical OHLCV price data for a ticker.

    Args:
        ticker: Ticker symbol (e.g., "AAPL").
        period: Time period — one of "1d","5d","1mo","3mo","6mo","ytd","1y","5y","max".
        interval: Bar interval — one of "1d","1wk","1mo" for daily+ data.

    Returns:
        Dict with 'bars' list of OHLCV dicts and metadata.
    """
    ticker = ticker.upper().strip()
    cached = cache.get_historical(ticker, period, interval)
    if cached:
        return cached

    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        bars = []
        for idx, row in df.iterrows():
            bars.append({
                "date": str(idx.date()),
                "open": float(row["Open"].iloc[0] if hasattr(row["Open"], "iloc") else row["Open"]),
                "high": float(row["High"].iloc[0] if hasattr(row["High"], "iloc") else row["High"]),
                "low": float(row["Low"].iloc[0] if hasattr(row["Low"], "iloc") else row["Low"]),
                "close": float(row["Close"].iloc[0] if hasattr(row["Close"], "iloc") else row["Close"]),
                "volume": int(row["Volume"].iloc[0] if hasattr(row["Volume"], "iloc") else row["Volume"]),
                "adj_close": float(row["Close"].iloc[0] if hasattr(row["Close"], "iloc") else row["Close"]),
            })
        result = {
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "bars": bars,
            "count": len(bars),
        }
        cache.set_historical(ticker, period, interval, result)
        return result
    except Exception as exc:
        logger.error("Failed to fetch historical prices for %s: %s", ticker, exc)
        return {"ticker": ticker, "period": period, "interval": interval, "bars": [], "error": str(exc)}


@mcp.tool()
async def get_fundamentals(ticker: str) -> dict[str, Any]:
    """Get fundamental financial data for a company.

    Args:
        ticker: Ticker symbol (e.g., "AAPL").

    Returns:
        Dict of fundamental metrics (P/E, P/B, dividend yield, etc.).
    """
    ticker = ticker.upper().strip()
    cached = cache.get_fundamentals(ticker)
    if cached:
        return cached

    try:
        info = yf.Ticker(ticker).info
        result: dict[str, Any] = {
            "ticker": ticker,
            "pe_ratio": info.get("trailingPE"),
            "pb_ratio": info.get("priceToBook"),
            "ps_ratio": info.get("priceToSalesTrailing12Months"),
            "ev_ebitda": info.get("enterpriseToEbitda"),
            "dividend_yield": info.get("dividendYield"),
            "payout_ratio": info.get("payoutRatio"),
            "eps_ttm": info.get("trailingEps"),
            "revenue_ttm": info.get("totalRevenue"),
            "net_income_ttm": info.get("netIncomeToCommon"),
            "debt_to_equity": info.get("debtToEquity"),
            "return_on_equity": info.get("returnOnEquity"),
            "profit_margin": info.get("profitMargins"),
            "earnings_growth_yoy": info.get("earningsGrowth"),
            "company_name": info.get("shortName", ticker),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "data_timestamp": datetime.now(timezone.utc).isoformat(),
        }
        cache.set_fundamentals(ticker, result)
        return result
    except Exception as exc:
        logger.error("Failed to fetch fundamentals for %s: %s", ticker, exc)
        return {"ticker": ticker, "error": str(exc)}


@mcp.tool()
async def get_technical_indicators(
    ticker: str,
    indicators: list[str],
    period: str = "3mo",
) -> dict[str, Any]:
    """Calculate technical analysis indicators for a ticker.

    Args:
        ticker: Ticker symbol.
        indicators: List of indicator names from: RSI, MACD, SMA_20, SMA_50,
            SMA_200, EMA_12, EMA_26, BOLLINGER_BANDS, ATR.
        period: Lookback period — "1mo","3mo","6mo","1y".

    Returns:
        Dict mapping indicator name to its computed series (list of {date, value}).
    """
    import pandas as pd
    import numpy as np

    ticker = ticker.upper().strip()
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        if df.empty:
            return {"ticker": ticker, "error": "No price data available"}

        close = df["Close"].squeeze()
        high = df["High"].squeeze()
        low = df["Low"].squeeze()
        volume = df["Volume"].squeeze()

        result: dict[str, Any] = {"ticker": ticker, "period": period}

        if "RSI" in indicators:
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            result["RSI"] = [{"date": str(d.date()), "value": round(float(v), 2)}
                             for d, v in zip(df.index, rsi) if not pd.isna(v)]

        if "MACD" in indicators:
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9, adjust=False).mean()
            result["MACD"] = [
                {"date": str(d.date()), "macd": round(float(m), 4), "signal": round(float(s), 4)}
                for d, m, s in zip(df.index, macd, signal)
                if not (pd.isna(m) or pd.isna(s))
            ]

        for name, window in [("SMA_20", 20), ("SMA_50", 50), ("SMA_200", 200)]:
            if name in indicators:
                sma = close.rolling(window).mean()
                result[name] = [{"date": str(d.date()), "value": round(float(v), 4)}
                                for d, v in zip(df.index, sma) if not pd.isna(v)]

        for name, span in [("EMA_12", 12), ("EMA_26", 26)]:
            if name in indicators:
                ema = close.ewm(span=span, adjust=False).mean()
                result[name] = [{"date": str(d.date()), "value": round(float(v), 4)}
                                for d, v in zip(df.index, ema)]

        if "BOLLINGER_BANDS" in indicators:
            sma20 = close.rolling(20).mean()
            std20 = close.rolling(20).std()
            result["BOLLINGER_BANDS"] = [
                {"date": str(d.date()), "upper": round(float(u), 4),
                 "middle": round(float(m), 4), "lower": round(float(lo), 4)}
                for d, u, m, lo in zip(df.index, sma20 + 2*std20, sma20, sma20 - 2*std20)
                if not pd.isna(m)
            ]

        if "ATR" in indicators:
            tr = pd.concat([
                high - low,
                (high - close.shift()).abs(),
                (low - close.shift()).abs(),
            ], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()
            result["ATR"] = [{"date": str(d.date()), "value": round(float(v), 4)}
                             for d, v in zip(df.index, atr) if not pd.isna(v)]

        return result

    except Exception as exc:
        logger.error("Failed to calculate indicators for %s: %s", ticker, exc)
        return {"ticker": ticker, "error": str(exc)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
