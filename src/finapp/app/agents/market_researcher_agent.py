"""Market Researcher Agent — AGENT-004."""

from typing import Any

from finapp.app.agents.base_agent import BaseAgent


class MarketResearcherAgent(BaseAgent):
    """Researches securities using market data, technicals, and web search."""

    agent_name = "Market Researcher"

    system_prompt = """You are a thorough market researcher with both technical analysis and
fundamental analysis skills. You present balanced views and acknowledge uncertainty.

Your responsibilities:
- Look up real-time quotes and price data for any security
- Analyze technical indicators (RSI, MACD, Bollinger Bands, SMA/EMA)
- Review fundamental metrics (P/E, earnings growth, margins, debt)
- Analyze sector trends and macro environment impact
- Compare securities against peers and benchmarks

Output format:
- Provide BOTH bull and bear perspectives for any security analysis
- Include key metrics in a formatted table (use markdown)
- Reference the data source and its freshness
- Do NOT use the word "will" — use "may", "could", "historically has"
- Always note that past performance does not guarantee future results
- Flag when fundamentals and technicals are in conflict

GUARDRAILS:
- Present positive AND negative information — avoid confirmation bias
- Never imply certainty about price direction
- Always note the date of the most recent data used
"""

    tools: list[dict[str, Any]] = [
        {
            "name": "get_quote",
            "description": "Get current quotes for tickers",
            "input_schema": {
                "type": "object",
                "properties": {
                    "tickers": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["tickers"],
            },
        },
        {
            "name": "get_historical_prices",
            "description": "Get OHLCV historical data",
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
            "name": "get_fundamentals",
            "description": "Get fundamental financial metrics for a company",
            "input_schema": {
                "type": "object",
                "properties": {"ticker": {"type": "string"}},
                "required": ["ticker"],
            },
        },
        {
            "name": "get_technical_indicators",
            "description": "Calculate technical indicators (RSI, MACD, SMA, Bollinger Bands)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "indicators": {"type": "array", "items": {"type": "string"}},
                    "period": {"type": "string", "default": "3mo"},
                },
                "required": ["ticker", "indicators"],
            },
        },
        {
            "name": "web_search",
            "description": "Search the web for recent financial news and information",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer", "default": 5},
                    "date_range": {"type": "string", "default": "month"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "search_news",
            "description": "Search financial news by ticker or topic",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "tickers": {"type": "array", "items": {"type": "string"}},
                    "max_articles": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        },
    ]

    async def _dispatch_tool(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        if tool_name == "get_quote":
            from finapp.mcp_servers.market_data_server import get_quote
            return await get_quote(**tool_input)
        if tool_name == "get_historical_prices":
            from finapp.mcp_servers.market_data_server import get_historical_prices
            return await get_historical_prices(**tool_input)
        if tool_name == "get_fundamentals":
            from finapp.mcp_servers.market_data_server import get_fundamentals
            return await get_fundamentals(**tool_input)
        if tool_name == "get_technical_indicators":
            from finapp.mcp_servers.market_data_server import get_technical_indicators
            return await get_technical_indicators(**tool_input)
        if tool_name == "web_search":
            from finapp.mcp_servers.search_server import web_search
            return await web_search(**tool_input)
        if tool_name == "search_news":
            from finapp.mcp_servers.news_server import search_news
            return await search_news(**tool_input)
        return await super()._dispatch_tool(tool_name, tool_input)
