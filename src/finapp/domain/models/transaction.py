"""Transaction domain model — immutable record of a financial event."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, computed_field, model_validator


class Transaction(BaseModel):
    """Immutable record of a financial transaction.

    GRD-ARCH: Transactions are append-only — never modified after creation.
    Corrections are recorded as new offsetting transactions.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    account_id: uuid.UUID
    ticker: str = Field(max_length=10)
    transaction_type: str = Field(
        description="buy|sell|dividend|transfer_in|transfer_out|split|reinvestment"
    )
    quantity: Decimal = Field(
        description="Positive for acquisitions (buy, transfer_in), negative for disposals"
    )
    price_per_share: Decimal = Field(ge=Decimal(0))
    fees: Decimal = Field(default=Decimal(0), ge=Decimal(0))
    transaction_date: date
    settlement_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def validate_quantity_sign(self) -> "Transaction":
        """Ensure quantity sign matches transaction type."""
        disposal_types = {"sell", "transfer_out"}
        acquisition_types = {"buy", "transfer_in", "dividend", "reinvestment", "split"}
        if self.transaction_type in disposal_types and self.quantity > 0:
            object.__setattr__(self, "quantity", -self.quantity)
        if self.transaction_type in acquisition_types and self.quantity < 0:
            object.__setattr__(self, "quantity", -self.quantity)
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_amount(self) -> Decimal:
        """Total transaction amount including fees."""
        return abs(self.quantity) * self.price_per_share + self.fees

    model_config = {"frozen": True}  # Immutable — matches GRD-ARCH
