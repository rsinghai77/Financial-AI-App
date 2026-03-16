"""Dashboard Page — PAGE-001.

Main portfolio overview with KPIs, charts, and news preview.
GRD-CQ-003: All data fetches use st.spinner().
GRD-OPS-003: Data timestamps shown on all market data.
"""

import asyncio
from decimal import Decimal

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from finapp.app.services.market_data_service import MarketDataService
from finapp.app.services.news_service import NewsService
from finapp.app.services.portfolio_service import PortfolioService
from finapp.gui.components.shared import (
    color_pct,
    color_value,
    sentiment_badge,
    staleness_warning,
)


def render_dashboard() -> None:
    """Render the full Portfolio Dashboard page."""
    st.title("📊 Portfolio Dashboard")

    portfolio_service = PortfolioService()
    market_service = MarketDataService()
    news_service = NewsService()

    # -------------------------------------------------------------------------
    # Fetch data
    # -------------------------------------------------------------------------
    with st.spinner("Loading portfolio..."):
        portfolio = asyncio.run(portfolio_service.get_or_create_portfolio())
        tickers = portfolio_service.get_all_tickers(portfolio)

    prices: dict[str, Decimal] = {}
    max_cache_age = 0

    if tickers:
        with st.spinner(f"Fetching market prices for {len(tickers)} holdings..."):
            quotes = asyncio.run(market_service.get_quotes(tickers))
            prices = {t: q.price for t, q in quotes.items()}
            max_cache_age = max((q.cache_age_seconds for q in quotes.values()), default=0)

    # Inject prices into portfolio
    with st.spinner("Calculating portfolio values..."):
        portfolio = asyncio.run(portfolio_service.get_portfolio_with_prices(prices))

    # Staleness warning (GRD-OPS-003)
    if max_cache_age > 900:
        staleness_warning(max_cache_age)

    # -------------------------------------------------------------------------
    # KPI Row — 4 metric cards
    # -------------------------------------------------------------------------
    total_value = float(portfolio.total_value)
    total_cost = float(portfolio.total_cost_basis)
    total_gl = float(portfolio.total_gain_loss)
    total_gl_pct = float(portfolio.total_gain_loss_pct)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Total Portfolio Value",
            f"${total_value:,.2f}",
            delta=None,
        )
    with col2:
        st.metric(
            "Total Gain / Loss",
            f"${total_gl:+,.2f}",
            delta=f"{total_gl_pct:+.2f}%",
            delta_color="normal",
        )
    with col3:
        st.metric(
            "Total Cost Basis",
            f"${total_cost:,.2f}",
        )
    with col4:
        holding_count = sum(
            1 for acc in portfolio.accounts for h in acc.holdings if h.is_open
        )
        st.metric("Open Positions", str(holding_count))

    st.divider()

    # -------------------------------------------------------------------------
    # Charts Row — Portfolio Value Placeholder + Allocation Pie
    # -------------------------------------------------------------------------
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Portfolio Value Over Time")
        if not tickers:
            st.info("Add holdings to see your portfolio value chart.")
        else:
            # Use SPY as a proxy timeline placeholder until daily snapshots are persisted
            with st.spinner("Loading chart data..."):
                bars = asyncio.run(market_service.get_historical_prices(tickers[0], "1y"))
            if bars:
                import pandas as pd
                df = pd.DataFrame([{"Date": b.date, "Value": float(b.close)} for b in bars])
                fig = go.Figure(go.Scatter(
                    x=df["Date"], y=df["Value"],
                    mode="lines", line={"color": "#1E88E5", "width": 2},
                    fill="tozeroy", fillcolor="rgba(30,136,229,0.1)",
                ))
                fig.update_layout(
                    height=300, margin={"l": 0, "r": 0, "t": 0, "b": 0},
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    xaxis={"gridcolor": "#2c2c2c"}, yaxis={"gridcolor": "#2c2c2c"},
                )
                st.plotly_chart(fig, use_container_width=True)
                st.caption(f"*Showing {tickers[0]} price as portfolio timeline proxy (v0.1)*")

    with chart_col2:
        st.subheader("Asset Allocation")
        allocation = portfolio.asset_allocation
        if allocation:
            fig = px.pie(
                names=list(allocation.keys()),
                values=[float(v) for v in allocation.values()],
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig.update_layout(
                height=300, margin={"l": 0, "r": 0, "t": 0, "b": 0},
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=True,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No holdings yet. Add positions in the Portfolio page.")

    st.divider()

    # -------------------------------------------------------------------------
    # Holdings Table
    # -------------------------------------------------------------------------
    st.subheader("Holdings Summary")
    all_holdings = []
    for account in portfolio.accounts:
        for holding in account.holdings:
            if holding.is_open:
                all_holdings.append({
                    "Account": account.name,
                    "Ticker": holding.ticker,
                    "Asset Class": holding.asset_class,
                    "Quantity": float(holding.quantity),
                    "Cost Basis/Share": f"${float(holding.cost_basis_per_share):.2f}",
                    "Current Price": f"${float(holding.current_price):.2f}" if holding.current_price else "N/A",
                    "Current Value": f"${float(holding.current_value):,.2f}",
                    "Gain/Loss ($)": f"${float(holding.gain_loss_dollars):+,.2f}",
                    "Gain/Loss (%)": f"{float(holding.gain_loss_pct):+.2f}%",
                })

    if all_holdings:
        import pandas as pd
        df = pd.DataFrame(all_holdings)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No holdings in your portfolio yet. Go to the **Portfolio** page to add positions.")

    st.divider()

    # -------------------------------------------------------------------------
    # News Preview
    # -------------------------------------------------------------------------
    st.subheader("📰 Latest Portfolio News")
    if tickers:
        with st.spinner("Fetching news..."):
            articles = asyncio.run(news_service.get_portfolio_news(portfolio, max_articles=5))

        if articles:
            for article in articles:
                with st.container():
                    col_a, col_b = st.columns([4, 1])
                    with col_a:
                        if article.url:
                            st.markdown(f"**[{article.title}]({article.url})**")
                        else:
                            st.markdown(f"**{article.title}**")
                        st.caption(f"{article.source} · {article.published_at.strftime('%b %d, %Y')}")
                        if article.description:
                            st.caption(article.description[:200] + "..." if len(article.description or "") > 200 else article.description)
                    with col_b:
                        st.markdown(
                            sentiment_badge(article.sentiment_label),
                            unsafe_allow_html=True,
                        )
                st.divider()
        else:
            st.info("No news found for your holdings. Configure NEWS_API_KEY in Settings.")
    else:
        st.info("Add holdings to see relevant news.")
