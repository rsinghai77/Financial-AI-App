"""Pure financial performance calculation functions.

GRD-CQ-002: Uses numpy for vectorised computations.
GRD-CQ-004: All public functions must have corresponding unit tests.
"""

from decimal import Decimal

import numpy as np
import numpy.typing as npt


def calculate_twr(
    period_returns: list[float],
) -> float:
    """Calculate Time-Weighted Return from a list of sub-period returns.

    TWR eliminates the distorting effect of external cash flows, making it
    the industry standard for comparing investment manager performance.

    Args:
        period_returns: List of sub-period returns as decimals (e.g., 0.05 for 5%).

    Returns:
        Cumulative time-weighted return as a decimal.

    Raises:
        ValueError: If any sub-period return is -1 (100% loss) or list is empty.
    """
    if not period_returns:
        raise ValueError("period_returns must not be empty")
    if any(r <= -1.0 for r in period_returns):
        raise ValueError("Sub-period return cannot be -100% or worse")

    arr: npt.NDArray[np.float64] = np.array(period_returns, dtype=np.float64)
    twr = float(np.prod(1 + arr)) - 1.0
    return round(twr, 6)


def calculate_irr(
    cash_flows: list[float],
    max_iterations: int = 1000,
    tolerance: float = 1e-6,
) -> dict[str, float]:
    """Calculate Internal Rate of Return using Newton-Raphson method.

    Args:
        cash_flows: Cash flow series (negative = outflow, positive = inflow).
            First element is typically the initial investment (negative).
        max_iterations: Maximum Newton-Raphson iterations.
        tolerance: Convergence tolerance.

    Returns:
        Dict with irr_annual and irr_monthly.

    Raises:
        ValueError: If no sign change in cash flows (no IRR exists).
        RuntimeError: If IRR does not converge.
    """
    cf = np.array(cash_flows, dtype=np.float64)

    if not (np.any(cf > 0) and np.any(cf < 0)):
        raise ValueError("Cash flows must have at least one positive and one negative value")

    # Newton-Raphson
    rate = 0.1  # Initial guess: 10%
    for _ in range(max_iterations):
        t = np.arange(len(cf), dtype=np.float64)
        npv = np.sum(cf / (1 + rate) ** t)
        dnpv = np.sum(-t * cf / (1 + rate) ** (t + 1))
        if abs(dnpv) < 1e-12:
            break
        new_rate = rate - npv / dnpv
        if abs(new_rate - rate) < tolerance:
            irr_annual = new_rate
            irr_monthly = (1 + irr_annual) ** (1 / 12) - 1
            return {
                "irr_annual": round(irr_annual, 6),
                "irr_monthly": round(irr_monthly, 6),
            }
        rate = new_rate

    raise RuntimeError("IRR calculation did not converge")


def calculate_alpha(
    portfolio_return: float,
    benchmark_return: float,
    portfolio_beta: float,
    risk_free_rate: float = 0.05,
) -> float:
    """Calculate Jensen's Alpha.

    Alpha = Portfolio Return - [Risk-Free Rate + Beta * (Benchmark Return - Risk-Free Rate)]

    Args:
        portfolio_return: Annualised portfolio return as decimal.
        benchmark_return: Annualised benchmark return as decimal.
        portfolio_beta: Portfolio beta relative to the benchmark.
        risk_free_rate: Annual risk-free rate as decimal.

    Returns:
        Jensen's alpha as a decimal.
    """
    expected_return = risk_free_rate + portfolio_beta * (benchmark_return - risk_free_rate)
    return round(portfolio_return - expected_return, 6)


def project_future_value(
    initial_value: float,
    annual_return_rate: float,
    years: int,
    monthly_contribution: float = 0.0,
    inflation_rate: float = 0.03,
) -> dict[str, object]:
    """Project the future value of an investment with regular contributions.

    GRD-FC-004: Projections must include conservative, base, and optimistic scenarios.

    Args:
        initial_value: Starting portfolio value in USD.
        annual_return_rate: Expected annual return (e.g., 0.07 for 7%).
        years: Number of years to project.
        monthly_contribution: Monthly contribution in USD.
        inflation_rate: Annual inflation rate for real-value calculation.

    Returns:
        Dict with future_value_nominal, future_value_real, total_contributions,
        total_growth, and year_by_year list.

    Raises:
        ValueError: If years < 1 or years > 50.
    """
    if not 1 <= years <= 50:
        raise ValueError(f"years must be between 1 and 50, got {years}")

    monthly_rate = (1 + annual_return_rate) ** (1 / 12) - 1
    monthly_inflation = (1 + inflation_rate) ** (1 / 12) - 1

    value = float(initial_value)
    total_contributions = 0.0
    year_by_year = []

    for year in range(1, years + 1):
        for _ in range(12):
            value = value * (1 + monthly_rate) + monthly_contribution
            total_contributions += monthly_contribution

        year_by_year.append({
            "year": year,
            "value_nominal": round(value, 2),
            "value_real": round(value / (1 + inflation_rate) ** year, 2),
        })

    total_growth = value - initial_value - total_contributions
    future_value_real = value / (1 + inflation_rate) ** years

    return {
        "future_value_nominal": round(value, 2),
        "future_value_real": round(future_value_real, 2),
        "total_contributions": round(total_contributions, 2),
        "total_growth": round(total_growth, 2),
        "year_by_year": year_by_year,
    }


def calculate_tax_impact(
    ticker: str,
    quantity: float,
    purchase_price: float,
    sale_price: float,
    purchase_date_days_ago: int,
    federal_short_term_rate: float = 0.37,
    federal_long_term_rate: float = 0.20,
    state_rate: float = 0.05,
) -> dict[str, float]:
    """Estimate capital gains tax impact of a sale.

    GRD-FC-003: Result must be displayed with the tax disclaimer.

    Args:
        ticker: Ticker symbol (informational only).
        quantity: Number of shares/units sold.
        purchase_price: Original cost basis per share.
        sale_price: Current sale price per share.
        purchase_date_days_ago: Days since purchase (determines LT vs ST treatment).
        federal_short_term_rate: Federal short-term capital gains rate.
        federal_long_term_rate: Federal long-term capital gains rate.
        state_rate: State capital gains tax rate.

    Returns:
        Dict with gain_loss, is_long_term, applicable_rate, estimated_tax,
        net_proceeds.
    """
    gain_loss = (sale_price - purchase_price) * quantity
    is_long_term = purchase_date_days_ago >= 365
    federal_rate = federal_long_term_rate if is_long_term else federal_short_term_rate
    total_rate = federal_rate + state_rate

    estimated_tax = max(gain_loss * total_rate, 0.0) if gain_loss > 0 else 0.0
    net_proceeds = (sale_price * quantity) - estimated_tax

    return {
        "gain_loss": round(gain_loss, 2),
        "is_long_term": float(is_long_term),
        "federal_rate": federal_rate,
        "state_rate": state_rate,
        "total_rate": total_rate,
        "estimated_tax": round(estimated_tax, 2),
        "net_proceeds": round(net_proceeds, 2),
    }


def optimize_weights(
    expected_returns: dict[str, float],
    covariance_matrix: npt.NDArray[np.float64],
    optimization_target: str = "max_sharpe",
    risk_free_rate: float = 0.05,
    min_weight: float = 0.0,
    max_weight: float = 1.0,
    n_simulations: int = 5000,
) -> dict[str, object]:
    """Optimise portfolio weights using Monte Carlo simulation.

    Uses random portfolio simulation to find the efficient frontier and
    select the portfolio matching the optimization_target.

    Args:
        expected_returns: Dict of ticker -> expected annual return.
        covariance_matrix: Covariance matrix (n x n numpy array).
        optimization_target: 'max_sharpe' | 'min_volatility' | 'max_return_for_risk'.
        risk_free_rate: Annual risk-free rate.
        min_weight: Minimum weight per asset (0.0 = allow zero).
        max_weight: Maximum weight per asset (1.0 = allow full concentration).
        n_simulations: Number of random portfolios to simulate.

    Returns:
        Dict with weights (ticker -> weight), expected_return, expected_volatility,
        sharpe_ratio.

    Raises:
        ValueError: If unknown optimization_target.
    """
    tickers = list(expected_returns.keys())
    n = len(tickers)
    exp_ret = np.array([expected_returns[t] for t in tickers])

    best_metric = -np.inf if optimization_target in ("max_sharpe", "max_return_for_risk") else np.inf
    best_weights = np.ones(n) / n  # Equal weight fallback
    best_ret = 0.0
    best_vol = 0.0

    rng = np.random.default_rng(42)

    for _ in range(n_simulations):
        raw = rng.random(n)
        raw = np.clip(raw, min_weight, max_weight)
        w = raw / raw.sum()

        port_ret = float(np.dot(w, exp_ret))
        port_var = float(w @ covariance_matrix @ w)
        port_vol = float(np.sqrt(max(port_var, 0)))

        if optimization_target == "max_sharpe":
            metric = (port_ret - risk_free_rate) / port_vol if port_vol > 0 else -np.inf
            if metric > best_metric:
                best_metric, best_weights, best_ret, best_vol = metric, w, port_ret, port_vol
        elif optimization_target == "min_volatility":
            if port_vol < best_metric or best_metric == np.inf:
                best_metric, best_weights, best_ret, best_vol = port_vol, w, port_ret, port_vol
        elif optimization_target == "max_return_for_risk":
            if port_ret > best_metric:
                best_metric, best_weights, best_ret, best_vol = port_ret, w, port_ret, port_vol
        else:
            raise ValueError(f"Unknown optimization_target: {optimization_target}")

    sharpe = (best_ret - risk_free_rate) / best_vol if best_vol > 0 else 0.0
    weights_dict = {t: round(float(w), 4) for t, w in zip(tickers, best_weights)}

    return {
        "weights": weights_dict,
        "expected_return": round(best_ret, 6),
        "expected_volatility": round(best_vol, 6),
        "sharpe_ratio": round(sharpe, 4),
    }
