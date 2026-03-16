"""Risk Analysis Page — PAGE-005."""

import asyncio
from decimal import Decimal

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from finapp.app.services.market_data_service import MarketDataService
from finapp.app.services.portfolio_service import PortfolioService
from finapp.app.services.risk_service import RiskService


def render_risk() -> None:
    """Render the Risk Analysis page."""
    st.title("⚠️ Risk Analysis")

    portfolio_service = PortfolioService()
    market_service = MarketDataService()
    risk_service = RiskService()

    with st.spinner("Loading portfolio..."):
        portfolio = asyncio.run(portfolio_service.get_or_create_portfolio())
        tickers = portfolio_service.get_all_tickers(portfolio)

    if not tickers:
        st.info("Add holdings to your portfolio to see risk analysis.")
        return

    with st.spinner("Fetching prices and computing risk metrics..."):
        prices = asyncio.run(market_service.get_prices_map(tickers))
        portfolio = asyncio.run(portfolio_service.get_portfolio_with_prices(prices))
        risk_metrics = asyncio.run(risk_service.calculate_portfolio_risk(portfolio))

    # -------------------------------------------------------------------------
    # KPI Row
    # -------------------------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "VaR (95%, 1-Day)",
            f"${float(risk_metrics.var_95_1d_dollars):,.2f}",
            help="With 95% confidence, maximum expected 1-day loss",
        )
    with col2:
        st.metric(
            "VaR (99%, 1-Day)",
            f"${float(risk_metrics.var_99_1d_dollars):,.2f}",
            help="With 99% confidence, maximum expected 1-day loss",
        )
    with col3:
        sr = risk_metrics.sharpe_ratio
        st.metric(
            "Sharpe Ratio",
            f"{float(sr):.2f}" if sr else "N/A",
            help="Risk-adjusted return (higher is better; >1 is generally good)",
        )
    with col4:
        md = risk_metrics.max_drawdown_pct
        st.metric(
            "Max Drawdown",
            f"{float(md)*100:.1f}%" if md else "N/A",
            help="Largest peak-to-trough decline in the historical period",
        )

    st.caption(
        "⚠️ Risk metrics are estimated from 1-year historical returns. "
        "Past performance does not guarantee future results."
    )
    st.divider()

    # -------------------------------------------------------------------------
    # Charts Row: Correlation Heatmap + Return Distribution
    # -------------------------------------------------------------------------
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Correlation Heatmap")
        if len(tickers) >= 2:
            with st.spinner("Computing correlations..."):
                corr = asyncio.run(risk_service.get_correlation_matrix(tickers[:10]))

            if corr:
                import pandas as pd
                corr_df = pd.DataFrame(corr).fillna(0)
                fig = px.imshow(
                    corr_df,
                    color_continuous_scale="RdBu_r",
                    zmin=-1, zmax=1,
                    text_auto=".2f",
                )
                fig.update_layout(
                    height=350,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin={"l": 0, "r": 0, "t": 0, "b": 0},
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Not enough historical data to compute correlations.")
        else:
            st.info("Add at least 2 holdings to see the correlation heatmap.")

    with chart_col2:
        st.subheader("Return Distribution")
        if tickers:
            with st.spinner("Fetching return data..."):
                returns = asyncio.run(market_service.get_daily_returns(tickers[0], "1y"))

            if returns:
                import numpy as np
                import pandas as pd

                fig = go.Figure()
                fig.add_trace(go.Histogram(
                    x=returns,
                    nbinsx=50,
                    name="Historical Returns",
                    marker_color="#1E88E5",
                    opacity=0.7,
                ))
                fig.update_layout(
                    height=350,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis_title="Daily Return",
                    yaxis_title="Frequency",
                    margin={"l": 0, "r": 0, "t": 0, "b": 0},
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption(f"Distribution of daily returns for {tickers[0]} (1-year)")

    st.divider()

    # -------------------------------------------------------------------------
    # Stress Testing
    # -------------------------------------------------------------------------
    st.subheader("🧪 Stress Testing")

    scenario_options = {
        "2008 Financial Crisis (S&P -57%)": "2008_financial_crisis",
        "2020 COVID Crash (S&P -34%)": "2020_covid_crash",
        "2022 Rate Hike Cycle (S&P -25%)": "2022_rate_hike",
        "Dot-Com Bubble (S&P -49%)": "dot_com_bubble",
        "Custom Scenario": "custom",
    }

    sel_scenario_label = st.selectbox("Select Scenario", options=list(scenario_options.keys()))
    sel_scenario = scenario_options[sel_scenario_label]

    custom_shock = None
    if sel_scenario == "custom":
        custom_shock_pct = st.slider("Custom Market Drop (%)", min_value=-70, max_value=-5, value=-30)
        custom_shock = custom_shock_pct / 100.0

    if st.button("▶️ Run Stress Test", type="primary"):
        with st.spinner("Running stress test..."):
            result = asyncio.run(risk_service.run_stress_test(portfolio, sel_scenario, custom_shock))

        st.subheader("Stress Test Results")
        res_col1, res_col2, res_col3 = st.columns(3)
        with res_col1:
            loss_pct = float(result["portfolio_loss_pct"]) * 100
            st.metric("Portfolio Loss", f"{loss_pct:.1f}%")
        with res_col2:
            loss_dollars = float(result["portfolio_loss_dollars"])
            st.metric("Dollar Loss", f"${loss_dollars:,.2f}")
        with res_col3:
            recovery = float(result["estimated_recovery_years"])
            st.metric("Est. Recovery", f"{recovery:.1f} years", help="Assumes 7% annual return")

        if result.get("worst_holding"):
            st.warning(
                f"**Worst holding in this scenario:** {result['worst_holding']} "
                f"({float(result['worst_holding_loss_pct'])*100:.1f}% loss)"
            )

        st.caption(
            "⚠️ Stress test results are based on historical crash patterns applied to current "
            "portfolio weights. Actual losses may differ significantly. "
            "Past performance does not guarantee future results."
        )


if __name__ == "__main__":
    render_risk()
