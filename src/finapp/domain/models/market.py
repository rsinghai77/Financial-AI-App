"""Transient market data models — cached, not stored in the database."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class MarketQuote(BaseModel):
    """Real-time or delayed market quote for a single security."""

    ticker: str
    price: Decimal
    change: Decimal
    change_pct: Decimal
    volume: int
    market_cap: Optional[Decimal] = None
    high_52w: Optional[Decimal] = None
    low_52w: Optional[Decimal] = None
    data_timestamp: datetime
    is_cached: bool = False
    cache_age_seconds: int = 0


class OHLCVBar(BaseModel):
    """Single OHLCV price bar for historical data."""

    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    adj_close: Decimal


class FundamentalData(BaseModel):
    """Fundamental financial metrics for a company."""

    ticker: str
    pe_ratio: Optional[Decimal] = None
    pb_ratio: Optional[Decimal] = None
    ps_ratio: Optional[Decimal] = None
    ev_ebitda: Optional[Decimal] = None
    dividend_yield: Optional[Decimal] = None
    payout_ratio: Optional[Decimal] = None
    eps_ttm: Optional[Decimal] = None
    revenue_ttm: Optional[Decimal] = None
    net_income_ttm: Optional[Decimal] = None
    debt_to_equity: Optional[Decimal] = None
    return_on_equity: Optional[Decimal] = None
    profit_margin: Optional[Decimal] = None
    earnings_growth_yoy: Optional[Decimal] = None
    data_timestamp: datetime = Field(default_factory=datetime.utcnow)


class PortfolioSummary(BaseModel):
    """Computed portfolio overview (aggregated on demand, not stored)."""

    total_value: Decimal
    total_cost_basis: Decimal
    total_gain_loss: Decimal
    total_gain_loss_pct: Decimal
    day_change: Decimal = Decimal(0)
    day_change_pct: Decimal = Decimal(0)
    asset_allocation: dict[str, Decimal] = Field(default_factory=dict)
    as_of: datetime = Field(default_factory=datetime.utcnow)


class RiskMetrics(BaseModel):
    """Computed risk metrics (calculated on demand, not stored)."""

    var_95_1d_pct: Decimal
    var_95_1d_dollars: Decimal
    var_99_1d_pct: Decimal
    var_99_1d_dollars: Decimal
    portfolio_beta: Optional[Decimal] = None
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    max_drawdown_pct: Optional[Decimal] = None
    volatility_annualized: Optional[Decimal] = None
    calculated_at: datetime = Field(default_factory=datetime.utcnow)


class NewsArticle(BaseModel):
    """A financial news article with sentiment scoring."""

    title: str
    source: str
    url: str
    published_at: datetime
    description: Optional[str] = None
    sentiment_score: Decimal = Field(ge=Decimal(-1), le=Decimal(1))
    sentiment_label: str = Field(description="positive|neutral|negative")
    relevant_tickers: list[str] = Field(default_factory=list)
    summary: Optional[str] = None
