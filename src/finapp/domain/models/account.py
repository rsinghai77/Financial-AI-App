"""Account domain model — a named investment account."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, computed_field

from finapp.domain.models.holding import Holding


class Account(BaseModel):
    """A named investment account (brokerage, IRA, 401k, etc.)."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    portfolio_id: uuid.UUID
    name: str = Field(max_length=100)
    account_type: str = Field(
        description="brokerage|ira|roth_ira|401k|crypto|savings|other"
    )
    currency: str = Field(default="USD", max_length=3)
    holdings: list[Holding] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    notes: Optional[str] = Field(default=None, max_length=500)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_value(self) -> Decimal:
        """Sum of current value of all open holdings."""
        return sum(
            (h.current_value for h in self.holdings if h.is_open),
            Decimal(0),
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_cost_basis(self) -> Decimal:
        """Sum of cost basis of all open holdings."""
        return sum(
            (h.total_cost_basis for h in self.holdings if h.is_open),
            Decimal(0),
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def holdings_count(self) -> int:
        """Number of open holdings in this account."""
        return sum(1 for h in self.holdings if h.is_open)
