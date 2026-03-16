"""Risk Service — orchestrates risk calculations for the application layer."""

import logging
from decimal import Decimal
from typing import Any

from finapp.app.services.market_data_service import MarketDataService
from finapp.domain.models.market import RiskMetrics
from finapp.domain.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


class RiskService:
    """Application-layer orchestrator for portfolio risk analysis."""

    def __init__(self) -> None:
        self._market_service = MarketDataService()

    async def calculate_portfolio_risk(
        self,
        portfolio: Portfolio,
        period: str = "1y",
    ) -> RiskMetrics:
        """Calculate comprehensive risk metrics for the full portfolio.

        Fetches historical returns for each holding, weights them by portfolio
        allocation, then computes VaR, Sharpe, beta, and drawdown.

        Args:
            portfolio: Priced portfolio (current_price set on all holdings).
            period: Historical period for return calculation.

        Returns:
            RiskMetrics domain model.
        """
        total_value = float(portfolio.total_value)
        if total_value == 0:
            return RiskMetrics(
                var_95_1d_pct=Decimal(0),
                var_95_1d_dollars=Decimal(0),
                var_99_1d_pct=Decimal(0),
                var_99_1d_dollars=Decimal(0),
            )

        # Collect weighted return series for each holding
        all_tickers = []
        weights: dict[str, float] = {}
        for account in portfolio.accounts:
            for holding in account.holdings:
                if holding.is_open and float(holding.current_value) > 0:
                    all_tickers.append(holding.ticker)
                    weights[holding.ticker] = float(holding.current_value) / total_value

        if not all_tickers:
            return RiskMetrics(
                var_95_1d_pct=Decimal(0),
                var_95_1d_dollars=Decimal(0),
                var_99_1d_pct=Decimal(0),
                var_99_1d_dollars=Decimal(0),
            )

        # Fetch returns and compute portfolio-level weighted returns
        ticker_returns: dict[str, list[float]] = {}
        for ticker in all_tickers:
            try:
                returns = await self._market_service.get_daily_returns(ticker, period)
                if returns:
                    ticker_returns[ticker] = returns
            except Exception as exc:
                logger.warning("Could not fetch returns for %s: %s", ticker, exc)

        if not ticker_returns:
            return RiskMetrics(
                var_95_1d_pct=Decimal(0),
                var_95_1d_dollars=Decimal(0),
                var_99_1d_pct=Decimal(0),
                var_99_1d_dollars=Decimal(0),
            )

        # Align return series to common length
        min_len = min(len(r) for r in ticker_returns.values())
        portfolio_returns = [
            sum(
                ticker_returns[t][i] * weights.get(t, 0)
                for t in ticker_returns
            )
            for i in range(min_len)
        ]

        from finapp.domain.calculators.risk_calculator import calculate_sharpe, calculate_var

        var_95 = calculate_var(portfolio_returns, 0.95, 1, total_value)
        var_99 = calculate_var(portfolio_returns, 0.99, 1, total_value)
        sharpe_data = calculate_sharpe(portfolio_returns)

        return RiskMetrics(
            var_95_1d_pct=Decimal(str(var_95["var_pct"])),
            var_95_1d_dollars=Decimal(str(var_95["var_dollars"])),
            var_99_1d_pct=Decimal(str(var_99["var_pct"])),
            var_99_1d_dollars=Decimal(str(var_99["var_dollars"])),
            sharpe_ratio=Decimal(str(sharpe_data["sharpe_ratio"])),
            sortino_ratio=Decimal(str(sharpe_data["sortino_ratio"])),
            max_drawdown_pct=Decimal(str(sharpe_data["max_drawdown"])),
            volatility_annualized=Decimal(str(sharpe_data["annualized_volatility"])),
        )

    async def run_stress_test(
        self,
        portfolio: Portfolio,
        scenario: str,
        custom_shock_pct: float | None = None,
    ) -> dict[str, Any]:
        """Run a historical scenario stress test on the portfolio.

        Args:
            portfolio: Portfolio with current_price set on holdings.
            scenario: Scenario name from STRESS_SCENARIOS or "custom".
            custom_shock_pct: Custom shock percentage (e.g., -0.30).

        Returns:
            Stress test result dict.
        """
        total_value = float(portfolio.total_value)
        holdings_input = []
        for account in portfolio.accounts:
            for holding in account.holdings:
                if holding.is_open and float(holding.current_value) > 0:
                    holdings_input.append({
                        "ticker": holding.ticker,
                        "weight": float(holding.current_value) / total_value,
                        "asset_class": holding.asset_class,
                    })

        from finapp.domain.calculators.risk_calculator import run_stress_test
        return run_stress_test(holdings_input, scenario, total_value, custom_shock_pct)

    async def get_correlation_matrix(
        self,
        tickers: list[str],
        period: str = "1y",
    ) -> dict[str, dict[str, float]]:
        """Calculate pairwise correlation matrix for a set of tickers."""
        returns_by_ticker: dict[str, list[float]] = {}
        for ticker in tickers:
            try:
                returns = await self._market_service.get_daily_returns(ticker, period)
                if len(returns) >= 20:
                    returns_by_ticker[ticker] = returns
            except Exception as exc:
                logger.warning("Could not get returns for %s: %s", ticker, exc)

        if len(returns_by_ticker) < 2:
            return {}

        from finapp.domain.calculators.risk_calculator import calculate_correlation_matrix
        # Trim to common length
        min_len = min(len(r) for r in returns_by_ticker.values())
        trimmed = {t: r[:min_len] for t, r in returns_by_ticker.items()}
        return calculate_correlation_matrix(trimmed)
