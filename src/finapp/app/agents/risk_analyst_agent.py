"""Risk Analyst Agent — AGENT-003."""

from typing import Any

from finapp.app.agents.base_agent import BaseAgent


class RiskAnalystAgent(BaseAgent):
    """Quantifies and explains portfolio risk. Conducts stress tests."""

    agent_name = "Risk Analyst"

    system_prompt = """You are a quantitative risk analyst with expertise in portfolio risk measurement.
You are precise with numbers, explain statistical concepts in plain language, and never minimize
the significance of downside risks.

Your responsibilities:
- Calculate Value at Risk (VaR) at various confidence levels
- Analyze portfolio volatility and potential drawdown
- Run historical stress tests (2008, 2020, 2022, custom)
- Identify correlation concentration risks
- Explain risk metrics in plain language

Output format:
- Lead with the most critical risk finding
- Express VaR as: "With 95% confidence, the maximum 1-day loss is $X (Y%)"
- Include a plain-language explanation of what each metric means
- Stress test results must show dollar loss, not just percentage
- Always present best-case AND worst-case scenarios

GUARDRAILS:
- Never frame risk as negligible or trivial
- Always present both upside and downside scenarios
- Be explicit about assumptions underlying any calculation
- Use "estimated", "historical simulation suggests", "based on past data"
"""

    tools: list[dict[str, Any]] = [
        {
            "name": "get_portfolio",
            "description": "Get portfolio with holdings",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "get_historical_prices",
            "description": "Get historical price data for calculating returns",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "period": {"type": "string", "default": "1y"},
                    "interval": {"type": "string", "default": "1d"},
                },
                "required": ["ticker"],
            },
        },
        {
            "name": "tool_calculate_var",
            "description": "Calculate Value at Risk using historical simulation",
            "input_schema": {
                "type": "object",
                "properties": {
                    "portfolio_returns": {"type": "array", "items": {"type": "number"}},
                    "confidence_level": {"type": "number", "default": 0.95},
                    "holding_period_days": {"type": "integer", "default": 1},
                    "portfolio_value": {"type": "number"},
                },
                "required": ["portfolio_returns", "portfolio_value"],
            },
        },
        {
            "name": "tool_calculate_sharpe",
            "description": "Calculate Sharpe ratio, Sortino ratio, and max drawdown",
            "input_schema": {
                "type": "object",
                "properties": {
                    "returns": {"type": "array", "items": {"type": "number"}},
                    "risk_free_rate_annual": {"type": "number", "default": 0.05},
                },
                "required": ["returns"],
            },
        },
        {
            "name": "tool_run_stress_test",
            "description": "Simulate portfolio under historical crash scenario",
            "input_schema": {
                "type": "object",
                "properties": {
                    "holdings": {"type": "array"},
                    "scenario": {"type": "string"},
                    "portfolio_value": {"type": "number"},
                    "custom_shock_pct": {"type": "number"},
                },
                "required": ["holdings", "scenario", "portfolio_value"],
            },
        },
    ]

    async def _dispatch_tool(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        if tool_name == "get_portfolio":
            from finapp.mcp_servers.portfolio_server import get_portfolio
            return await get_portfolio(**tool_input)
        if tool_name == "get_historical_prices":
            from finapp.mcp_servers.market_data_server import get_historical_prices
            return await get_historical_prices(**tool_input)
        if tool_name == "tool_calculate_var":
            from finapp.mcp_servers.calculator_server import tool_calculate_var
            return tool_calculate_var(**tool_input)
        if tool_name == "tool_calculate_sharpe":
            from finapp.mcp_servers.calculator_server import tool_calculate_sharpe
            return tool_calculate_sharpe(**tool_input)
        if tool_name == "tool_run_stress_test":
            from finapp.mcp_servers.calculator_server import tool_run_stress_test
            return tool_run_stress_test(**tool_input)
        return await super()._dispatch_tool(tool_name, tool_input)
