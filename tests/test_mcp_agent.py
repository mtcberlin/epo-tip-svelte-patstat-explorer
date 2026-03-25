"""Tests for the MCP-powered agentic loop in the sidecar."""

import json
import sys
import pytest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock, AsyncMock


# --- MCP client helpers ---

class TestMcpToolConversion:
    """Test converting MCP tools to Anthropic API format."""

    def test_converts_tool_list(self):
        from sidecar import _mcp_tools_to_anthropic

        mcp_tools = [
            SimpleNamespace(
                name="list_tables",
                description="List all tables",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            SimpleNamespace(
                name="execute_query",
                description="Execute SQL",
                inputSchema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            ),
        ]

        result = _mcp_tools_to_anthropic(mcp_tools)
        assert len(result) == 2
        assert result[0]["name"] == "list_tables"
        assert result[0]["input_schema"] == {"type": "object", "properties": {}, "required": []}
        assert result[1]["name"] == "execute_query"
        assert "inputSchema" not in result[1]


async def _collect_steps(agentic_gen) -> list[dict]:
    """Helper to collect all steps from the async generator."""
    steps = []
    async for step in agentic_gen:
        steps.append(step)
    return steps


class TestAgenticLoop:
    """Test the agentic loop behavior with mocked MCP and Claude."""

    @pytest.fixture
    def mock_anthropic(self):
        mock_mod = MagicMock()
        mock_mod.AuthenticationError = type("AuthenticationError", (Exception,), {})
        with patch.dict(sys.modules, {"anthropic": mock_mod}):
            yield mock_mod

    @pytest.mark.asyncio
    async def test_simple_query_no_tools(self, mock_anthropic):
        """Claude answers directly without calling tools → returns SQL immediately."""
        from sidecar import _run_agentic_loop

        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "SELECT COUNT(*) FROM tls201_appln"
        mock_response.content = [text_block]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        steps = await _collect_steps(_run_agentic_loop(
            question="How many patents are there?",
            history=[],
            api_key="sk-test",
            model="claude-sonnet-4-20250514",
            mcp_tools=[],
            mcp_call_tool=AsyncMock(),
        ))

        assert any(s["event"] == "result" for s in steps)
        result_step = next(s for s in steps if s["event"] == "result")
        assert "SELECT" in result_step["data"]["text"]

    @pytest.mark.asyncio
    async def test_tool_call_loop(self, mock_anthropic):
        """Claude calls a tool, gets result, then produces final answer."""
        from sidecar import _run_agentic_loop

        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.id = "toolu_123"
        tool_use_block.name = "list_tables"
        tool_use_block.input = {}

        first_response = MagicMock()
        first_response.stop_reason = "tool_use"
        first_response.content = [tool_use_block]

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "SELECT * FROM tls201_appln LIMIT 10"

        second_response = MagicMock()
        second_response.stop_reason = "end_turn"
        second_response.content = [text_block]

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = [first_response, second_response]
        mock_anthropic.Anthropic.return_value = mock_client

        async def mock_mcp_call(name, args):
            return "Available tables: tls201_appln, tls206_person"

        steps = await _collect_steps(_run_agentic_loop(
            question="Show me all tables",
            history=[],
            api_key="sk-test",
            model="claude-sonnet-4-20250514",
            mcp_tools=[{"name": "list_tables", "description": "List tables", "input_schema": {}}],
            mcp_call_tool=mock_mcp_call,
        ))

        events = [s["event"] for s in steps]
        assert "tool_call" in events
        assert "tool_result" in events
        assert "result" in events

    @pytest.mark.asyncio
    async def test_max_iterations_safeguard(self, mock_anthropic):
        """Loop stops after max iterations even if Claude keeps calling tools."""
        from sidecar import _run_agentic_loop, MAX_AGENT_ITERATIONS

        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.id = "toolu_123"
        tool_use_block.name = "list_tables"
        tool_use_block.input = {}

        response = MagicMock()
        response.stop_reason = "tool_use"
        response.content = [tool_use_block]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = response
        mock_anthropic.Anthropic.return_value = mock_client

        async def mock_mcp_call(name, args):
            return "tables: tls201_appln"

        steps = await _collect_steps(_run_agentic_loop(
            question="Loop forever",
            history=[],
            api_key="sk-test",
            model="claude-sonnet-4-20250514",
            mcp_tools=[{"name": "list_tables", "description": "List", "input_schema": {}}],
            mcp_call_tool=mock_mcp_call,
        ))

        assert any(s["event"] == "error" for s in steps)
        error_step = next(s for s in steps if s["event"] == "error")
        assert "iteration" in error_step["data"]["message"].lower() or "max" in error_step["data"]["message"].lower()

    @pytest.mark.asyncio
    async def test_no_api_key_yields_error(self, mock_anthropic):
        """Missing API key produces error step."""
        from sidecar import _run_agentic_loop

        steps = await _collect_steps(_run_agentic_loop(
            question="test",
            history=[],
            api_key="",
            model="claude-sonnet-4-20250514",
            mcp_tools=[],
            mcp_call_tool=AsyncMock(),
        ))

        assert any(s["event"] == "error" for s in steps)
