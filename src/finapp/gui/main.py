"""FinApp Streamlit application entry point.

Start with: uv run streamlit run src/finapp/gui/main.py
"""

import asyncio
import logging

import streamlit as st

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _configure_page() -> None:
    """Configure global Streamlit page settings from gui.yaml spec."""
    st.set_page_config(
        page_title="FinApp",
        page_icon="💼",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def _apply_theme() -> None:
    """Inject custom CSS for the FinApp dark theme."""
    st.markdown(
        """
        <style>
        /* FinApp custom theme */
        .stMetric { background: #1e2130; border-radius: 8px; padding: 12px; }
        .stMetric label { color: #9E9E9E !important; font-size: 0.85em; }
        .stMetric [data-testid="metric-container"] { padding: 8px; }
        .positive { color: #43A047; }
        .negative { color: #E53935; }
        div[data-testid="stSidebarNav"] { padding-top: 1rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sidebar() -> None:
    """Render the navigation sidebar."""
    with st.sidebar:
        st.title("💼 FinApp")
        st.caption("AI-Enabled Financial Application")
        st.divider()

        # Navigation
        st.page_link("src/finapp/gui/main.py", label="📊 Dashboard", icon="📊")
        st.page_link("src/finapp/gui/pages/portfolio.py", label="💼 Portfolio", icon="💼")
        st.page_link("src/finapp/gui/pages/ai_advisor.py", label="🤖 AI Advisor", icon="🤖")
        st.page_link("src/finapp/gui/pages/market.py", label="📈 Market Data", icon="📈")
        st.page_link("src/finapp/gui/pages/risk.py", label="⚠️ Risk Analysis", icon="⚠️")
        st.page_link("src/finapp/gui/pages/news.py", label="📰 News", icon="📰")
        st.page_link("src/finapp/gui/pages/settings.py", label="⚙️ Settings", icon="⚙️")

        st.divider()
        st.caption("v0.1.0 | claude-sonnet-4-6")


def main() -> None:
    """Main entry point — renders the Dashboard as the home page."""
    _configure_page()
    _apply_theme()

    # Initialize database on first run
    if "db_initialized" not in st.session_state:
        with st.spinner("Initialising database..."):
            asyncio.run(_init_db())
        st.session_state.db_initialized = True

    # Render Dashboard as home
    from finapp.gui.pages.dashboard import render_dashboard
    render_dashboard()


async def _init_db() -> None:
    """Create database tables if they don't exist."""
    from finapp.infrastructure.database import create_all_tables
    await create_all_tables()


if __name__ == "__main__":
    main()
