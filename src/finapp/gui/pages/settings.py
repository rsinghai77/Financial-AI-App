"""Settings Page — PAGE-007.

Tabs: API Keys | Portfolio Settings | Preferences
GRD-SEC-001: API keys stored only in .env — never in database or session state.
"""

import os
from pathlib import Path

import streamlit as st


def render_settings() -> None:
    """Render the Settings page."""
    st.title("⚙️ Settings")

    tab_keys, tab_portfolio, tab_prefs = st.tabs(["🔑 API Keys", "💼 Portfolio", "🎛️ Preferences"])

    # -------------------------------------------------------------------------
    # TAB: API Keys
    # -------------------------------------------------------------------------
    with tab_keys:
        st.subheader("API Key Configuration")
        st.info(
            "API keys are saved to your local `.env` file and are **never** stored in the "
            "application database. The `.env` file is excluded from version control."
        )

        env_path = Path(".env")
        current_env: dict[str, str] = {}
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    current_env[key.strip()] = value.strip()

        with st.form("api_keys_form"):
            anthropic_key = st.text_input(
                "Anthropic API Key *",
                value=current_env.get("ANTHROPIC_API_KEY", ""),
                type="password",
                help="Required for all AI features. Get yours at console.anthropic.com",
            )
            alpha_key = st.text_input(
                "Alpha Vantage API Key",
                value=current_env.get("ALPHA_VANTAGE_API_KEY", ""),
                type="password",
                help="For enhanced market data. Free tier: 5 requests/minute.",
            )
            news_key = st.text_input(
                "NewsAPI Key",
                value=current_env.get("NEWS_API_KEY", ""),
                type="password",
                help="For financial news. Free tier: 100 requests/day.",
            )
            brave_key = st.text_input(
                "Brave Search API Key",
                value=current_env.get("BRAVE_SEARCH_API_KEY", ""),
                type="password",
                help="For web search in the Market Researcher agent.",
            )

            save_btn = st.form_submit_button("💾 Save API Keys", type="primary")

        if save_btn:
            _save_env_keys({
                "ANTHROPIC_API_KEY": anthropic_key,
                "ALPHA_VANTAGE_API_KEY": alpha_key,
                "NEWS_API_KEY": news_key,
                "BRAVE_SEARCH_API_KEY": brave_key,
            })
            st.success("✅ API keys saved to .env file. Restart the application to apply changes.")

        # Connection status
        st.subheader("Connection Status")
        status_col1, status_col2 = st.columns(2)
        with status_col1:
            anthropic_configured = bool(current_env.get("ANTHROPIC_API_KEY"))
            st.metric("Claude AI", "✅ Configured" if anthropic_configured else "❌ Not configured")
            alpha_configured = bool(current_env.get("ALPHA_VANTAGE_API_KEY"))
            st.metric("Alpha Vantage", "✅ Configured" if alpha_configured else "⚠️ Using yfinance fallback")
        with status_col2:
            news_configured = bool(current_env.get("NEWS_API_KEY"))
            st.metric("NewsAPI", "✅ Configured" if news_configured else "⚠️ News disabled")
            brave_configured = bool(current_env.get("BRAVE_SEARCH_API_KEY"))
            st.metric("Brave Search", "✅ Configured" if brave_configured else "⚠️ Web search disabled")

    # -------------------------------------------------------------------------
    # TAB: Portfolio Settings
    # -------------------------------------------------------------------------
    with tab_portfolio:
        st.subheader("Portfolio Settings")

        if "settings" not in st.session_state:
            st.session_state.settings = {
                "base_currency": "USD",
                "default_benchmark": "SPY",
                "risk_free_rate": 5.0,
                "large_position_threshold": 10.0,
            }

        with st.form("portfolio_settings_form"):
            currency = st.selectbox(
                "Base Currency",
                options=["USD", "EUR", "GBP", "CAD", "AUD"],
                index=["USD", "EUR", "GBP", "CAD", "AUD"].index(
                    st.session_state.settings.get("base_currency", "USD")
                ),
            )
            benchmark = st.selectbox(
                "Default Benchmark",
                options=["SPY", "QQQ", "DIA", "IWM", "VTI"],
                index=["SPY", "QQQ", "DIA", "IWM", "VTI"].index(
                    st.session_state.settings.get("default_benchmark", "SPY")
                ),
            )
            risk_free_rate = st.number_input(
                "Risk-Free Rate (%)",
                min_value=0.0, max_value=20.0, step=0.1,
                value=float(st.session_state.settings.get("risk_free_rate", 5.0)),
                help="Used in Sharpe ratio calculations (typically the 3-month T-bill rate)",
            )
            large_pos_threshold = st.number_input(
                "Large Position Warning Threshold (%)",
                min_value=1.0, max_value=100.0, step=1.0,
                value=float(st.session_state.settings.get("large_position_threshold", 10.0)),
                help="Warn when a single holding exceeds this % of total portfolio",
            )
            port_save = st.form_submit_button("Save Portfolio Settings")

        if port_save:
            st.session_state.settings.update({
                "base_currency": currency,
                "default_benchmark": benchmark,
                "risk_free_rate": risk_free_rate,
                "large_position_threshold": large_pos_threshold,
            })
            st.success("✅ Portfolio settings saved for this session.")

    # -------------------------------------------------------------------------
    # TAB: Preferences
    # -------------------------------------------------------------------------
    with tab_prefs:
        st.subheader("Display Preferences")

        if "prefs" not in st.session_state:
            st.session_state.prefs = {
                "refresh_interval": 5,
                "decimal_places": 2,
            }

        with st.form("prefs_form"):
            refresh_interval = st.slider(
                "Market data refresh interval (minutes)",
                min_value=1, max_value=60,
                value=st.session_state.prefs.get("refresh_interval", 5),
            )
            decimal_places = st.selectbox(
                "Decimal places for prices",
                options=[2, 4, 6],
                index=[2, 4, 6].index(st.session_state.prefs.get("decimal_places", 2)),
            )
            prefs_save = st.form_submit_button("Save Preferences")

        if prefs_save:
            st.session_state.prefs.update({
                "refresh_interval": refresh_interval,
                "decimal_places": decimal_places,
            })
            st.success("✅ Preferences saved.")

        st.divider()
        st.subheader("Cache Management")
        if st.button("🗑️ Clear Market Data Cache"):
            from finapp.infrastructure.cache.market_data_cache import get_cache
            get_cache().clear()
            st.success("✅ Market data cache cleared.")


def _save_env_keys(keys: dict[str, str]) -> None:
    """Write API keys to the .env file, preserving existing non-API-key lines."""
    env_path = Path(".env")
    existing_lines: list[str] = []

    managed_keys = set(keys.keys())
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line_key = line.split("=")[0].strip()
            if line_key not in managed_keys:
                existing_lines.append(line)

    new_lines = existing_lines + [f"{k}={v}" for k, v in keys.items() if v]

    env_path.write_text("\n".join(new_lines) + "\n")


if __name__ == "__main__":
    render_settings()
