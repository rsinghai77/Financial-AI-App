"""Market Data Page — PAGE-004.

Tabs: Quotes & Charts | Watchlist
"""

import asyncio

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from finapp.app.services.market_data_service import MarketDataService
from finapp.gui.components.shared import staleness_warning


def render_market() -> None:
    """Render the Market Data page."""
    st.title("📈 Market Data")

    market_service = MarketDataService()
    tab_charts, tab_watchlist = st.tabs(["📊 Quotes & Charts", "👁️ Watchlist"])

    # -------------------------------------------------------------------------
    # TAB: Quotes & Charts
    # -------------------------------------------------------------------------
    with tab_charts:
        ticker_input = st.text_input(
            "Search ticker symbol",
            placeholder="e.g. AAPL, MSFT, SPY...",
            max_chars=10,
        ).upper().strip()

        if ticker_input:
            col_period, col_indicators = st.columns(2)
            with col_period:
                period = st.selectbox("Period", ["1mo", "3mo", "6mo", "ytd", "1y", "5y", "max"], index=4)
            with col_indicators:
                selected_indicators = st.multiselect(
                    "Overlay Indicators",
                    options=["SMA_20", "SMA_50", "SMA_200", "EMA_12", "EMA_26", "BOLLINGER_BANDS"],
                )

            # Fetch quote and historical data in parallel
            with st.spinner(f"Loading data for {ticker_input}..."):
                quotes = asyncio.run(market_service.get_quotes([ticker_input]))
                bars = asyncio.run(market_service.get_historical_prices(ticker_input, period))

            quote = quotes.get(ticker_input)
            if quote:
                # Price header
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Price", f"${float(quote.price):.2f}")
                with col2:
                    change_pct = float(quote.change_pct)
                    st.metric("Day Change", f"${float(quote.change):+.2f}", delta=f"{change_pct:+.2f}%")
                with col3:
                    st.metric("Volume", f"{quote.volume:,}" if quote.volume else "N/A")
                with col4:
                    if quote.market_cap:
                        mc = float(quote.market_cap)
                        st.metric("Market Cap", f"${mc/1e9:.1f}B" if mc > 1e9 else f"${mc/1e6:.1f}M")

                if quote.is_cached:
                    staleness_warning(quote.cache_age_seconds)

            # Candlestick chart
            if bars:
                fig = go.Figure()

                dates = [b.date for b in bars]
                closes = [float(b.close) for b in bars]
                opens = [float(b.open) for b in bars]
                highs = [float(b.high) for b in bars]
                lows = [float(b.low) for b in bars]

                fig.add_trace(go.Candlestick(
                    x=dates, open=opens, high=highs, low=lows, close=closes,
                    name=ticker_input,
                    increasing_line_color="#43A047",
                    decreasing_line_color="#E53935",
                ))

                # Overlay indicators
                if selected_indicators:
                    with st.spinner("Calculating indicators..."):
                        from finapp.mcp_servers.market_data_server import get_technical_indicators
                        ind_data = asyncio.run(
                            get_technical_indicators(ticker_input, selected_indicators, period)
                        )

                    colors = {"SMA_20": "#FF9800", "SMA_50": "#9C27B0", "SMA_200": "#F44336",
                              "EMA_12": "#00BCD4", "EMA_26": "#E91E63"}
                    for ind in selected_indicators:
                        if ind in ind_data and isinstance(ind_data[ind], list):
                            ind_dates = [p["date"] for p in ind_data[ind]]
                            ind_vals = [p["value"] for p in ind_data[ind] if "value" in p]
                            if ind_dates and ind_vals:
                                fig.add_trace(go.Scatter(
                                    x=ind_dates, y=ind_vals, name=ind,
                                    line={"color": colors.get(ind, "#FFFFFF"), "width": 1},
                                ))

                fig.update_layout(
                    height=450,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis_rangeslider_visible=False,
                    legend={"orientation": "h"},
                    margin={"l": 0, "r": 0, "t": 10, "b": 0},
                )
                st.plotly_chart(fig, use_container_width=True)

            # Fundamentals
            st.subheader("Fundamental Data")
            with st.spinner("Loading fundamentals..."):
                fundamentals = asyncio.run(market_service.get_fundamentals(ticker_input))

            fund_data = {
                "P/E Ratio": f"{float(fundamentals.pe_ratio):.2f}" if fundamentals.pe_ratio else "N/A",
                "P/B Ratio": f"{float(fundamentals.pb_ratio):.2f}" if fundamentals.pb_ratio else "N/A",
                "P/S Ratio": f"{float(fundamentals.ps_ratio):.2f}" if fundamentals.ps_ratio else "N/A",
                "EV/EBITDA": f"{float(fundamentals.ev_ebitda):.2f}" if fundamentals.ev_ebitda else "N/A",
                "Dividend Yield": f"{float(fundamentals.dividend_yield)*100:.2f}%" if fundamentals.dividend_yield else "N/A",
                "EPS (TTM)": f"${float(fundamentals.eps_ttm):.2f}" if fundamentals.eps_ttm else "N/A",
                "Profit Margin": f"{float(fundamentals.profit_margin)*100:.1f}%" if fundamentals.profit_margin else "N/A",
                "ROE": f"{float(fundamentals.return_on_equity)*100:.1f}%" if fundamentals.return_on_equity else "N/A",
                "Debt/Equity": f"{float(fundamentals.debt_to_equity):.2f}" if fundamentals.debt_to_equity else "N/A",
                "Earnings Growth YoY": f"{float(fundamentals.earnings_growth_yoy)*100:.1f}%" if fundamentals.earnings_growth_yoy else "N/A",
            }
            fund_df = pd.DataFrame(list(fund_data.items()), columns=["Metric", "Value"])
            col1, col2 = st.columns(2)
            with col1:
                st.dataframe(fund_df.iloc[:5], use_container_width=True, hide_index=True)
            with col2:
                st.dataframe(fund_df.iloc[5:], use_container_width=True, hide_index=True)
        else:
            st.info("Enter a ticker symbol above to view quotes, charts, and fundamentals.")

    # -------------------------------------------------------------------------
    # TAB: Watchlist
    # -------------------------------------------------------------------------
    with tab_watchlist:
        st.subheader("Watchlist")

        if "watchlist" not in st.session_state:
            st.session_state.watchlist = []

        # Add ticker
        add_col, btn_col = st.columns([3, 1])
        with add_col:
            new_ticker = st.text_input("Add to watchlist", placeholder="e.g. TSLA", key="watchlist_input", max_chars=10)
        with btn_col:
            st.write("")  # Vertical alignment spacer
            st.write("")
            if st.button("Add", key="watchlist_add"):
                if new_ticker and new_ticker.upper() not in st.session_state.watchlist:
                    st.session_state.watchlist.append(new_ticker.upper())

        if st.session_state.watchlist:
            with st.spinner("Fetching watchlist prices..."):
                quotes = asyncio.run(market_service.get_quotes(st.session_state.watchlist))

            wl_data = []
            for ticker in st.session_state.watchlist:
                q = quotes.get(ticker)
                wl_data.append({
                    "Ticker": ticker,
                    "Price": f"${float(q.price):.2f}" if q else "N/A",
                    "Day Change": f"{float(q.change_pct):+.2f}%" if q else "N/A",
                    "52W High": f"${float(q.high_52w):.2f}" if q and q.high_52w else "N/A",
                    "52W Low": f"${float(q.low_52w):.2f}" if q and q.low_52w else "N/A",
                })

            st.dataframe(pd.DataFrame(wl_data), use_container_width=True, hide_index=True)

            if st.button("🗑️ Clear Watchlist"):
                st.session_state.watchlist = []
                st.rerun()
        else:
            st.info("Your watchlist is empty. Add tickers above to track them.")


if __name__ == "__main__":
    render_market()
