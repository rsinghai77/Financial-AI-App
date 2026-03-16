"""Unit tests for domain/calculators/performance_calculator.py.

GRD-CQ-004: Full coverage of all public functions.
"""

import math

import pytest

from finapp.domain.calculators.performance_calculator import (
    calculate_alpha,
    calculate_irr,
    calculate_twr,
    project_future_value,
)


# ---------------------------------------------------------------------------
# calculate_twr
# ---------------------------------------------------------------------------

class TestCalculateTwr:
    def test_single_period_equals_return(self) -> None:
        """TWR for a single period should equal that period's return."""
        result = calculate_twr([0.10])
        assert abs(result - 0.10) < 1e-9

    def test_two_periods_compounded(self) -> None:
        """TWR of +10% then -10% = (1.10)(0.90) - 1 = -0.01."""
        result = calculate_twr([0.10, -0.10])
        assert abs(result - (-0.01)) < 1e-6

    def test_zero_returns_gives_zero_twr(self) -> None:
        result = calculate_twr([0.0, 0.0, 0.0])
        assert abs(result) < 1e-12

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            calculate_twr([])

    def test_total_loss_raises(self) -> None:
        with pytest.raises(ValueError, match="-100%"):
            calculate_twr([-1.0, 0.05])

    def test_consistent_positive_returns(self) -> None:
        """12 months of +1% should give approx 12.68% TWR."""
        result = calculate_twr([0.01] * 12)
        expected = (1.01 ** 12) - 1
        assert abs(result - expected) < 1e-9


# ---------------------------------------------------------------------------
# calculate_irr
# ---------------------------------------------------------------------------

class TestCalculateIrr:
    def test_simple_two_period(self) -> None:
        """Initial investment of -100, return of 110 after 1 year → IRR = 10%."""
        result = calculate_irr([-100.0, 110.0])
        assert abs(result["irr_annual"] - 0.10) < 1e-4

    def test_monthly_irr_consistent_with_annual(self) -> None:
        result = calculate_irr([-1000.0, 1200.0])
        # (1 + monthly_irr)^12 ≈ 1 + annual_irr
        monthly = result["irr_monthly"]
        reconstructed_annual = (1 + monthly) ** 12 - 1
        assert abs(reconstructed_annual - result["irr_annual"]) < 1e-5

    def test_no_sign_change_raises(self) -> None:
        """All positive cash flows have no IRR."""
        with pytest.raises(ValueError, match="at least one positive and one negative"):
            calculate_irr([100.0, 200.0, 300.0])

    def test_all_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one positive and one negative"):
            calculate_irr([-100.0, -200.0])

    def test_realistic_investment_scenario(self) -> None:
        """Invest $10k, receive $2k/year for 6 years → IRR should be reasonable."""
        cash_flows = [-10_000.0] + [2_000.0] * 6
        result = calculate_irr(cash_flows)
        # IRR for this scenario is approximately 5.5%
        assert 0.03 < result["irr_annual"] < 0.10


# ---------------------------------------------------------------------------
# calculate_alpha
# ---------------------------------------------------------------------------

class TestCalculateAlpha:
    def test_market_return_portfolio_no_alpha(self) -> None:
        """Portfolio earning exactly the market return with beta=1 should have alpha≈0."""
        alpha = calculate_alpha(
            portfolio_return=0.10,
            benchmark_return=0.10,
            portfolio_beta=1.0,
            risk_free_rate=0.05,
        )
        assert abs(alpha) < 1e-9

    def test_outperforming_portfolio_positive_alpha(self) -> None:
        alpha = calculate_alpha(
            portfolio_return=0.15,
            benchmark_return=0.10,
            portfolio_beta=1.0,
            risk_free_rate=0.05,
        )
        assert alpha > 0

    def test_underperforming_portfolio_negative_alpha(self) -> None:
        alpha = calculate_alpha(
            portfolio_return=0.05,
            benchmark_return=0.10,
            portfolio_beta=1.0,
            risk_free_rate=0.05,
        )
        assert alpha < 0

    def test_low_beta_portfolio_alpha_calculation(self) -> None:
        """Beta=0.5: expected return = 0.05 + 0.5*(0.10-0.05) = 0.075.
        If portfolio returned 0.10, alpha = 0.025."""
        alpha = calculate_alpha(0.10, 0.10, 0.5, 0.05)
        assert abs(alpha - 0.025) < 1e-9


# ---------------------------------------------------------------------------
# project_future_value
# ---------------------------------------------------------------------------

class TestProjectFutureValue:
    def test_no_contribution_compound_growth(self) -> None:
        """$10k at 7% for 10 years, no contributions → $10k * 1.07^10 ≈ $19,672."""
        result = project_future_value(10_000.0, 0.07, 10, 0.0, 0.0)
        expected = 10_000.0 * (1.07 ** 10)
        assert abs(result["future_value_nominal"] - expected) < 1.0  # Within $1

    def test_zero_return_only_contributions(self) -> None:
        """0% return, $100/month for 12 months → $10k + 12*$100 = $11,200."""
        result = project_future_value(10_000.0, 0.0, 1, 100.0, 0.0)
        expected = 10_000.0 + 12 * 100.0
        assert abs(result["future_value_nominal"] - expected) < 0.01

    def test_real_value_less_than_nominal(self) -> None:
        """Inflation-adjusted value should always be less than nominal."""
        result = project_future_value(10_000.0, 0.07, 20, 500.0, 0.03)
        assert result["future_value_real"] < result["future_value_nominal"]

    def test_year_by_year_length(self) -> None:
        result = project_future_value(10_000.0, 0.07, 15, 0.0, 0.03)
        assert len(result["year_by_year"]) == 15

    def test_year_by_year_monotonically_increasing_with_positive_return(self) -> None:
        result = project_future_value(10_000.0, 0.07, 10, 0.0, 0.0)
        values = [y["value_nominal"] for y in result["year_by_year"]]
        for i in range(1, len(values)):
            assert values[i] > values[i - 1]

    def test_total_contributions_accurate(self) -> None:
        """120 months * $500 = $60,000 in total contributions."""
        result = project_future_value(0.0, 0.07, 10, 500.0, 0.0)
        assert abs(result["total_contributions"] - 60_000.0) < 0.01

    def test_years_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="between 1 and 50"):
            project_future_value(10_000.0, 0.07, 0)

    def test_years_over_50_raises(self) -> None:
        with pytest.raises(ValueError, match="between 1 and 50"):
            project_future_value(10_000.0, 0.07, 51)
