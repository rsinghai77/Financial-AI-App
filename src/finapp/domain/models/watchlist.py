"""Watchlist and price alert domain models."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class PriceAlert(BaseModel):
    """A configurable price threshold alert for a security."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    ticker: str = Field(max_length=10)
    alert_type: str = Field(
        description="price_above|price_below|change_pct_above|change_pct_below"
    )
    threshold_value: Decimal
    is_active: bool = True
    last_triggered_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WatchlistItem(BaseModel):
    """A security being monitored without being held in the portfolio."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: str
    ticker: str = Field(max_length=10)
    added_date: date = Field(default_factory=date.today)
    notes: Optional[str] = Field(default=None, max_length=500)
    alerts: list[PriceAlert] = Field(default_factory=list)

    # Injected by MarketDataService — not persisted
    current_price: Optional[Decimal] = None
    day_change_pct: Optional[Decimal] = None
