"""Tests for MCP server resources."""

import pytest
from mcp_server_template.resources import handle_resource, list_resources


def test_list_resources_returns_resources():
    resources = list_resources()
    assert len(resources) >= 1
    uris = [str(r.uri) for r in resources]
    assert "template://info" in uris


@pytest.mark.asyncio
async def test_handle_resource_info():
    result = await handle_resource("template://info")
    assert "mcp-server-template" in result


@pytest.mark.asyncio
async def test_unknown_resource_raises():
    with pytest.raises(ValueError, match="Unknown resource"):
        await handle_resource("template://nonexistent")
