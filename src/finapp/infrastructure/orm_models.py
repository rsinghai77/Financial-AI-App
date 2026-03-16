"""SQLAlchemy ORM table definitions.

These map to the database schema defined in openspec/data_models.yaml.
GRD-ARCH-002: Only infrastructure layer imports these — never domain or GUI.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy import Date as SADate
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from finapp.infrastructure.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class PortfolioORM(Base):
    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    accounts: Mapped[list["AccountORM"]] = relationship(
        "AccountORM", back_populates="portfolio", cascade="all, delete-orphan"
    )


class AccountORM(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    portfolio_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    portfolio: Mapped["PortfolioORM"] = relationship("PortfolioORM", back_populates="accounts")
    holdings: Mapped[list["HoldingORM"]] = relationship(
        "HoldingORM", back_populates="account", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["TransactionORM"]] = relationship(
        "TransactionORM", back_populates="account"
    )


class HoldingORM(Base):
    __tablename__ = "holdings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    asset_class: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    cost_basis_per_share: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    purchase_date: Mapped[date] = mapped_column(SADate, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    account: Mapped["AccountORM"] = relationship("AccountORM", back_populates="holdings")
    tax_lots: Mapped[list["TaxLotORM"]] = relationship(
        "TaxLotORM", back_populates="holding", cascade="all, delete-orphan"
    )


class TaxLotORM(Base):
    __tablename__ = "tax_lots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    holding_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("holdings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    cost_basis_per_share: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    purchase_date: Mapped[date] = mapped_column(SADate, nullable=False, index=True)

    holding: Mapped["HoldingORM"] = relationship("HoldingORM", back_populates="tax_lots")


class TransactionORM(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    price_per_share: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    fees: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal(0))
    transaction_date: Mapped[date] = mapped_column(SADate, nullable=False, index=True)
    settlement_date: Mapped[Optional[date]] = mapped_column(SADate, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    account: Mapped["AccountORM"] = relationship("AccountORM", back_populates="transactions")


class WatchlistItemORM(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    added_date: Mapped[date] = mapped_column(SADate, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    alerts: Mapped[list["PriceAlertORM"]] = relationship(
        "PriceAlertORM", back_populates="watchlist_item", cascade="all, delete-orphan"
    )


class PriceAlertORM(Base):
    __tablename__ = "price_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    watchlist_item_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("watchlist_items.id", ondelete="CASCADE"), nullable=True
    )
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    threshold_value: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    watchlist_item: Mapped[Optional["WatchlistItemORM"]] = relationship(
        "WatchlistItemORM", back_populates="alerts"
    )


class FinancialGoalORM(Base):
    __tablename__ = "financial_goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    goal_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    target_date: Mapped[date] = mapped_column(SADate, nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal(0))
    monthly_contribution: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal(0))
    assumed_return_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0.07"))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
