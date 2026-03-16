"""Unit tests for core domain models.

Tests computed properties, validation, and business rules.
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from finapp.domain.models.holding import Holding, TaxLot
from finapp.domain.models.transaction import Transaction


class TestHolding:
    def _make_holding(self, **kwargs) -> Holding:
        defaults = {
            "account_id": uuid.uuid4(),
            "ticker": "AAPL",
            "asset_class": "equity",
            "quantity": Decimal("10"),
            "cost_basis_per_share": Decimal("100.00"),
            "purchase_date": date(2023, 1, 1),
            "current_price": Decimal("150.00"),
        }
        defaults.update(kwargs)
        return Holding(**defaults)

    def test_total_cost_basis(self) -> None:
        h = self._make_holding(quantity=Decimal("10"), cost_basis_per_share=Decimal("100"))
        assert h.total_cost_basis == Decimal("1000")

    def test_current_value(self) -> None:
        h = self._make_holding(quantity=Decimal("10"), current_price=Decimal("150"))
        assert h.current_value == Decimal("1500")

    def test_gain_loss_dollars(self) -> None:
        h = self._make_holding(
            quantity=Decimal("10"),
            cost_basis_per_share=Decimal("100"),
            current_price=Decimal("150"),
        )
        assert h.gain_loss_dollars == Decimal("500")

    def test_gain_loss_pct(self) -> None:
        h = self._make_holding(
            quantity=Decimal("10"),
            cost_basis_per_share=Decimal("100"),
            current_price=Decimal("150"),
        )
        assert h.gain_loss_pct == Decimal("50")

    def test_zero_cost_basis_gain_loss_pct_is_zero(self) -> None:
        h = self._make_holding(cost_basis_per_share=Decimal("0"), current_price=Decimal("100"))
        assert h.gain_loss_pct == Decimal("0")

    def test_holding_period_days(self) -> None:
        purchase = date.today() - timedelta(days=400)
        h = self._make_holding(purchase_date=purchase)
        assert h.holding_period_days == 400

    def test_is_long_term_true_after_365_days(self) -> None:
        purchase = date.today() - timedelta(days=366)
        h = self._make_holding(purchase_date=purchase)
        assert h.is_long_term is True

    def test_is_long_term_false_before_365_days(self) -> None:
        purchase = date.today() - timedelta(days=364)
        h = self._make_holding(purchase_date=purchase)
        assert h.is_long_term is False

    def test_ticker_max_length(self) -> None:
        with pytest.raises(Exception):
            self._make_holding(ticker="TOOLONGTICKER")


class TestTransaction:
    def _make_buy(self, **kwargs) -> Transaction:
        defaults = {
            "account_id": uuid.uuid4(),
            "ticker": "AAPL",
            "transaction_type": "buy",
            "quantity": Decimal("10"),
            "price_per_share": Decimal("150.00"),
            "fees": Decimal("0"),
            "transaction_date": date.today(),
        }
        defaults.update(kwargs)
        return Transaction(**defaults)

    def test_buy_quantity_is_positive(self) -> None:
        t = self._make_buy(quantity=Decimal("10"))
        assert t.quantity > 0

    def test_sell_quantity_becomes_negative(self) -> None:
        t = Transaction(
            account_id=uuid.uuid4(),
            ticker="AAPL",
            transaction_type="sell",
            quantity=Decimal("5"),  # Positive input
            price_per_share=Decimal("150"),
            fees=Decimal("0"),
            transaction_date=date.today(),
        )
        assert t.quantity < 0

    def test_total_amount_includes_fees(self) -> None:
        t = self._make_buy(quantity=Decimal("10"), price_per_share=Decimal("100"), fees=Decimal("5"))
        # total = abs(10) * 100 + 5 = 1005
        assert t.total_amount == Decimal("1005")

    def test_transaction_is_immutable(self) -> None:
        """Transactions are frozen — mutation should raise."""
        t = self._make_buy()
        with pytest.raises(Exception):
            t.ticker = "MSFT"  # type: ignore[misc]

    def test_ticker_stored_correctly(self) -> None:
        t = self._make_buy(ticker="AAPL")
        assert t.ticker == "AAPL"
