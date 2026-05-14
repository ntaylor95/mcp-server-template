"""Tests for MCP server tools."""

import json

import pytest
from mcp_server_template.tools import handle_tool_call, list_tools


def test_list_tools_returns_tools():
    tools = list_tools()
    names = [t.name for t in tools]
    assert "hello" in names
    assert "add_numbers" in names
    assert "fetch_weather" in names
    assert "format_json" in names
    assert "get_env_info" in names


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
async def test_fetch_weather_tool():
    result = await handle_tool_call("fetch_weather", {"city": "Portland", "units": "celsius"})
    data = json.loads(result[0].text)
    assert data["city"] == "Portland"
    assert data["units"] == "celsius"
    assert data["temperature"] == 22


@pytest.mark.asyncio
async def test_format_json_tool():
    raw = '{"b":2,"a":1}'
    result = await handle_tool_call("format_json", {"data": raw})
    parsed = json.loads(result[0].text)
    assert parsed == {"a": 1, "b": 2}


@pytest.mark.asyncio
async def test_format_json_tool_invalid():
    result = await handle_tool_call("format_json", {"data": "not json"})
    assert "Invalid JSON" in result[0].text


@pytest.mark.asyncio
async def test_get_env_info_tool():
    result = await handle_tool_call("get_env_info", {})
    data = json.loads(result[0].text)
    assert "python_version" in data
    assert "platform" in data
    assert "timestamp_utc" in data


@pytest.mark.asyncio
async def test_unknown_tool_raises():
    with pytest.raises(ValueError, match="Unknown tool"):
        await handle_tool_call("nonexistent", {})
