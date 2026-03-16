"""Portfolio Advisor Agent — AGENT-002."""

from typing import Any

from finapp.app.agents.base_agent import BaseAgent


class PortfolioAdvisorAgent(BaseAgent):
    """Provides portfolio analysis and rebalancing recommendations."""

    agent_name = "Portfolio Advisor"

    system_prompt = """You are a seasoned portfolio advisor with deep knowledge of asset allocation,
diversification, and factor investing. You analyze portfolios objectively and provide balanced
perspectives on opportunities and risks.

Your responsibilities:
- Analyze current portfolio composition and identify imbalances
- Suggest rebalancing strategies when allocation drifts from targets
- Identify concentration risks and over-exposure (flag >10% in single position)
- Provide tax-efficient investment considerations
- Explain portfolio performance drivers

Output format:
- Start with a 2-3 sentence summary of key findings
- Use bullet points for specific observations and recommendations
- Include relevant metrics in structured format
- End with the mandatory disclaimer

GUARDRAILS:
- Never recommend a specific dollar amount to invest without major caveats
- Always consider tax implications of position changes
- Flag concentration when a single position exceeds 10% of portfolio
- Use "consider", "may want to explore", "historically" — never "you should" or "guaranteed"
"""

    tools: list[dict[str, Any]] = [
        {
            "name": "get_portfolio",
            "description": "Get complete portfolio with all holdings and accounts",
            "input_schema": {
                "type": "object",
                "properties": {
                    "include_closed": {"type": "boolean", "default": False}
                },
            },
        },
        {
            "name": "get_quote",
            "description": "Get current market quotes for tickers",
            "input_schema": {
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of ticker symbols",
                    }
                },
                "required": ["tickers"],
            },
        },
        {
            "name": "get_fundamentals",
            "description": "Get fundamental financial data for a company",
            "input_schema": {
                "type": "object",
                "properties": {"ticker": {"type": "string"}},
                "required": ["ticker"],
            },
        },
        {
            "name": "tool_calculate_sharpe",
            "description": "Calculate Sharpe and Sortino ratios for a return series",
            "input_schema": {
                "type": "object",
                "properties": {
                    "returns": {"type": "array", "items": {"type": "number"}},
                    "risk_free_rate_annual": {"type": "number", "default": 0.05},
                },
                "required": ["returns"],
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
        if tool_name == "get_fundamentals":
            from finapp.mcp_servers.market_data_server import get_fundamentals
            return await get_fundamentals(**tool_input)
        if tool_name == "tool_calculate_sharpe":
            from finapp.mcp_servers.calculator_server import tool_calculate_sharpe
            return tool_calculate_sharpe(**tool_input)
        return await super()._dispatch_tool(tool_name, tool_input)
