"""Tests for MCP server resources."""

import json

import pytest
from mcp_server_template.resources import handle_resource, list_resources


def test_list_resources_returns_resources():
    resources = list_resources()
    uris = [str(r.uri) for r in resources]
    assert "template://info" in uris
    assert "template://status" in uris
    assert "template://config" in uris
    assert "template://notes" in uris


@pytest.mark.asyncio
async def test_handle_resource_info():
    result = await handle_resource("template://info")
    assert "mcp-server-template" in result


@pytest.mark.asyncio
async def test_handle_resource_status():
    result = await handle_resource("template://status")
    data = json.loads(result)
    assert data["status"] == "running"
    assert "python_version" in data


@pytest.mark.asyncio
async def test_handle_resource_config():
    result = await handle_resource("template://config")
    data = json.loads(result)
    assert data["server_name"] == "mcp-server-template"
    assert data["capabilities"]["tools"] is True


@pytest.mark.asyncio
async def test_handle_resource_notes():
    result = await handle_resource("template://notes")
    assert "notes" in result.lower()


@pytest.mark.asyncio
async def test_unknown_resource_raises():
    with pytest.raises(ValueError, match="Unknown resource"):
        await handle_resource("template://nonexistent")
