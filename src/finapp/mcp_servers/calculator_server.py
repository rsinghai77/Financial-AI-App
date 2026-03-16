"""Financial Calculator MCP Server — MCP-004.

Stateless financial calculation tools. All functions are pure — no data persisted.
GRD-CQ-002: Uses numpy for vectorised calculations.
"""

import logging
from typing import Any, Optional

from mcp.server import FastMCP

from finapp.domain.calculators.performance_calculator import (
    calculate_irr,
    calculate_tax_impact,
    optimize_weights,
    project_future_value,
)
from finapp.domain.calculators.risk_calculator import (
    calculate_sharpe,
    calculate_var,
    run_stress_test,
)

logger = logging.getLogger(__name__)
mcp = FastMCP("calculator-mcp")


@mcp.tool()
def tool_calculate_var(
    portfolio_returns: list[float],
    confidence_level: float = 0.95,
    holding_period_days: int = 1,
    portfolio_value: float = 100_000.0,
) -> dict[str, Any]:
    """Calculate Value at Risk for a portfolio using historical simulation.

    Args:
        portfolio_returns: Historical daily return series as decimals.
        confidence_level: 0.90, 0.95, or 0.99.
        holding_period_days: 1, 5, or 10.
        portfolio_value: Current portfolio value in USD.

    Returns:
        Dict with var_pct, var_dollars, confidence_level, holding_period_days, method.
    """
    try:
        return calculate_var(portfolio_returns, confidence_level, holding_period_days, portfolio_value)
    except ValueError as exc:
        return {"error": str(exc)}


@mcp.tool()
def tool_calculate_sharpe(
    returns: list[float],
    risk_free_rate_annual: float = 0.05,
) -> dict[str, Any]:
    """Calculate Sharpe and Sortino ratios from a daily return series.

    Args:
        returns: Daily return series as decimals.
        risk_free_rate_annual: Annual risk-free rate (e.g., 0.05 for 5%).

    Returns:
        Dict with sharpe_ratio, sortino_ratio, annualized_return,
        annualized_volatility, max_drawdown.
    """
    try:
        return calculate_sharpe(returns, risk_free_rate_annual)
    except ValueError as exc:
        return {"error": str(exc)}


@mcp.tool()
def tool_run_stress_test(
    holdings: list[dict[str, Any]],
    scenario: str,
    portfolio_value: float,
    custom_shock_pct: Optional[float] = None,
) -> dict[str, Any]:
    """Simulate portfolio loss under a historical crash scenario.

    Args:
        holdings: List of dicts with 'ticker', 'weight', 'asset_class'.
        scenario: One of "2008_financial_crisis", "2020_covid_crash",
            "2022_rate_hike", "dot_com_bubble", "custom".
        portfolio_value: Current portfolio value in USD.
        custom_shock_pct: For custom scenario (e.g., -0.30 for 30% drop).

    Returns:
        Dict with portfolio_loss_pct, portfolio_loss_dollars, worst_holding,
        estimated_recovery_years.
    """
    try:
        return run_stress_test(holdings, scenario, portfolio_value, custom_shock_pct)
    except (ValueError, KeyError) as exc:
        return {"error": str(exc)}


@mcp.tool()
def tool_calculate_irr(
    cash_flows: list[float],
    dates: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Calculate Internal Rate of Return for a series of cash flows.

    Args:
        cash_flows: Cash flows (negative=outflow, positive=inflow).
        dates: Optional ISO dates for each cash flow (informational).

    Returns:
        Dict with irr_annual, irr_monthly.
    """
    try:
        return calculate_irr(cash_flows)
    except (ValueError, RuntimeError) as exc:
        return {"error": str(exc)}


@mcp.tool()
def tool_optimize_weights(
    tickers: list[str],
    expected_returns: list[float],
    return_correlations: list[list[float]],
    return_volatilities: list[float],
    optimization_target: str = "max_sharpe",
    min_weight: float = 0.0,
    max_weight: float = 1.0,
) -> dict[str, Any]:
    """Calculate optimal portfolio weights using Monte Carlo simulation.

    Args:
        tickers: List of ticker symbols.
        expected_returns: Expected annual return per ticker (same order).
        return_correlations: n×n correlation matrix as nested list.
        return_volatilities: Annualised volatility per ticker (same order).
        optimization_target: "max_sharpe" | "min_volatility" | "max_return_for_risk".
        min_weight: Minimum allocation per asset.
        max_weight: Maximum allocation per asset.

    Returns:
        Dict with weights (ticker->weight), expected_return, expected_volatility, sharpe_ratio.
    """
    import numpy as np

    try:
        n = len(tickers)
        vol = np.array(return_volatilities)
        corr = np.array(return_correlations)
        # Convert correlation + volatility to covariance matrix
        cov = np.outer(vol, vol) * corr
        exp_ret_dict = dict(zip(tickers, expected_returns))
        return optimize_weights(exp_ret_dict, cov, optimization_target, min_weight=min_weight, max_weight=max_weight)
    except (ValueError, Exception) as exc:
        return {"error": str(exc)}


@mcp.tool()
def tool_project_future_value(
    initial_value: float,
    annual_return_rate: float,
    years: int,
    monthly_contribution: float = 0.0,
    inflation_rate: float = 0.03,
) -> dict[str, Any]:
    """Project future value of an investment with optional monthly contributions.

    GRD-FC-004: Always includes conservative, base, optimistic scenarios.

    Args:
        initial_value: Starting value in USD.
        annual_return_rate: Expected annual return (e.g., 0.07 for 7%).
        years: Number of years to project (1–50).
        monthly_contribution: Monthly contribution in USD.
        inflation_rate: Annual inflation rate (default 3%).

    Returns:
        Dict with three scenarios (conservative/base/optimistic) and year_by_year data.
    """
    try:
        # GRD-FC-004: Always include three scenarios
        scenarios = {
            "conservative": project_future_value(
                initial_value, max(annual_return_rate - 0.02, 0.01), years, monthly_contribution, inflation_rate
            ),
            "base": project_future_value(
                initial_value, annual_return_rate, years, monthly_contribution, inflation_rate
            ),
            "optimistic": project_future_value(
                initial_value, annual_return_rate + 0.02, years, monthly_contribution, inflation_rate
            ),
        }
        return {
            "scenarios": scenarios,
            "assumptions": {
                "initial_value": initial_value,
                "base_annual_return": annual_return_rate,
                "monthly_contribution": monthly_contribution,
                "inflation_rate": inflation_rate,
                "years": years,
                "disclaimer": "Past performance does not guarantee future results.",
            },
        }
    except ValueError as exc:
        return {"error": str(exc)}


@mcp.tool()
def tool_calculate_tax_impact(
    ticker: str,
    quantity: float,
    purchase_price: float,
    sale_price: float,
    purchase_date_days_ago: int,
    federal_short_term_rate: float = 0.37,
    federal_long_term_rate: float = 0.20,
    state_rate: float = 0.05,
) -> dict[str, Any]:
    """Estimate capital gains tax impact of a sale.

    GRD-FC-003: Caller must display the tax disclaimer alongside results.

    Args:
        ticker: Ticker symbol (informational).
        quantity: Number of shares sold.
        purchase_price: Original cost basis per share.
        sale_price: Sale price per share.
        purchase_date_days_ago: Days since purchase.
        federal_short_term_rate: Federal ST rate (default 37%).
        federal_long_term_rate: Federal LT rate (default 20%).
        state_rate: State rate (default 5%).

    Returns:
        Dict with gain_loss, is_long_term, estimated_tax, net_proceeds.
    """
    result = calculate_tax_impact(
        ticker, quantity, purchase_price, sale_price, purchase_date_days_ago,
        federal_short_term_rate, federal_long_term_rate, state_rate,
    )
    result["disclaimer"] = (
        "Tax calculations shown are estimates based on general rules and may not "
        "reflect your specific tax situation. Consult a qualified tax professional."
    )
    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
