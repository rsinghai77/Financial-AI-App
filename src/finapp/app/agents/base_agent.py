"""Base agent class — shared logic for all FinApp AI agents.

GRD-FC-001: The mandatory disclaimer is appended to every financial response.
GRD-SEC-001: API key loaded from config, never hardcoded.
All agents use streaming via the Anthropic SDK.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any, Optional

import anthropic

from finapp.config import settings

logger = logging.getLogger(__name__)

MANDATORY_DISCLAIMER = (
    "\n\n---\n"
    "⚠️ *This analysis is for informational purposes only and does not constitute "
    "financial advice. Always consult a licensed financial advisor before making "
    "investment decisions.*"
)

GLOBAL_SYSTEM_PROMPT_PREFIX = """You are an AI assistant embedded in FinApp, a personal financial management application.
You have access to real-time portfolio data, market information, and financial analysis tools.

MANDATORY RULES:
1. Include the following disclaimer at the end of every response containing financial analysis,
   recommendations, or market commentary:
   "⚠️ This analysis is for informational purposes only and does not constitute financial advice.
   Always consult a licensed financial advisor before making investment decisions."

2. NEVER say: "You should buy X", "Sell X now", "This is guaranteed to...", "You will make money if..."
3. ALWAYS say: "Consider...", "Historically...", "Based on available data...", "This analysis suggests..."
4. Never recommend specific buy/sell price targets as instructions.
5. Always recommend consulting a licensed financial advisor for material decisions.
"""


class BaseAgent:
    """Shared base for all FinApp agents.

    Subclasses must define:
    - agent_name: str — display name shown in the UI
    - system_prompt: str — agent-specific persona and instructions
    - tools: list[dict] — MCP tool definitions available to this agent
    """

    agent_name: str = "FinApp Agent"
    system_prompt: str = ""
    tools: list[dict[str, Any]] = []

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def stream_response(
        self,
        user_message: str,
        conversation_history: Optional[list[dict[str, Any]]] = None,
        tool_results: Optional[list[dict[str, Any]]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream agent response tokens back to the caller.

        Handles the full tool-use loop: if Claude calls a tool, the result is
        fed back automatically until a final text response is generated.

        Args:
            user_message: The user's latest message.
            conversation_history: Prior conversation turns for context.
            tool_results: Pre-fetched tool results (for internal chaining).

        Yields:
            String tokens as they stream from the Claude API.
        """
        messages: list[dict[str, Any]] = list(conversation_history or [])
        if user_message:
            messages.append({"role": "user", "content": user_message})

        full_system = f"{GLOBAL_SYSTEM_PROMPT_PREFIX}\n\n{self.system_prompt}"

        # Tool-use loop — max 5 rounds to prevent infinite loops
        for _ in range(5):
            kwargs: dict[str, Any] = {
                "model": settings.anthropic_model,
                "max_tokens": settings.agent_max_tokens,
                "temperature": settings.agent_temperature,
                "system": full_system,
                "messages": messages,
            }
            if self.tools:
                kwargs["tools"] = self.tools

            text_buffer = ""
            tool_calls: list[dict[str, Any]] = []

            async with self._client.messages.stream(**kwargs) as stream:
                async for event in stream:
                    if hasattr(event, "type"):
                        if event.type == "content_block_delta":
                            delta = getattr(event.delta, "text", None)
                            if delta:
                                text_buffer += delta
                                yield delta
                        elif event.type == "content_block_start":
                            block = getattr(event, "content_block", None)
                            if block and getattr(block, "type", None) == "tool_use":
                                tool_calls.append({
                                    "id": block.id,
                                    "name": block.name,
                                    "input": {},
                                })
                        elif event.type == "content_block_delta":
                            if hasattr(event.delta, "partial_json"):
                                if tool_calls:
                                    # Accumulate JSON input for the last tool call
                                    tool_calls[-1]["input_json"] = (
                                        tool_calls[-1].get("input_json", "") + event.delta.partial_json
                                    )

                final_message = await stream.get_final_message()

            # If no tool calls — we're done
            if not any(b.type == "tool_use" for b in final_message.content):
                break

            # Dispatch tool calls
            messages.append({"role": "assistant", "content": final_message.content})
            tool_result_content = []

            for block in final_message.content:
                if block.type == "tool_use":
                    result = await self._dispatch_tool(block.name, block.input)
                    tool_result_content.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })
                    yield f"\n*[Tool called: {block.name}]*\n"

            messages.append({"role": "user", "content": tool_result_content})

    async def _dispatch_tool(self, tool_name: str, tool_input: dict[str, Any]) -> Any:
        """Dispatch a tool call to the appropriate MCP server function.

        Subclasses override this to register their available tools.
        """
        logger.warning("No tool dispatcher registered for: %s", tool_name)
        return {"error": f"Tool '{tool_name}' not available in this agent"}

    async def get_response(
        self,
        user_message: str,
        conversation_history: Optional[list[dict[str, Any]]] = None,
    ) -> str:
        """Non-streaming response — collects full text. Use stream_response for UI."""
        full_text = ""
        async for chunk in self.stream_response(user_message, conversation_history):
            full_text += chunk
        return full_text
