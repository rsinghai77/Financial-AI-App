"""Financial goal domain model."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, computed_field


class FinancialGoal(BaseModel):
    """A user-defined financial goal with progress tracking."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str = Field(max_length=200)
    goal_type: str = Field(
        description="retirement|house_down_payment|education|emergency_fund|travel|custom"
    )
    target_amount: Decimal = Field(gt=Decimal(0))
    target_date: date
    current_amount: Decimal = Field(default=Decimal(0), ge=Decimal(0))
    monthly_contribution: Decimal = Field(default=Decimal(0), ge=Decimal(0))
    assumed_return_rate: Decimal = Field(
        default=Decimal("0.07"),
        description="Annual return assumption (e.g., 0.07 = 7%)",
    )
    notes: Optional[str] = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def progress_pct(self) -> Decimal:
        """Current progress as percentage of target amount."""
        if self.target_amount == 0:
            return Decimal(0)
        return min((self.current_amount / self.target_amount) * Decimal(100), Decimal(100))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def remaining_amount(self) -> Decimal:
        """Amount still needed to reach the goal."""
        return max(self.target_amount - self.current_amount, Decimal(0))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def days_to_target(self) -> int:
        """Calendar days until target date."""
        return max((self.target_date - date.today()).days, 0)
