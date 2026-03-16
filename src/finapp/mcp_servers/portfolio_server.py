"""Portfolio Data MCP Server — MCP-003.

Provides CRUD operations for portfolio data, holdings, and transactions.
GRD-ARCH-002: All data access goes through repository classes.
GRD-SEC-005: This server only exposes portfolio data to agents when explicitly invoked.
"""

import asyncio
import logging
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from mcp.server import FastMCP

from finapp.config import settings
from finapp.domain.models.holding import Holding
from finapp.domain.models.transaction import Transaction
from finapp.infrastructure.database import create_all_tables
from finapp.infrastructure.repositories.portfolio_repository import (
    HoldingRepository,
    PortfolioRepository,
    TransactionRepository,
)

logger = logging.getLogger(__name__)
mcp = FastMCP("portfolio-mcp")

_portfolio_repo = PortfolioRepository()
_holding_repo = HoldingRepository()
_transaction_repo = TransactionRepository()

# Default user ID for single-user local app
DEFAULT_USER_ID = "local_user"


@mcp.tool()
async def get_portfolio(
    account_id: Optional[str] = None,
    include_closed: bool = False,
) -> dict[str, Any]:
    """Get complete portfolio data including all holdings.

    Args:
        account_id: Filter to a specific account (optional).
        include_closed: Include fully-sold positions.

    Returns:
        Portfolio summary with accounts, holdings, values, and gain/loss.
    """
    portfolio = await _portfolio_repo.get_portfolio(DEFAULT_USER_ID)
    if portfolio is None:
        portfolio = await _portfolio_repo.create_portfolio(DEFAULT_USER_ID)

    # Serialize to dict
    accounts_data = []
    for account in portfolio.accounts:
        if account_id and str(account.id) != account_id:
            continue
        if not account.is_active:
            continue
        holdings_data = []
        for h in account.holdings:
            if not include_closed and not h.is_open:
                continue
            holdings_data.append({
                "holding_id": str(h.id),
                "ticker": h.ticker,
                "asset_class": h.asset_class,
                "quantity": float(h.quantity),
                "cost_basis_per_share": float(h.cost_basis_per_share),
                "total_cost_basis": float(h.total_cost_basis),
                "purchase_date": str(h.purchase_date),
                "holding_period_days": h.holding_period_days,
                "is_long_term": h.is_long_term,
                "is_open": h.is_open,
                "notes": h.notes,
            })
        accounts_data.append({
            "account_id": str(account.id),
            "name": account.name,
            "account_type": account.account_type,
            "currency": account.currency,
            "holdings": holdings_data,
            "holdings_count": len(holdings_data),
        })

    return {
        "portfolio_id": str(portfolio.id),
        "user_id": portfolio.user_id,
        "accounts": accounts_data,
        "total_cost_basis": float(portfolio.total_cost_basis),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
async def add_holding(
    ticker: str,
    quantity: float,
    cost_basis_per_share: float,
    purchase_date: str,
    account_id: Optional[str] = None,
    asset_class: str = "equity",
    notes: Optional[str] = None,
) -> dict[str, Any]:
    """Add a new holding to the portfolio.

    Args:
        ticker: Exchange ticker symbol (e.g., "AAPL").
        quantity: Number of shares (supports fractional).
        cost_basis_per_share: Average cost basis per share in USD.
        purchase_date: ISO 8601 date (e.g., "2024-01-15").
        account_id: Target account ID. Creates default account if not provided.
        asset_class: equity|etf|mutual_fund|bond|crypto|cash|reit|commodity|other.
        notes: Optional notes for this holding.

    Returns:
        Dict with holding_id and success flag.
    """
    # GRD-SEC-003: Validate inputs
    ticker = ticker.upper().strip()
    if not ticker or len(ticker) > 10:
        return {"success": False, "error": "Invalid ticker symbol"}
    if quantity <= 0 or quantity > 1_000_000_000:
        return {"success": False, "error": "Quantity must be between 0 and 1,000,000,000"}
    if cost_basis_per_share < 0:
        return {"success": False, "error": "Cost basis cannot be negative"}

    try:
        purchase_dt = date.fromisoformat(purchase_date)
    except ValueError:
        return {"success": False, "error": f"Invalid date format: {purchase_date}"}
    if purchase_dt > date.today():
        return {"success": False, "error": "Purchase date cannot be in the future"}

    # Ensure portfolio + account exist
    portfolio = await _portfolio_repo.get_portfolio(DEFAULT_USER_ID)
    if portfolio is None:
        portfolio = await _portfolio_repo.create_portfolio(DEFAULT_USER_ID)

    target_account = None
    if account_id:
        target_account = await _portfolio_repo.get_account(uuid.UUID(account_id))
    if target_account is None:
        # Use first active account or create default
        if portfolio.accounts:
            target_account = portfolio.accounts[0]
        else:
            target_account = await _portfolio_repo.create_account(
                portfolio.id, "Default Account", "brokerage"
            )

    holding = Holding(
        account_id=target_account.id,
        ticker=ticker,
        asset_class=asset_class,
        quantity=Decimal(str(quantity)),
        cost_basis_per_share=Decimal(str(cost_basis_per_share)),
        purchase_date=purchase_dt,
        notes=notes,
    )
    saved = await _holding_repo.add_holding(holding)
    return {"holding_id": str(saved.id), "success": True}


@mcp.tool()
async def update_holding(
    holding_id: str,
    quantity: Optional[float] = None,
    notes: Optional[str] = None,
) -> dict[str, Any]:
    """Update quantity or notes for an existing holding.

    Args:
        holding_id: UUID of the holding to update.
        quantity: New quantity (optional).
        notes: New notes (optional).

    Returns:
        Dict with success flag.
    """
    try:
        hid = uuid.UUID(holding_id)
    except ValueError:
        return {"success": False, "error": "Invalid holding_id format"}

    result = await _holding_repo.update_holding(hid, quantity, notes)
    if result is None:
        return {"success": False, "error": "Holding not found"}
    return {"success": True, "holding_id": holding_id}


@mcp.tool()
async def get_performance(
    period: str = "ytd",
    account_id: Optional[str] = None,
    benchmark: str = "SPY",
) -> dict[str, Any]:
    """Get portfolio performance metrics for a given period.

    Args:
        period: 1d|1w|1m|3m|6m|ytd|1y|all
        account_id: Filter to specific account (optional).
        benchmark: Benchmark ticker to compare against (default: SPY).

    Returns:
        Performance metrics including return, alpha, Sharpe, drawdown.

    Note: This is a simplified implementation. Full TWR requires daily
    portfolio snapshots which are not yet persisted in v0.1.
    """
    portfolio = await _portfolio_repo.get_portfolio(DEFAULT_USER_ID)
    if portfolio is None:
        return {"error": "No portfolio found"}

    # Compute cost basis vs current value ratio as a simplified return
    total_cost = float(portfolio.total_cost_basis)
    # Without live prices injected, we can only report cost-basis data
    return {
        "period": period,
        "benchmark": benchmark,
        "total_cost_basis": total_cost,
        "note": (
            "Live return calculation requires market prices. "
            "Use get_quote tool to fetch current prices and compute gain/loss."
        ),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
async def get_transactions(
    account_id: Optional[str] = None,
    ticker: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    transaction_types: Optional[list[str]] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Retrieve transaction history with optional filtering.

    Args:
        account_id: Filter by account ID (optional).
        ticker: Filter by ticker symbol (optional).
        from_date: Start date ISO format (optional).
        to_date: End date ISO format (optional).
        transaction_types: Filter by types: buy|sell|dividend|transfer_in|transfer_out|split.
        limit: Maximum records to return (default 100).

    Returns:
        List of transaction dicts.
    """
    aid = uuid.UUID(account_id) if account_id else None
    fd = date.fromisoformat(from_date) if from_date else None
    td = date.fromisoformat(to_date) if to_date else None

    transactions = await _transaction_repo.list_transactions(
        account_id=aid,
        ticker=ticker,
        from_date=fd,
        to_date=td,
        transaction_types=transaction_types,
        limit=limit,
    )
    return [
        {
            "transaction_id": str(t.id),
            "date": str(t.transaction_date),
            "type": t.transaction_type,
            "ticker": t.ticker,
            "quantity": float(t.quantity),
            "price": float(t.price_per_share),
            "total": float(t.total_amount),
            "fees": float(t.fees),
            "account_id": str(t.account_id),
            "notes": t.notes,
        }
        for t in transactions
    ]


if __name__ == "__main__":
    asyncio.run(create_all_tables())
    mcp.run(transport="stdio")
