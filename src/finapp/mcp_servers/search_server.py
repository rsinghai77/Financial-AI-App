"""Web Search MCP Server — MCP-005.

Provides web search via Brave Search API for market research agent.
GRD-SEC-005: Only search queries sent — never portfolio data.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from mcp.server import FastMCP

from finapp.config import settings

logger = logging.getLogger(__name__)
mcp = FastMCP("search-mcp")


@mcp.tool()
async def web_search(
    query: str,
    max_results: int = 5,
    date_range: str = "month",
) -> list[dict[str, Any]]:
    """Search the web for financial information using Brave Search.

    Args:
        query: Search query string.
        max_results: Maximum results to return (1–10).
        date_range: Freshness filter — "day","week","month","year","all".

    Returns:
        List of search result dicts with title, url, description.
    """
    max_results = min(max(max_results, 1), 10)

    # Map date_range to Brave API freshness parameter
    freshness_map = {
        "day": "pd",
        "week": "pw",
        "month": "pm",
        "year": "py",
        "all": None,
    }
    freshness = freshness_map.get(date_range)

    if not settings.brave_search_api_key:
        return [{
            "title": "Brave Search not configured",
            "url": "",
            "description": (
                "Configure BRAVE_SEARCH_API_KEY in .env to enable web search. "
                "Get a free key at brave.com/search/api/"
            ),
            "published_date": None,
        }]

    params: dict[str, Any] = {
        "q": query,
        "count": max_results,
        "search_lang": "en",
        "country": "us",
    }
    if freshness:
        params["freshness"] = freshness

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                settings.brave_search_base_url,
                params=params,
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": settings.brave_search_api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("Brave Search HTTP error: %s", exc)
        return [{"error": f"Search API error: {exc.response.status_code}"}]
    except Exception as exc:
        logger.error("Brave Search error: %s", exc)
        return [{"error": str(exc)}]

    results = []
    for item in data.get("web", {}).get("results", [])[:max_results]:
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "description": item.get("description", ""),
            "published_date": item.get("page_age"),
        })

    return results


if __name__ == "__main__":
    mcp.run(transport="stdio")
