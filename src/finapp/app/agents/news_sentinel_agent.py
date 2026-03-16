"""News Sentinel Agent — AGENT-005."""

from typing import Any

from finapp.app.agents.base_agent import BaseAgent


class NewsSentinelAgent(BaseAgent):
    """Monitors financial news and sentiment for portfolio holdings."""

    agent_name = "News Sentinel"

    system_prompt = """You are a financial news analyst who quickly parses large volumes of news
and extracts what matters most for a specific portfolio. You are objective and present
information without editorial bias.

Your responsibilities:
- Fetch and summarize news for portfolio holdings and watchlist items
- Score sentiment of news (positive/neutral/negative)
- Identify high-impact events (earnings surprises, M&A, regulatory actions)
- Provide daily news digests for top portfolio holdings
- Alert on significant news for any holding

Output format:
- Daily digest: Headline | Source | Date | Sentiment | One-sentence summary
- For high-impact news: 2-3 sentence analysis of potential portfolio impact
- Group news by holding for easy scanning
- Flag potential MNPI risks (do not analyze if suspected material non-public information)

GUARDRAILS:
- Do NOT speculate on earnings outcomes before they are released
- If a source is unclear or potentially unreliable, note this explicitly
- Do NOT recommend actions based on news alone
- ALWAYS include: "Past performance does not guarantee future results"
"""

    tools: list[dict[str, Any]] = [
        {
            "name": "get_portfolio",
            "description": "Get portfolio holdings to determine which tickers to monitor",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "search_news",
            "description": "Search financial news by query and/or ticker list",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "tickers": {"type": "array", "items": {"type": "string"}},
                    "from_date": {"type": "string"},
                    "max_articles": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_sentiment_score",
            "description": "Get aggregate sentiment for a ticker or analyze text sentiment",
            "input_schema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "ticker": {"type": "string"},
                    "lookback_days": {"type": "integer", "default": 7},
                },
            },
        },
        {
            "name": "get_sec_filings",
            "description": "Get recent SEC filings for a company",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "filing_types": {"type": "array", "items": {"type": "string"}},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["ticker"],
            },
        },
    ]

    async def _dispatch_tool(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        if tool_name == "get_portfolio":
            from finapp.mcp_servers.portfolio_server import get_portfolio
            return await get_portfolio(**tool_input)
        if tool_name == "search_news":
            from finapp.mcp_servers.news_server import search_news
            return await search_news(**tool_input)
        if tool_name == "get_sentiment_score":
            from finapp.mcp_servers.news_server import get_sentiment_score
            return await get_sentiment_score(**tool_input)
        if tool_name == "get_sec_filings":
            from finapp.mcp_servers.news_server import get_sec_filings
            return await get_sec_filings(**tool_input)
        return await super()._dispatch_tool(tool_name, tool_input)
