"""Shared UI components used across multiple Streamlit pages.

GRD-CQ-003: All long-running operations use st.spinner().
GRD-FC-001: Disclaimer banner used on all AI advisory pages.
"""

from decimal import Decimal
from typing import Any, Optional

import streamlit as st

DISCLAIMER_TEXT = (
    "⚠️ **FinApp provides information for educational purposes only.** "
    "Nothing here constitutes financial advice. "
    "Always consult a licensed financial advisor before making investment decisions."
)

DISCLAIMER_STYLE = """
<div style="background-color: #3d2b00; border-left: 4px solid #ffa500;
     padding: 10px 15px; border-radius: 4px; margin-bottom: 16px;">
    ⚠️ <strong>FinApp provides information for educational purposes only.</strong>
    Nothing here constitutes financial advice.
    Always consult a licensed financial advisor before making investment decisions.
</div>
"""


def show_disclaimer_banner() -> None:
    """Render the mandatory financial disclaimer banner (GRD-FC-001)."""
    st.markdown(DISCLAIMER_STYLE, unsafe_allow_html=True)


def color_value(value: float, prefix: str = "$", suffix: str = "") -> str:
    """Format a monetary value with green (positive) or red (negative) color."""
    color = "#43A047" if value >= 0 else "#E53935"
    sign = "+" if value > 0 else ""
    return f'<span style="color:{color}">{sign}{prefix}{value:,.2f}{suffix}</span>'


def color_pct(value: float) -> str:
    """Format a percentage with color coding."""
    color = "#43A047" if value >= 0 else "#E53935"
    sign = "+" if value > 0 else ""
    return f'<span style="color:{color}">{sign}{value:.2f}%</span>'


def sentiment_badge(label: str) -> str:
    """Render a colored sentiment badge."""
    colors = {
        "positive": ("#43A047", "📈"),
        "neutral": ("#9E9E9E", "➡️"),
        "negative": ("#E53935", "📉"),
    }
    color, icon = colors.get(label, ("#9E9E9E", "➡️"))
    return f'<span style="background:{color}; color:white; padding:2px 8px; border-radius:12px; font-size:0.85em;">{icon} {label.capitalize()}</span>'


def metric_row(metrics: list[tuple[str, Any, Optional[Any], Optional[str]]]) -> None:
    """Render a row of st.metric cards.

    Args:
        metrics: List of (label, value, delta, help_text) tuples.
    """
    cols = st.columns(len(metrics))
    for col, (label, value, delta, help_text) in zip(cols, metrics):
        with col:
            st.metric(label=label, value=value, delta=delta, help=help_text)


def staleness_warning(cache_age_seconds: int, threshold_seconds: int = 900) -> None:
    """Show a yellow warning if data is stale (GRD-OPS-003)."""
    if cache_age_seconds > threshold_seconds:
        minutes = cache_age_seconds // 60
        st.warning(f"⚠️ Market data is {minutes} minutes old. Refresh to get current prices.")


def error_card(message: str) -> None:
    """Display an error card in the UI."""
    st.error(f"❌ {message}")


def info_card(message: str) -> None:
    """Display an informational card."""
    st.info(f"ℹ️ {message}")
