"""Trade Reviewer Agent — AGENT-007.

GRD-FC-002: NEVER says "proceed with this trade". Only presents considerations.
"""

from typing import Any

from finapp.app.agents.base_agent import BaseAgent


class TradeReviewerAgent(BaseAgent):
    """Reviews proposed trades for risk impact, tax implications, and portfolio fit."""

    agent_name = "Trade Reviewer"

    system_prompt = """You are a careful trade reviewer — the last line of defense before
a user takes action on a proposed transaction. You evaluate the FULL impact.

Your responsibilities:
- Analyze impact of a proposed trade on portfolio metrics
- Calculate tax implications (short vs long-term capital gains)
- Check for potential wash sale rule considerations
- Assess concentration change from the trade
- Flag unusually large position sizes

Output format (always use this checklist structure):
- ✅ or ⚠️ or ❌ for each factor:
  * Market context (current price vs entry, recent trend)
  * Portfolio impact (concentration change, allocation shift)
  * Risk impact (how does this change overall portfolio risk?)
  * Tax considerations (estimated gain/loss, LT vs ST treatment)
  * Wash sale check (sold similar security in past 30 days?)
- Show before/after portfolio allocation percentages
- Estimated tax impact clearly shown
- Summary: "Key considerations to weigh before proceeding:"

GUARDRAILS:
- NEVER say "proceed with this trade" or "this is a good trade"
- ONLY present considerations — the decision is always the user's
- Always note: "Verify current prices before trading — this analysis uses data as of [timestamp]"
- Flag trades resulting in > 20% portfolio change with ❌ warning
- Include the mandatory financial disclaimer
"""

    tools: list[dict[str, Any]] = [
        {
            "name": "get_portfolio",
            "description": "Get current portfolio to analyze impact of proposed trade",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "get_quote",
            "description": "Get current price for the security being considered",
            "input_schema": {
                "type": "object",
                "properties": {
                    "tickers": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["tickers"],
            },
        },
        {
            "name": "get_transactions",
            "description": "Review recent transactions for wash sale analysis",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "from_date": {"type": "string"},
                    "limit": {"type": "integer", "default": 20},
                },
            },
        },
        {
            "name": "tool_calculate_tax_impact",
            "description": "Estimate capital gains tax for a proposed sale",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "quantity": {"type": "number"},
                    "purchase_price": {"type": "number"},
                    "sale_price": {"type": "number"},
                    "purchase_date_days_ago": {"type": "integer"},
                },
                "required": ["ticker", "quantity", "purchase_price", "sale_price", "purchase_date_days_ago"],
            },
        },
    ]

    async def _dispatch_tool(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        if tool_name == "get_portfolio":
            from finapp.mcp_servers.portfolio_server import get_portfolio
            return await get_portfolio(**tool_input)
        if tool_name == "get_quote":
            from finapp.mcp_servers.market_data_server import get_quote
            return await get_quote(**tool_input)
        if tool_name == "get_transactions":
            from finapp.mcp_servers.portfolio_server import get_transactions
            return await get_transactions(**tool_input)
        if tool_name == "tool_calculate_tax_impact":
            from finapp.mcp_servers.calculator_server import tool_calculate_tax_impact
            return tool_calculate_tax_impact(**tool_input)
        return await super()._dispatch_tool(tool_name, tool_input)
