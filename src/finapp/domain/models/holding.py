"""Holding domain model — a single investment position."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class TaxLot(BaseModel):
    """Individual purchase lot for accurate tax basis tracking."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    holding_id: uuid.UUID
    quantity: Decimal = Field(gt=Decimal(0))
    cost_basis_per_share: Decimal = Field(gt=Decimal(0))
    purchase_date: date
    transaction_id: Optional[uuid.UUID] = None


class Holding(BaseModel):
    """A single investment position within an account.

    current_price must be set externally (from MarketDataService) before
    computed properties like current_value and gain_loss are meaningful.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    account_id: uuid.UUID
    ticker: str = Field(max_length=10)
    asset_class: str = Field(
        description="equity|etf|mutual_fund|bond|crypto|cash|reit|commodity|other"
    )
    quantity: Decimal = Field(ge=Decimal(0))
    cost_basis_per_share: Decimal = Field(ge=Decimal(0))
    purchase_date: date
    notes: Optional[str] = Field(default=None, max_length=1000)
    tax_lots: list[TaxLot] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_open: bool = True

    # Injected by MarketDataService — not persisted
    current_price: Decimal = Field(default=Decimal(0))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_cost_basis(self) -> Decimal:
        """Total cost basis in account currency."""
        return self.quantity * self.cost_basis_per_share

    @computed_field  # type: ignore[prop-decorator]
    @property
    def current_value(self) -> Decimal:
        """Current market value (requires current_price to be set)."""
        return self.quantity * self.current_price

    @computed_field  # type: ignore[prop-decorator]
    @property
    def gain_loss_dollars(self) -> Decimal:
        """Unrealised gain/loss in dollars."""
        return self.current_value - self.total_cost_basis

    @computed_field  # type: ignore[prop-decorator]
    @property
    def gain_loss_pct(self) -> Decimal:
        """Unrealised gain/loss as percentage of cost basis."""
        if self.total_cost_basis == 0:
            return Decimal(0)
        return (self.gain_loss_dollars / self.total_cost_basis) * Decimal(100)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def holding_period_days(self) -> int:
        """Number of days since first purchase."""
        return (date.today() - self.purchase_date).days

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_long_term(self) -> bool:
        """True if holding qualifies for long-term capital gains treatment (>= 365 days)."""
        return self.holding_period_days >= 365
