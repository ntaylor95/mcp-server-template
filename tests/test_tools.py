"""Tests for MCP server tools."""

import pytest
from mcp_server_template.tools import handle_tool_call, list_tools


def test_list_tools_returns_tools():
    tools = list_tools()
    assert len(tools) >= 2
    names = [t.name for t in tools]
    assert "hello" in names
    assert "add_numbers" in names


@pytest.mark.asyncio
async def test_hello_tool():
    result = await handle_tool_call("hello", {"name": "World"})
    assert len(result) == 1
    assert "World" in result[0].text


@pytest.mark.asyncio
async def test_add_numbers_tool():
    result = await handle_tool_call("add_numbers", {"a": 2, "b": 3})
    assert result[0].text == "5"


@pytest.mark.asyncio
async def test_unknown_tool_raises():
    with pytest.raises(ValueError, match="Unknown tool"):
        await handle_tool_call("nonexistent", {})
