"""Abstract repository interfaces for the domain layer.

GRD-ARCH-002: All database operations must go through these interfaces.
The domain layer defines the contract; the infrastructure layer implements it.
No SQLAlchemy or database imports here — only Python standard library and domain models.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from finapp.domain.models.account import Account
from finapp.domain.models.goal import FinancialGoal
from finapp.domain.models.holding import Holding, TaxLot
from finapp.domain.models.portfolio import Portfolio
from finapp.domain.models.transaction import Transaction
from finapp.domain.models.watchlist import PriceAlert, WatchlistItem


class IPortfolioRepository(ABC):
    """Abstract interface for portfolio and account persistence."""

    @abstractmethod
    async def get_portfolio(self, user_id: str) -> Optional[Portfolio]:
        """Fetch the portfolio for a given user, including all accounts and holdings."""
        ...

    @abstractmethod
    async def create_portfolio(self, user_id: str) -> Portfolio:
        """Create a new portfolio for a user."""
        ...

    @abstractmethod
    async def get_account(self, account_id: uuid.UUID) -> Optional[Account]:
        """Fetch a single account by ID."""
        ...

    @abstractmethod
    async def create_account(
        self,
        portfolio_id: uuid.UUID,
        name: str,
        account_type: str,
        currency: str = "USD",
    ) -> Account:
        """Create a new account within a portfolio."""
        ...

    @abstractmethod
    async def list_accounts(self, portfolio_id: uuid.UUID) -> list[Account]:
        """List all active accounts in a portfolio."""
        ...


class IHoldingRepository(ABC):
    """Abstract interface for holding persistence."""

    @abstractmethod
    async def get_holding(self, holding_id: uuid.UUID) -> Optional[Holding]:
        """Fetch a single holding by ID."""
        ...

    @abstractmethod
    async def list_holdings(
        self,
        account_id: uuid.UUID,
        include_closed: bool = False,
    ) -> list[Holding]:
        """List all holdings in an account."""
        ...

    @abstractmethod
    async def add_holding(self, holding: Holding) -> Holding:
        """Persist a new holding and return it with database-assigned fields."""
        ...

    @abstractmethod
    async def update_holding(
        self,
        holding_id: uuid.UUID,
        quantity: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Optional[Holding]:
        """Update mutable fields of an existing holding."""
        ...

    @abstractmethod
    async def close_holding(self, holding_id: uuid.UUID) -> None:
        """Mark a holding as closed (fully sold)."""
        ...

    @abstractmethod
    async def add_tax_lot(self, tax_lot: TaxLot) -> TaxLot:
        """Persist a new tax lot for a holding."""
        ...


class ITransactionRepository(ABC):
    """Abstract interface for transaction persistence (append-only)."""

    @abstractmethod
    async def add_transaction(self, transaction: Transaction) -> Transaction:
        """Persist a new transaction. Transactions are immutable once created."""
        ...

    @abstractmethod
    async def list_transactions(
        self,
        account_id: Optional[uuid.UUID] = None,
        ticker: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        transaction_types: Optional[list[str]] = None,
        limit: int = 100,
    ) -> list[Transaction]:
        """Retrieve transactions with optional filters."""
        ...


class IWatchlistRepository(ABC):
    """Abstract interface for watchlist and alert persistence."""

    @abstractmethod
    async def get_watchlist(self, user_id: str) -> list[WatchlistItem]:
        """Fetch the full watchlist for a user."""
        ...

    @abstractmethod
    async def add_watchlist_item(self, item: WatchlistItem) -> WatchlistItem:
        """Add a security to the watchlist."""
        ...

    @abstractmethod
    async def remove_watchlist_item(self, item_id: uuid.UUID) -> None:
        """Remove a security from the watchlist."""
        ...

    @abstractmethod
    async def add_price_alert(self, alert: PriceAlert) -> PriceAlert:
        """Add a price alert."""
        ...

    @abstractmethod
    async def get_active_alerts(self, ticker: Optional[str] = None) -> list[PriceAlert]:
        """Get all active price alerts, optionally filtered by ticker."""
        ...

    @abstractmethod
    async def deactivate_alert(self, alert_id: uuid.UUID) -> None:
        """Deactivate a triggered or cancelled alert."""
        ...


class IGoalRepository(ABC):
    """Abstract interface for financial goal persistence."""

    @abstractmethod
    async def list_goals(self, user_id: str) -> list[FinancialGoal]:
        """List all financial goals for a user."""
        ...

    @abstractmethod
    async def add_goal(self, goal: FinancialGoal) -> FinancialGoal:
        """Persist a new financial goal."""
        ...

    @abstractmethod
    async def update_goal(self, goal: FinancialGoal) -> FinancialGoal:
        """Update an existing financial goal."""
        ...

    @abstractmethod
    async def delete_goal(self, goal_id: uuid.UUID) -> None:
        """Delete a financial goal."""
        ...
