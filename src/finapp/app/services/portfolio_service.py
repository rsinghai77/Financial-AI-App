"""Portfolio Service — application layer use cases for portfolio management.

GRD-ARCH-001: No streamlit imports here. This is pure business logic.
GRD-ARCH-002: All DB access through repositories.
"""

import logging
import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from finapp.domain.models.account import Account
from finapp.domain.models.holding import Holding
from finapp.domain.models.market import PortfolioSummary
from finapp.domain.models.portfolio import Portfolio
from finapp.domain.models.transaction import Transaction
from finapp.infrastructure.repositories.portfolio_repository import (
    HoldingRepository,
    PortfolioRepository,
    TransactionRepository,
)

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "local_user"


class PortfolioService:
    """Use-case orchestrator for portfolio operations.

    Coordinates between the repository layer and the MCP market data server
    to produce fully-valued portfolio summaries.
    """

    def __init__(self) -> None:
        self._portfolio_repo = PortfolioRepository()
        self._holding_repo = HoldingRepository()
        self._transaction_repo = TransactionRepository()

    async def get_or_create_portfolio(self) -> Portfolio:
        """Return the user's portfolio, creating it if it does not exist."""
        portfolio = await self._portfolio_repo.get_portfolio(DEFAULT_USER_ID)
        if portfolio is None:
            portfolio = await self._portfolio_repo.create_portfolio(DEFAULT_USER_ID)
            # Create a default account for first-time users
            await self._portfolio_repo.create_account(
                portfolio.id, "Default Brokerage", "brokerage"
            )
            portfolio = await self._portfolio_repo.get_portfolio(DEFAULT_USER_ID)
        return portfolio  # type: ignore[return-value]

    async def get_portfolio_with_prices(
        self, prices: dict[str, Decimal]
    ) -> Portfolio:
        """Return the portfolio with current_price injected into each holding.

        Args:
            prices: Dict mapping ticker -> current price from MarketDataService.

        Returns:
            Portfolio with all holdings priced.
        """
        portfolio = await self.get_or_create_portfolio()
        for account in portfolio.accounts:
            for holding in account.holdings:
                if holding.ticker in prices:
                    holding.current_price = prices[holding.ticker]
        return portfolio

    async def get_portfolio_summary(self, prices: dict[str, Decimal]) -> PortfolioSummary:
        """Compute the high-level portfolio summary with live prices."""
        portfolio = await self.get_portfolio_with_prices(prices)
        return PortfolioSummary(
            total_value=portfolio.total_value,
            total_cost_basis=portfolio.total_cost_basis,
            total_gain_loss=portfolio.total_gain_loss,
            total_gain_loss_pct=portfolio.total_gain_loss_pct,
            asset_allocation=portfolio.asset_allocation,
        )

    async def add_holding(
        self,
        ticker: str,
        quantity: float,
        cost_basis_per_share: float,
        purchase_date: date,
        asset_class: str = "equity",
        account_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
    ) -> Holding:
        """Add a new holding to the portfolio.

        GRD-SEC-003: Input validation applied before persistence.
        """
        ticker = ticker.upper().strip()
        if not ticker or len(ticker) > 10:
            raise ValueError(f"Invalid ticker: {ticker}")
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if cost_basis_per_share < 0:
            raise ValueError("Cost basis cannot be negative")
        if purchase_date > date.today():
            raise ValueError("Purchase date cannot be in the future")

        portfolio = await self.get_or_create_portfolio()
        if account_id is None:
            account_id = portfolio.accounts[0].id if portfolio.accounts else None
            if account_id is None:
                account = await self._portfolio_repo.create_account(
                    portfolio.id, "Default Brokerage", "brokerage"
                )
                account_id = account.id

        holding = Holding(
            account_id=account_id,
            ticker=ticker,
            asset_class=asset_class,
            quantity=Decimal(str(quantity)),
            cost_basis_per_share=Decimal(str(cost_basis_per_share)),
            purchase_date=purchase_date,
            notes=notes,
        )
        return await self._holding_repo.add_holding(holding)

    async def add_transaction(
        self,
        account_id: uuid.UUID,
        ticker: str,
        transaction_type: str,
        quantity: float,
        price_per_share: float,
        transaction_date: date,
        fees: float = 0.0,
        notes: Optional[str] = None,
    ) -> Transaction:
        """Record a transaction (buy, sell, dividend, etc.)."""
        transaction = Transaction(
            account_id=account_id,
            ticker=ticker.upper().strip(),
            transaction_type=transaction_type,
            quantity=Decimal(str(quantity)),
            price_per_share=Decimal(str(price_per_share)),
            fees=Decimal(str(fees)),
            transaction_date=transaction_date,
            notes=notes,
        )
        return await self._transaction_repo.add_transaction(transaction)

    async def list_accounts(self) -> list[Account]:
        """List all active accounts."""
        portfolio = await self.get_or_create_portfolio()
        return [a for a in portfolio.accounts if a.is_active]

    async def create_account(
        self, name: str, account_type: str, currency: str = "USD"
    ) -> Account:
        """Create a new investment account."""
        portfolio = await self.get_or_create_portfolio()
        return await self._portfolio_repo.create_account(
            portfolio.id, name, account_type, currency
        )

    def get_all_tickers(self, portfolio: Portfolio) -> list[str]:
        """Extract all unique open tickers from the portfolio."""
        tickers: set[str] = set()
        for account in portfolio.accounts:
            for holding in account.holdings:
                if holding.is_open:
                    tickers.add(holding.ticker)
        return sorted(tickers)
