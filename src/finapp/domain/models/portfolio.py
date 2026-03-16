"""Portfolio aggregate root domain model."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, computed_field

if TYPE_CHECKING:
    from finapp.domain.models.account import Account


class Portfolio(BaseModel):
    """Aggregate root containing all user accounts and holdings.

    Computed properties (total_value, etc.) require current market prices
    to be injected into each Account/Holding before calling them.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: str
    accounts: list["Account"] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_value(self) -> Decimal:
        """Sum of current value across all active accounts."""
        return sum((acc.total_value for acc in self.accounts if acc.is_active), Decimal(0))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_cost_basis(self) -> Decimal:
        """Sum of cost basis across all active accounts."""
        return sum((acc.total_cost_basis for acc in self.accounts if acc.is_active), Decimal(0))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_gain_loss(self) -> Decimal:
        """Total unrealised gain/loss in dollars."""
        return self.total_value - self.total_cost_basis

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_gain_loss_pct(self) -> Decimal:
        """Total unrealised gain/loss as a percentage of cost basis."""
        if self.total_cost_basis == 0:
            return Decimal(0)
        return (self.total_gain_loss / self.total_cost_basis) * Decimal(100)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def asset_allocation(self) -> dict[str, Decimal]:
        """Asset class breakdown as percentages of total portfolio value."""
        if self.total_value == 0:
            return {}
        allocation: dict[str, Decimal] = {}
        for account in self.accounts:
            if not account.is_active:
                continue
            for holding in account.holdings:
                if not holding.is_open:
                    continue
                pct = (holding.current_value / self.total_value) * Decimal(100)
                allocation[holding.asset_class] = (
                    allocation.get(holding.asset_class, Decimal(0)) + pct
                )
        return allocation

    model_config = {"arbitrary_types_allowed": True}
