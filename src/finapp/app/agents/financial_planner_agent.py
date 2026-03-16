"""Financial Planner Agent — AGENT-006."""

from typing import Any

from finapp.app.agents.base_agent import BaseAgent


class FinancialPlannerAgent(BaseAgent):
    """Helps users set and track long-term financial goals."""

    agent_name = "Financial Planner"

    system_prompt = """You are a compassionate financial planning assistant who helps users think
clearly about their long-term financial goals. You focus on behavior and process, not just numbers.

Your responsibilities:
- Help users define SMART financial goals (Specific, Measurable, Achievable, Relevant, Time-bound)
- Calculate required savings rates to reach goals
- Project portfolio growth under different scenarios
- Analyze retirement readiness
- Identify gaps between current trajectory and goals

Output format:
- Use projection tables with three scenarios:
  * Conservative: assumed return 2% below base
  * Base: user's stated assumption (default 7%)
  * Optimistic: assumed return 2% above base
- Clearly state ALL assumptions (return rate, inflation, contribution growth)
- Express goals in both present value and future value terms
- Use plain language and avoid excessive jargon

GUARDRAILS:
- Always use CONSERVATIVE return assumptions as the baseline (5-6% real return)
- Inflation assumption MUST always be included (default 3%)
- NEVER guarantee retirement readiness — always use "projected" and "estimated"
- Include: "Past performance does not guarantee future results" in all projections
"""

    tools: list[dict[str, Any]] = [
        {
            "name": "get_portfolio",
            "description": "Get current portfolio value as starting point for projections",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "tool_project_future_value",
            "description": "Project future value with contributions (includes 3 scenarios)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "initial_value": {"type": "number"},
                    "annual_return_rate": {"type": "number"},
                    "years": {"type": "integer"},
                    "monthly_contribution": {"type": "number", "default": 0},
                    "inflation_rate": {"type": "number", "default": 0.03},
                },
                "required": ["initial_value", "annual_return_rate", "years"],
            },
        },
        {
            "name": "tool_calculate_irr",
            "description": "Calculate IRR for a series of cash flows",
            "input_schema": {
                "type": "object",
                "properties": {
                    "cash_flows": {"type": "array", "items": {"type": "number"}},
                    "dates": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["cash_flows"],
            },
        },
    ]

    async def _dispatch_tool(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        if tool_name == "get_portfolio":
            from finapp.mcp_servers.portfolio_server import get_portfolio
            return await get_portfolio(**tool_input)
        if tool_name == "tool_project_future_value":
            from finapp.mcp_servers.calculator_server import tool_project_future_value
            return tool_project_future_value(**tool_input)
        if tool_name == "tool_calculate_irr":
            from finapp.mcp_servers.calculator_server import tool_calculate_irr
            return tool_calculate_irr(**tool_input)
        return await super()._dispatch_tool(tool_name, tool_input)
