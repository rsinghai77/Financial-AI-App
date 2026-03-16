"""AI Financial Advisor Page — PAGE-003.

Streaming chat interface for interacting with all AI agents.
GRD-FC-001: Mandatory disclaimer banner always visible.
GRD-CQ-003: Streaming via st.write_stream.
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import streamlit as st

from finapp.gui.components.shared import show_disclaimer_banner


def _stream_to_sync(async_gen: AsyncGenerator[str, Any]):
    """Convert async generator to sync generator for st.write_stream."""
    loop = asyncio.new_event_loop()
    try:
        while True:
            try:
                yield loop.run_until_complete(async_gen.__anext__())
            except StopAsyncIteration:
                break
    finally:
        loop.close()


def render_ai_advisor() -> None:
    """Render the AI Financial Advisor chat page."""
    st.title("🤖 AI Financial Advisor")

    # GRD-FC-001: Mandatory disclaimer — always visible on this page
    show_disclaimer_banner()

    # -------------------------------------------------------------------------
    # Agent selector
    # -------------------------------------------------------------------------
    agent_options = {
        "🤖 FinApp Assistant (auto-route)": "auto",
        "📊 Portfolio Advisor": "portfolio",
        "⚠️ Risk Analyst": "risk",
        "🔍 Market Researcher": "market",
        "📰 News Sentinel": "news",
        "🎯 Financial Planner": "planner",
        "✅ Trade Reviewer": "trade",
    }
    selected_label = st.selectbox("Chat with", options=list(agent_options.keys()))
    agent_key = agent_options[selected_label]

    # -------------------------------------------------------------------------
    # Session state: conversation history
    # -------------------------------------------------------------------------
    history_key = f"chat_history_{agent_key}"
    if history_key not in st.session_state:
        st.session_state[history_key] = []

    # -------------------------------------------------------------------------
    # Quick prompts
    # -------------------------------------------------------------------------
    st.write("**Quick questions:**")
    quick_cols = st.columns(3)
    quick_prompts = [
        "Summarize my portfolio performance",
        "What are my biggest risk exposures?",
        "Show recent news for my holdings",
        "How am I tracking vs S&P 500?",
        "Suggest how to better diversify",
        "What is my current asset allocation?",
    ]
    if "quick_prompt" not in st.session_state:
        st.session_state.quick_prompt = ""

    for i, prompt in enumerate(quick_prompts):
        with quick_cols[i % 3]:
            if st.button(prompt, key=f"qp_{i}", use_container_width=True):
                st.session_state.quick_prompt = prompt

    st.divider()

    # -------------------------------------------------------------------------
    # Chat history display
    # -------------------------------------------------------------------------
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state[history_key]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # -------------------------------------------------------------------------
    # Chat input
    # -------------------------------------------------------------------------
    user_input = st.chat_input("Ask me about your portfolio, market trends, risks...")

    # Use quick prompt if set
    if st.session_state.quick_prompt:
        user_input = st.session_state.quick_prompt
        st.session_state.quick_prompt = ""

    if user_input:
        # Add user message to history and display it
        st.session_state[history_key].append({"role": "user", "content": user_input})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_input)

        # Build conversation history for the agent (last 10 messages)
        history = st.session_state[history_key][:-1]  # Exclude the current user message
        conv_history = [
            {"role": m["role"], "content": m["content"]}
            for m in history[-10:]  # Keep last 10 for context
        ]

        # Get the appropriate agent
        agent = _get_agent(agent_key)

        # Stream response
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    async_gen = agent.stream_response(user_input, conv_history)
                    response_text = st.write_stream(_stream_to_sync(async_gen))

        # Save assistant response to history
        st.session_state[history_key].append({
            "role": "assistant",
            "content": response_text or "",
        })

    # -------------------------------------------------------------------------
    # Sidebar controls
    # -------------------------------------------------------------------------
    with st.sidebar:
        st.divider()
        if st.button("🗑️ Clear Chat History"):
            st.session_state[history_key] = []
            st.rerun()

        if st.session_state[history_key]:
            chat_text = "\n\n".join(
                f"**{m['role'].capitalize()}:** {m['content']}"
                for m in st.session_state[history_key]
            )
            st.download_button(
                "💾 Export Chat",
                data=chat_text,
                file_name="finapp_chat.md",
                mime="text/markdown",
            )


def _get_agent(agent_key: str):
    """Instantiate the requested agent."""
    from finapp.app.agents.financial_planner_agent import FinancialPlannerAgent
    from finapp.app.agents.market_researcher_agent import MarketResearcherAgent
    from finapp.app.agents.news_sentinel_agent import NewsSentinelAgent
    from finapp.app.agents.orchestrator_agent import OrchestratorAgent
    from finapp.app.agents.portfolio_advisor_agent import PortfolioAdvisorAgent
    from finapp.app.agents.risk_analyst_agent import RiskAnalystAgent
    from finapp.app.agents.trade_reviewer_agent import TradeReviewerAgent

    agents = {
        "auto": OrchestratorAgent,
        "portfolio": PortfolioAdvisorAgent,
        "risk": RiskAnalystAgent,
        "market": MarketResearcherAgent,
        "news": NewsSentinelAgent,
        "planner": FinancialPlannerAgent,
        "trade": TradeReviewerAgent,
    }
    return agents.get(agent_key, OrchestratorAgent)()


if __name__ == "__main__":
    render_ai_advisor()
