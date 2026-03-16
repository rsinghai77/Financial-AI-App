"""News Page — PAGE-006."""

import asyncio

import streamlit as st

from finapp.app.services.news_service import NewsService
from finapp.app.services.portfolio_service import PortfolioService
from finapp.gui.components.shared import sentiment_badge


def render_news() -> None:
    """Render the Financial News page."""
    st.title("📰 Financial News")

    portfolio_service = PortfolioService()
    news_service = NewsService()

    with st.spinner("Loading portfolio..."):
        portfolio = asyncio.run(portfolio_service.get_or_create_portfolio())
        tickers = portfolio_service.get_all_tickers(portfolio)

    # -------------------------------------------------------------------------
    # Filters
    # -------------------------------------------------------------------------
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        filter_ticker = st.multiselect("Filter by Ticker", options=tickers, default=[])
    with filter_col2:
        filter_sentiment = st.multiselect(
            "Sentiment", options=["positive", "neutral", "negative"], default=[]
        )
    with filter_col3:
        max_articles = st.number_input("Max Articles", min_value=5, max_value=50, value=20)

    refresh = st.button("🔄 Refresh News")

    st.divider()

    # -------------------------------------------------------------------------
    # News feed
    # -------------------------------------------------------------------------
    target_tickers = filter_ticker if filter_ticker else tickers

    if not target_tickers:
        st.info("Add holdings to your portfolio or select tickers to see relevant news.")
        return

    cache_key = f"news_{'_'.join(sorted(target_tickers))}_{max_articles}"
    if refresh or cache_key not in st.session_state:
        with st.spinner(f"Fetching news for {len(target_tickers)} tickers..."):
            articles = asyncio.run(news_service.get_portfolio_news(portfolio, max_articles=int(max_articles)))
            if filter_ticker:
                articles = [
                    a for a in articles
                    if any(t in (a.relevant_tickers or target_tickers) for t in filter_ticker)
                ]
        st.session_state[cache_key] = articles

    articles = st.session_state.get(cache_key, [])

    # Apply sentiment filter
    if filter_sentiment:
        articles = [a for a in articles if a.sentiment_label in filter_sentiment]

    if not articles:
        st.info("No articles found for the current filters.")
        return

    # Render article cards
    for article in articles:
        with st.container():
            col_main, col_badge = st.columns([5, 1])
            with col_main:
                if article.url:
                    st.markdown(f"#### [{article.title}]({article.url})")
                else:
                    st.markdown(f"#### {article.title}")

                source_date = f"**{article.source}** · {article.published_at.strftime('%b %d, %Y %H:%M UTC')}"
                st.caption(source_date)

                if article.description:
                    st.write(article.description[:300] + "..." if len(article.description or "") > 300 else article.description)

                if article.relevant_tickers:
                    ticker_tags = " ".join(f"`{t}`" for t in article.relevant_tickers[:5])
                    st.markdown(ticker_tags)

            with col_badge:
                st.markdown(
                    sentiment_badge(article.sentiment_label),
                    unsafe_allow_html=True,
                )
                st.caption(f"Score: {float(article.sentiment_score):+.2f}")

        st.divider()


if __name__ == "__main__":
    render_news()
