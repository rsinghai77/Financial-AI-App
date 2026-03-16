"""Pure financial risk calculation functions.

GRD-CQ-002: All calculations use numpy for vectorised operations.
GRD-CQ-004: Every public function here must have a corresponding unit test.

All functions are pure (no side effects, no I/O) to ensure testability.
"""

from decimal import Decimal

import numpy as np
import numpy.typing as npt


def calculate_var(
    returns: list[float],
    confidence_level: float,
    holding_period_days: int,
    portfolio_value: float,
) -> dict[str, float]:
    """Calculate Value at Risk using historical simulation.

    Args:
        returns: Historical daily return series as decimals (e.g., 0.01 for 1%).
        confidence_level: Confidence level, e.g., 0.95 or 0.99.
        holding_period_days: Holding period in days (1, 5, or 10).
        portfolio_value: Current portfolio value in USD.

    Returns:
        Dict with var_pct, var_dollars, confidence_level, holding_period_days, method.

    Raises:
        ValueError: If returns list is empty or confidence_level is invalid.
    """
    if not returns:
        raise ValueError("Returns series must not be empty")
    if not 0 < confidence_level < 1:
        raise ValueError(f"confidence_level must be between 0 and 1, got {confidence_level}")

    arr: npt.NDArray[np.float64] = np.array(returns, dtype=np.float64)
    # Scale to holding period using square-root-of-time rule
    scaled = arr * np.sqrt(holding_period_days)

    # Historical simulation: VaR is the loss at the (1-confidence) percentile
    var_pct = float(-np.percentile(scaled, (1 - confidence_level) * 100))
    var_dollars = var_pct * portfolio_value

    return {
        "var_pct": round(var_pct, 6),
        "var_dollars": round(var_dollars, 2),
        "confidence_level": confidence_level,
        "holding_period_days": holding_period_days,
        "method": "historical_simulation",
    }


def calculate_sharpe(
    returns: list[float],
    risk_free_rate_annual: float = 0.05,
) -> dict[str, float]:
    """Calculate Sharpe and Sortino ratios from a daily return series.

    Args:
        returns: Daily return series as decimals.
        risk_free_rate_annual: Annual risk-free rate (e.g., 0.05 for 5%).

    Returns:
        Dict with sharpe_ratio, sortino_ratio, annualized_return,
        annualized_volatility, max_drawdown.

    Raises:
        ValueError: If returns list has fewer than 2 elements.
    """
    if len(returns) < 2:
        raise ValueError("Need at least 2 data points to calculate Sharpe ratio")

    arr: npt.NDArray[np.float64] = np.array(returns, dtype=np.float64)
    trading_days = 252

    # Annualize
    ann_return = float(np.mean(arr)) * trading_days
    ann_vol = float(np.std(arr, ddof=1)) * np.sqrt(trading_days)

    # Sharpe ratio
    sharpe = (ann_return - risk_free_rate_annual) / ann_vol if ann_vol > 0 else 0.0

    # Sortino ratio (uses downside deviation)
    downside = arr[arr < 0]
    downside_dev = float(np.std(downside, ddof=1)) * np.sqrt(trading_days) if len(downside) > 1 else 0.0
    sortino = (ann_return - risk_free_rate_annual) / downside_dev if downside_dev > 0 else 0.0

    # Maximum drawdown
    cumulative = np.cumprod(1 + arr)
    rolling_max = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative - rolling_max) / rolling_max
    max_drawdown = float(np.min(drawdowns))

    return {
        "sharpe_ratio": round(sharpe, 4),
        "sortino_ratio": round(sortino, 4),
        "annualized_return": round(ann_return, 6),
        "annualized_volatility": round(ann_vol, 6),
        "max_drawdown": round(max_drawdown, 6),
    }


def calculate_portfolio_beta(
    portfolio_returns: list[float],
    benchmark_returns: list[float],
) -> float:
    """Calculate portfolio beta relative to a benchmark.

    Beta = Cov(portfolio, benchmark) / Var(benchmark)

    Args:
        portfolio_returns: Daily portfolio return series.
        benchmark_returns: Daily benchmark return series (same length).

    Returns:
        Portfolio beta as a float.

    Raises:
        ValueError: If series have different lengths or fewer than 2 points.
    """
    if len(portfolio_returns) != len(benchmark_returns):
        raise ValueError("Portfolio and benchmark return series must be the same length")
    if len(portfolio_returns) < 2:
        raise ValueError("Need at least 2 data points to calculate beta")

    p: npt.NDArray[np.float64] = np.array(portfolio_returns, dtype=np.float64)
    b: npt.NDArray[np.float64] = np.array(benchmark_returns, dtype=np.float64)

    cov_matrix = np.cov(p, b, ddof=1)
    beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else 0.0
    return round(float(beta), 4)


def calculate_correlation_matrix(
    returns_by_ticker: dict[str, list[float]],
) -> dict[str, dict[str, float]]:
    """Calculate pairwise correlation matrix for a set of return series.

    Args:
        returns_by_ticker: Dict mapping ticker -> daily return series.
            All series must be the same length.

    Returns:
        Nested dict: {ticker_a: {ticker_b: correlation_coefficient}}.

    Raises:
        ValueError: If fewer than 2 tickers or series have different lengths.
    """
    tickers = list(returns_by_ticker.keys())
    if len(tickers) < 2:
        raise ValueError("Need at least 2 tickers to calculate correlation matrix")

    lengths = {len(v) for v in returns_by_ticker.values()}
    if len(lengths) > 1:
        raise ValueError("All return series must be the same length")

    matrix: npt.NDArray[np.float64] = np.array(
        [returns_by_ticker[t] for t in tickers], dtype=np.float64
    )
    corr = np.corrcoef(matrix)

    result: dict[str, dict[str, float]] = {}
    for i, t_a in enumerate(tickers):
        result[t_a] = {}
        for j, t_b in enumerate(tickers):
            result[t_a][t_b] = round(float(corr[i, j]), 4)
    return result


# Historical crash scenario drawdowns by asset class
STRESS_SCENARIOS: dict[str, dict[str, float]] = {
    "2008_financial_crisis": {
        "equity": -0.57, "etf": -0.50, "bond": -0.05, "crypto": -0.50,
        "reit": -0.68, "commodity": -0.30, "cash": 0.0, "mutual_fund": -0.45, "other": -0.30,
    },
    "2020_covid_crash": {
        "equity": -0.34, "etf": -0.30, "bond": 0.05, "crypto": -0.50,
        "reit": -0.45, "commodity": -0.40, "cash": 0.0, "mutual_fund": -0.30, "other": -0.25,
    },
    "2022_rate_hike": {
        "equity": -0.25, "etf": -0.22, "bond": -0.18, "crypto": -0.65,
        "reit": -0.28, "commodity": 0.15, "cash": 0.02, "mutual_fund": -0.20, "other": -0.15,
    },
    "dot_com_bubble": {
        "equity": -0.49, "etf": -0.45, "bond": 0.08, "crypto": -0.50,
        "reit": 0.05, "commodity": -0.10, "cash": 0.0, "mutual_fund": -0.40, "other": -0.30,
    },
}


def run_stress_test(
    holdings: list[dict[str, object]],
    scenario: str,
    portfolio_value: float,
    custom_shock_pct: float | None = None,
) -> dict[str, object]:
    """Simulate portfolio loss under a historical crash scenario.

    Args:
        holdings: List of dicts with 'ticker', 'weight', 'asset_class' keys.
        scenario: Named scenario from STRESS_SCENARIOS or 'custom'.
        portfolio_value: Current portfolio value in USD.
        custom_shock_pct: Shock percentage for custom scenario (e.g., -0.30).

    Returns:
        Dict with scenario, portfolio_loss_pct, portfolio_loss_dollars,
        worst_holding, worst_holding_loss_pct, estimated_recovery_years.

    Raises:
        ValueError: If scenario is unknown or custom_shock_pct missing for custom.
    """
    if scenario == "custom":
        if custom_shock_pct is None:
            raise ValueError("custom_shock_pct required for custom scenario")
        shocks = {asset: custom_shock_pct for asset in ["equity", "etf", "bond", "crypto",
                                                          "reit", "commodity", "cash",
                                                          "mutual_fund", "other"]}
    elif scenario not in STRESS_SCENARIOS:
        raise ValueError(f"Unknown scenario '{scenario}'. Valid: {list(STRESS_SCENARIOS)}")
    else:
        shocks = STRESS_SCENARIOS[scenario]

    total_loss_pct = 0.0
    worst_holding = ""
    worst_loss = 0.0

    for h in holdings:
        asset_class = str(h.get("asset_class", "equity"))
        weight = float(h.get("weight", 0.0))
        shock = shocks.get(asset_class, -0.30)
        holding_loss = weight * shock
        total_loss_pct += holding_loss
        if holding_loss < worst_loss:
            worst_loss = holding_loss
            worst_holding = str(h.get("ticker", ""))

    portfolio_loss_dollars = total_loss_pct * portfolio_value
    # Estimate recovery assuming 7% annual return
    recovery_years = (
        np.log(1 / (1 + total_loss_pct)) / np.log(1.07) if total_loss_pct < 0 else 0.0
    )

    return {
        "scenario": scenario,
        "portfolio_loss_pct": round(total_loss_pct, 4),
        "portfolio_loss_dollars": round(portfolio_loss_dollars, 2),
        "worst_holding": worst_holding,
        "worst_holding_loss_pct": round(worst_loss, 4),
        "estimated_recovery_years": round(float(recovery_years), 1),
    }


def calculate_var_from_decimal(
    returns: list[Decimal],
    confidence_level: float,
    holding_period_days: int,
    portfolio_value: Decimal,
) -> dict[str, float]:
    """Decimal-aware wrapper around calculate_var for use in domain layer.

    Converts Decimal inputs to float, delegates to calculate_var.
    """
    return calculate_var(
        returns=[float(r) for r in returns],
        confidence_level=confidence_level,
        holding_period_days=holding_period_days,
        portfolio_value=float(portfolio_value),
    )
