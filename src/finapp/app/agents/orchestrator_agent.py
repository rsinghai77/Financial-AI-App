"""Orchestrator Agent — AGENT-001.

Primary entry point for all user interactions. Routes queries to specialist agents.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any, Optional

from finapp.app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Routes user queries to the most appropriate specialist agent.

    For simple queries, responds directly. For complex queries, chains
    multiple specialist agents and aggregates their responses.
    """

    agent_name = "FinApp Assistant"

    system_prompt = """You are the FinApp Assistant — a knowledgeable, concise, and helpful
financial companion. You understand financial concepts deeply and route complex questions
to the right specialist context.

When users ask about:
- Portfolio holdings, allocation, performance → analyze their portfolio data
- Risk, VaR, drawdown, volatility → provide risk-focused analysis
- Stock prices, charts, technical/fundamental data → provide market research
- News, earnings, events → provide news and sentiment analysis
- Goals, retirement, savings, budget → provide financial planning perspective
- Proposed trades, buy/sell decisions → provide trade review analysis

Always be concise and data-driven. If you don't have access to real-time data,
say so clearly and offer what analysis you can with available information.

Remember: You MUST include the financial disclaimer in every response that contains
investment analysis or market commentary."""

    tools: list[dict[str, Any]] = [
        {
            "name": "get_portfolio",
            "description": "Get the user's complete portfolio including all holdings and accounts",
            "input_schema": {
                "type": "object",
                "properties": {
                    "include_closed": {
                        "type": "boolean",
                        "description": "Include closed/sold positions",
                        "default": False,
                    }
                },
            },
        },
    ]

    # Intent routing keywords
    INTENT_MAP = {
        "portfolio_advisor": ["portfolio", "holdings", "allocation", "rebalance", "diversify", "position"],
        "risk_analyst": ["risk", "volatility", "var", "drawdown", "beta", "exposure", "stress"],
        "market_researcher": ["price", "market", "stock", "chart", "technical", "rsi", "macd", "pe ratio"],
        "news_sentinel": ["news", "sentiment", "earnings", "announcement", "event", "filing"],
        "financial_planner": ["goal", "retire", "retirement", "budget", "savings", "projection", "plan"],
        "trade_reviewer": ["buy", "sell", "trade", "order", "wash sale", "tax loss"],
    }

    def _classify_intent(self, message: str) -> str:
        """Simple keyword-based intent classification."""
        msg_lower = message.lower()
        scores: dict[str, int] = {}
        for intent, keywords in self.INTENT_MAP.items():
            scores[intent] = sum(1 for kw in keywords if kw in msg_lower)
        best = max(scores, key=lambda k: scores[k])
        return best if scores[best] > 0 else "general"

    async def stream_response(
        self,
        user_message: str,
        conversation_history: Optional[list[dict[str, Any]]] = None,
        tool_results: Optional[list[dict[str, Any]]] = None,
    ) -> AsyncGenerator[str, None]:
        """Route to specialist agent or handle directly."""
        intent = self._classify_intent(user_message)
        logger.info("Orchestrator classified intent: %s", intent)

        # Import specialist agents lazily to avoid circular imports
        agent: BaseAgent
        if intent == "portfolio_advisor":
            from finapp.app.agents.portfolio_advisor_agent import PortfolioAdvisorAgent
            agent = PortfolioAdvisorAgent()
        elif intent == "risk_analyst":
            from finapp.app.agents.risk_analyst_agent import RiskAnalystAgent
            agent = RiskAnalystAgent()
        elif intent == "market_researcher":
            from finapp.app.agents.market_researcher_agent import MarketResearcherAgent
            agent = MarketResearcherAgent()
        elif intent == "news_sentinel":
            from finapp.app.agents.news_sentinel_agent import NewsSentinelAgent
            agent = NewsSentinelAgent()
        elif intent == "financial_planner":
            from finapp.app.agents.financial_planner_agent import FinancialPlannerAgent
            agent = FinancialPlannerAgent()
        elif intent == "trade_reviewer":
            from finapp.app.agents.trade_reviewer_agent import TradeReviewerAgent
            agent = TradeReviewerAgent()
        else:
            agent = self  # Handle general queries directly

        if agent is not self:
            yield f"*Routing to {agent.agent_name}...*\n\n"

        async for chunk in BaseAgent.stream_response(
            agent, user_message, conversation_history, tool_results
        ):
            yield chunk

    async def _dispatch_tool(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Dispatch portfolio tool calls."""
        if tool_name == "get_portfolio":
            from finapp.mcp_servers.portfolio_server import get_portfolio
            return await get_portfolio(**tool_input)
        return await super()._dispatch_tool(tool_name, tool_input)
