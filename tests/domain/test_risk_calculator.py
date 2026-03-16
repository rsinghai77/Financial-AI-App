"""Unit tests for domain/calculators/risk_calculator.py.

GRD-CQ-004: Every public function in domain/calculators/ must have tests.
Tests include edge cases: empty portfolio, single holding, zero-risk asset.
"""

import math

import numpy as np
import pytest

from finapp.domain.calculators.risk_calculator import (
    STRESS_SCENARIOS,
    calculate_correlation_matrix,
    calculate_portfolio_beta,
    calculate_sharpe,
    calculate_var,
    run_stress_test,
)

# ---------------------------------------------------------------------------
# calculate_var
# ---------------------------------------------------------------------------

class TestCalculateVar:
    def test_basic_var_returns_expected_shape(self) -> None:
        returns = [0.01, -0.02, 0.005, -0.015, 0.008] * 50  # 250 data points
        result = calculate_var(returns, 0.95, 1, 100_000.0)
        assert "var_pct" in result
        assert "var_dollars" in result
        assert "confidence_level" in result
        assert "method" in result
        assert result["confidence_level"] == 0.95

    def test_var_is_non_negative(self) -> None:
        """VaR should always be non-negative (it represents a potential loss)."""
        returns = list(np.random.default_rng(42).normal(0.001, 0.02, 500))
        result = calculate_var(returns, 0.95, 1, 100_000.0)
        assert result["var_pct"] >= 0.0

    def test_risk_free_asset_var_is_near_zero(self) -> None:
        """A return series of all zeros should have VaR ≈ 0."""
        returns = [0.0] * 252
        result = calculate_var(returns, 0.95, 1, 100_000.0)
        assert abs(result["var_pct"]) < 1e-9

    def test_var_99_greater_than_var_95(self) -> None:
        """99% VaR must be >= 95% VaR (higher confidence = larger loss estimate)."""
        rng = np.random.default_rng(7)
        returns = list(rng.normal(0.0, 0.02, 500))
        var_95 = calculate_var(returns, 0.95, 1, 100_000.0)["var_pct"]
        var_99 = calculate_var(returns, 0.99, 1, 100_000.0)["var_pct"]
        assert var_99 >= var_95

    def test_var_scales_with_portfolio_value(self) -> None:
        """VaR in dollars should scale linearly with portfolio value."""
        returns = list(np.random.default_rng(1).normal(0.001, 0.02, 300))
        result_100k = calculate_var(returns, 0.95, 1, 100_000.0)
        result_200k = calculate_var(returns, 0.95, 1, 200_000.0)
        ratio = result_200k["var_dollars"] / result_100k["var_dollars"]
        assert abs(ratio - 2.0) < 1e-6

    def test_var_holding_period_scaling(self) -> None:
        """5-day VaR must be >= 1-day VaR (sqrt-of-time rule)."""
        returns = list(np.random.default_rng(2).normal(0.001, 0.02, 300))
        var_1d = calculate_var(returns, 0.95, 1, 100_000.0)["var_pct"]
        var_5d = calculate_var(returns, 0.95, 5, 100_000.0)["var_pct"]
        assert var_5d >= var_1d

    def test_empty_returns_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            calculate_var([], 0.95, 1, 100_000.0)

    def test_invalid_confidence_raises(self) -> None:
        with pytest.raises(ValueError, match="confidence_level"):
            calculate_var([0.01, -0.02], 1.5, 1, 100_000.0)


# ---------------------------------------------------------------------------
# calculate_sharpe
# ---------------------------------------------------------------------------

class TestCalculateSharpe:
    def test_returns_all_required_keys(self) -> None:
        returns = list(np.random.default_rng(3).normal(0.001, 0.02, 252))
        result = calculate_sharpe(returns)
        for key in ("sharpe_ratio", "sortino_ratio", "annualized_return", "annualized_volatility", "max_drawdown"):
            assert key in result

    def test_positive_return_series_has_positive_sharpe(self) -> None:
        # Monotonically positive returns (every day +0.1%)
        returns = [0.001] * 252
        result = calculate_sharpe(returns, risk_free_rate_annual=0.0)
        assert result["sharpe_ratio"] > 0

    def test_all_negative_returns_has_negative_sharpe(self) -> None:
        returns = [-0.001] * 252
        result = calculate_sharpe(returns, risk_free_rate_annual=0.0)
        assert result["sharpe_ratio"] < 0

    def test_max_drawdown_non_positive(self) -> None:
        """Max drawdown should always be ≤ 0 (it's a loss)."""
        rng = np.random.default_rng(10)
        returns = list(rng.normal(0.001, 0.02, 252))
        result = calculate_sharpe(returns)
        assert result["max_drawdown"] <= 0.0

    def test_insufficient_data_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            calculate_sharpe([0.01])

    def test_annualized_volatility_non_negative(self) -> None:
        rng = np.random.default_rng(11)
        returns = list(rng.normal(0, 0.02, 252))
        result = calculate_sharpe(returns)
        assert result["annualized_volatility"] >= 0.0


# ---------------------------------------------------------------------------
# calculate_portfolio_beta
# ---------------------------------------------------------------------------

class TestCalculatePortfolioBeta:
    def test_identical_series_has_beta_one(self) -> None:
        """A portfolio that is identical to the benchmark should have beta ≈ 1."""
        rng = np.random.default_rng(20)
        market = list(rng.normal(0.001, 0.015, 252))
        beta = calculate_portfolio_beta(market, market)
        assert abs(beta - 1.0) < 1e-6

    def test_zero_correlation_near_zero_beta(self) -> None:
        """Orthogonal (uncorrelated) series should have beta near 0."""
        n = 500
        rng = np.random.default_rng(21)
        market = list(rng.normal(0, 0.01, n))
        portfolio = list(rng.normal(0, 0.01, n))  # Independent — should have ~0 beta
        beta = calculate_portfolio_beta(portfolio, market)
        assert abs(beta) < 0.3  # Loose bound due to randomness

    def test_mismatched_lengths_raises(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            calculate_portfolio_beta([0.01, 0.02], [0.01])

    def test_insufficient_data_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            calculate_portfolio_beta([0.01], [0.01])


# ---------------------------------------------------------------------------
# calculate_correlation_matrix
# ---------------------------------------------------------------------------

class TestCalculateCorrelationMatrix:
    def test_self_correlation_is_one(self) -> None:
        """Each asset should have perfect correlation with itself."""
        rng = np.random.default_rng(30)
        series = list(rng.normal(0, 0.02, 252))
        result = calculate_correlation_matrix({"AAPL": series, "MSFT": series})
        assert abs(result["AAPL"]["AAPL"] - 1.0) < 1e-6
        assert abs(result["MSFT"]["MSFT"] - 1.0) < 1e-6

    def test_correlation_bounds(self) -> None:
        """All correlations must be in [-1, 1]."""
        rng = np.random.default_rng(31)
        data = {f"T{i}": list(rng.normal(0, 0.02, 252)) for i in range(5)}
        result = calculate_correlation_matrix(data)
        for row in result.values():
            for v in row.values():
                assert -1.0 <= v <= 1.0

    def test_symmetry(self) -> None:
        """Correlation matrix must be symmetric: corr(A, B) == corr(B, A)."""
        rng = np.random.default_rng(32)
        data = {"X": list(rng.normal(0, 0.02, 252)), "Y": list(rng.normal(0, 0.02, 252))}
        result = calculate_correlation_matrix(data)
        assert abs(result["X"]["Y"] - result["Y"]["X"]) < 1e-10

    def test_single_ticker_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            calculate_correlation_matrix({"AAPL": [0.01, -0.02, 0.005]})

    def test_unequal_lengths_raises(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            calculate_correlation_matrix({"A": [0.01, 0.02], "B": [0.01]})


# ---------------------------------------------------------------------------
# run_stress_test
# ---------------------------------------------------------------------------

class TestRunStressTest:
    HOLDINGS = [
        {"ticker": "AAPL", "weight": 0.5, "asset_class": "equity"},
        {"ticker": "TLT", "weight": 0.3, "asset_class": "bond"},
        {"ticker": "GLD", "weight": 0.2, "asset_class": "commodity"},
    ]

    def test_weights_sum_approximately_one(self) -> None:
        """Test holdings with weights summing to 1.0."""
        total = sum(h["weight"] for h in self.HOLDINGS)
        assert abs(total - 1.0) < 1e-10

    def test_known_scenario_returns_expected_structure(self) -> None:
        result = run_stress_test(self.HOLDINGS, "2008_financial_crisis", 100_000.0)
        assert "scenario" in result
        assert "portfolio_loss_pct" in result
        assert "portfolio_loss_dollars" in result
        assert "worst_holding" in result
        assert "estimated_recovery_years" in result

    def test_loss_is_negative(self) -> None:
        """Portfolio loss should be negative in a crash scenario."""
        result = run_stress_test(self.HOLDINGS, "2008_financial_crisis", 100_000.0)
        assert result["portfolio_loss_pct"] < 0

    def test_dollar_loss_consistent_with_portfolio_value(self) -> None:
        result = run_stress_test(self.HOLDINGS, "2020_covid_crash", 200_000.0)
        expected_dollars = result["portfolio_loss_pct"] * 200_000.0
        assert abs(result["portfolio_loss_dollars"] - expected_dollars) < 0.01

    def test_all_named_scenarios_work(self) -> None:
        for scenario in STRESS_SCENARIOS:
            result = run_stress_test(self.HOLDINGS, scenario, 50_000.0)
            assert result["scenario"] == scenario

    def test_custom_scenario_uses_custom_shock(self) -> None:
        result = run_stress_test(self.HOLDINGS, "custom", 100_000.0, custom_shock_pct=-0.50)
        # All holdings get -50% shock, so portfolio loss ≈ -50%
        assert result["portfolio_loss_pct"] < -0.45

    def test_custom_scenario_without_shock_raises(self) -> None:
        with pytest.raises(ValueError, match="custom_shock_pct"):
            run_stress_test(self.HOLDINGS, "custom", 100_000.0)

    def test_unknown_scenario_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown scenario"):
            run_stress_test(self.HOLDINGS, "great_depression", 100_000.0)

    def test_recovery_years_non_negative(self) -> None:
        result = run_stress_test(self.HOLDINGS, "2022_rate_hike", 100_000.0)
        assert result["estimated_recovery_years"] >= 0.0
