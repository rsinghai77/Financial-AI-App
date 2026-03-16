"""SQLAlchemy implementation of IPortfolioRepository and IHoldingRepository.

GRD-ARCH-002: This is the ONLY place that touches SQLAlchemy sessions for portfolio data.
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from finapp.domain.models.account import Account
from finapp.domain.models.holding import Holding, TaxLot
from finapp.domain.models.portfolio import Portfolio
from finapp.domain.models.transaction import Transaction
from finapp.domain.repositories.interfaces import (
    IHoldingRepository,
    IPortfolioRepository,
    ITransactionRepository,
)
from finapp.infrastructure.database import get_session
from finapp.infrastructure.orm_models import (
    AccountORM,
    HoldingORM,
    PortfolioORM,
    TaxLotORM,
    TransactionORM,
)


def _holding_orm_to_domain(orm: HoldingORM) -> Holding:
    """Convert HoldingORM to domain Holding model."""
    tax_lots = [
        TaxLot(
            id=uuid.UUID(lot.id),
            holding_id=uuid.UUID(lot.holding_id),
            quantity=Decimal(str(lot.quantity)),
            cost_basis_per_share=Decimal(str(lot.cost_basis_per_share)),
            purchase_date=lot.purchase_date,
            transaction_id=uuid.UUID(lot.transaction_id) if lot.transaction_id else None,
        )
        for lot in (orm.tax_lots or [])
    ]
    return Holding(
        id=uuid.UUID(orm.id),
        account_id=uuid.UUID(orm.account_id),
        ticker=orm.ticker,
        asset_class=orm.asset_class,
        quantity=Decimal(str(orm.quantity)),
        cost_basis_per_share=Decimal(str(orm.cost_basis_per_share)),
        purchase_date=orm.purchase_date,
        notes=orm.notes,
        created_at=orm.created_at,
        is_open=orm.is_open,
        tax_lots=tax_lots,
    )


def _account_orm_to_domain(orm: AccountORM) -> Account:
    """Convert AccountORM to domain Account model."""
    holdings = [_holding_orm_to_domain(h) for h in (orm.holdings or [])]
    return Account(
        id=uuid.UUID(orm.id),
        portfolio_id=uuid.UUID(orm.portfolio_id),
        name=orm.name,
        account_type=orm.account_type,
        currency=orm.currency,
        holdings=holdings,
        created_at=orm.created_at,
        is_active=orm.is_active,
        notes=orm.notes,
    )


class PortfolioRepository(IPortfolioRepository):
    """Concrete SQLAlchemy implementation of IPortfolioRepository."""

    async def get_portfolio(self, user_id: str) -> Optional[Portfolio]:
        """Fetch the portfolio for a user, eagerly loading all accounts and holdings."""
        async with get_session() as session:
            stmt = (
                select(PortfolioORM)
                .where(PortfolioORM.user_id == user_id)
                .options(
                    selectinload(PortfolioORM.accounts).selectinload(AccountORM.holdings)
                    .selectinload(HoldingORM.tax_lots)
                )
            )
            result = await session.execute(stmt)
            orm = result.scalars().first()
            if orm is None:
                return None
            accounts = [_account_orm_to_domain(a) for a in (orm.accounts or [])]
            return Portfolio(
                id=uuid.UUID(orm.id),
                user_id=orm.user_id,
                accounts=accounts,
                created_at=orm.created_at,
                updated_at=orm.updated_at,
            )

    async def create_portfolio(self, user_id: str) -> Portfolio:
        """Create a new portfolio for a user."""
        async with get_session() as session:
            orm = PortfolioORM(user_id=user_id)
            session.add(orm)
            await session.flush()
            return Portfolio(
                id=uuid.UUID(orm.id),
                user_id=orm.user_id,
                accounts=[],
                created_at=orm.created_at,
                updated_at=orm.updated_at,
            )

    async def get_account(self, account_id: uuid.UUID) -> Optional[Account]:
        async with get_session() as session:
            stmt = (
                select(AccountORM)
                .where(AccountORM.id == str(account_id))
                .options(selectinload(AccountORM.holdings).selectinload(HoldingORM.tax_lots))
            )
            result = await session.execute(stmt)
            orm = result.scalars().first()
            return _account_orm_to_domain(orm) if orm else None

    async def create_account(
        self,
        portfolio_id: uuid.UUID,
        name: str,
        account_type: str,
        currency: str = "USD",
    ) -> Account:
        async with get_session() as session:
            orm = AccountORM(
                portfolio_id=str(portfolio_id),
                name=name,
                account_type=account_type,
                currency=currency,
            )
            session.add(orm)
            await session.flush()
            return _account_orm_to_domain(orm)

    async def list_accounts(self, portfolio_id: uuid.UUID) -> list[Account]:
        async with get_session() as session:
            stmt = (
                select(AccountORM)
                .where(AccountORM.portfolio_id == str(portfolio_id), AccountORM.is_active.is_(True))
                .options(selectinload(AccountORM.holdings))
            )
            result = await session.execute(stmt)
            return [_account_orm_to_domain(a) for a in result.scalars().all()]


class HoldingRepository(IHoldingRepository):
    """Concrete SQLAlchemy implementation of IHoldingRepository."""

    async def get_holding(self, holding_id: uuid.UUID) -> Optional[Holding]:
        async with get_session() as session:
            stmt = (
                select(HoldingORM)
                .where(HoldingORM.id == str(holding_id))
                .options(selectinload(HoldingORM.tax_lots))
            )
            result = await session.execute(stmt)
            orm = result.scalars().first()
            return _holding_orm_to_domain(orm) if orm else None

    async def list_holdings(
        self, account_id: uuid.UUID, include_closed: bool = False
    ) -> list[Holding]:
        async with get_session() as session:
            stmt = select(HoldingORM).where(HoldingORM.account_id == str(account_id))
            if not include_closed:
                stmt = stmt.where(HoldingORM.is_open.is_(True))
            stmt = stmt.options(selectinload(HoldingORM.tax_lots))
            result = await session.execute(stmt)
            return [_holding_orm_to_domain(h) for h in result.scalars().all()]

    async def add_holding(self, holding: Holding) -> Holding:
        async with get_session() as session:
            orm = HoldingORM(
                id=str(holding.id),
                account_id=str(holding.account_id),
                ticker=holding.ticker.upper(),
                asset_class=holding.asset_class,
                quantity=holding.quantity,
                cost_basis_per_share=holding.cost_basis_per_share,
                purchase_date=holding.purchase_date,
                notes=holding.notes,
                is_open=holding.is_open,
            )
            session.add(orm)
            await session.flush()
            return holding

    async def update_holding(
        self,
        holding_id: uuid.UUID,
        quantity: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Optional[Holding]:
        async with get_session() as session:
            result = await session.execute(
                select(HoldingORM).where(HoldingORM.id == str(holding_id))
            )
            orm = result.scalars().first()
            if orm is None:
                return None
            if quantity is not None:
                orm.quantity = Decimal(str(quantity))
            if notes is not None:
                orm.notes = notes
            await session.flush()
            return _holding_orm_to_domain(orm)

    async def close_holding(self, holding_id: uuid.UUID) -> None:
        async with get_session() as session:
            result = await session.execute(
                select(HoldingORM).where(HoldingORM.id == str(holding_id))
            )
            orm = result.scalars().first()
            if orm:
                orm.is_open = False

    async def add_tax_lot(self, tax_lot: TaxLot) -> TaxLot:
        async with get_session() as session:
            orm = TaxLotORM(
                id=str(tax_lot.id),
                holding_id=str(tax_lot.holding_id),
                transaction_id=str(tax_lot.transaction_id) if tax_lot.transaction_id else None,
                quantity=tax_lot.quantity,
                cost_basis_per_share=tax_lot.cost_basis_per_share,
                purchase_date=tax_lot.purchase_date,
            )
            session.add(orm)
            return tax_lot


class TransactionRepository(ITransactionRepository):
    """Concrete SQLAlchemy implementation of ITransactionRepository."""

    async def add_transaction(self, transaction: Transaction) -> Transaction:
        """Append a new transaction — immutable after creation per GRD-ARCH."""
        async with get_session() as session:
            orm = TransactionORM(
                id=str(transaction.id),
                account_id=str(transaction.account_id),
                ticker=transaction.ticker.upper(),
                transaction_type=transaction.transaction_type,
                quantity=transaction.quantity,
                price_per_share=transaction.price_per_share,
                fees=transaction.fees,
                transaction_date=transaction.transaction_date,
                settlement_date=transaction.settlement_date,
                notes=transaction.notes,
            )
            session.add(orm)
            return transaction

    async def list_transactions(
        self,
        account_id: Optional[uuid.UUID] = None,
        ticker: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        transaction_types: Optional[list[str]] = None,
        limit: int = 100,
    ) -> list[Transaction]:
        async with get_session() as session:
            stmt = select(TransactionORM)
            if account_id:
                stmt = stmt.where(TransactionORM.account_id == str(account_id))
            if ticker:
                stmt = stmt.where(TransactionORM.ticker == ticker.upper())
            if from_date:
                stmt = stmt.where(TransactionORM.transaction_date >= from_date)
            if to_date:
                stmt = stmt.where(TransactionORM.transaction_date <= to_date)
            if transaction_types:
                stmt = stmt.where(TransactionORM.transaction_type.in_(transaction_types))
            stmt = stmt.order_by(TransactionORM.transaction_date.desc()).limit(limit)

            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                Transaction(
                    id=uuid.UUID(r.id),
                    account_id=uuid.UUID(r.account_id),
                    ticker=r.ticker,
                    transaction_type=r.transaction_type,
                    quantity=Decimal(str(r.quantity)),
                    price_per_share=Decimal(str(r.price_per_share)),
                    fees=Decimal(str(r.fees)),
                    transaction_date=r.transaction_date,
                    settlement_date=r.settlement_date,
                    notes=r.notes,
                    created_at=r.created_at,
                )
                for r in rows
            ]
