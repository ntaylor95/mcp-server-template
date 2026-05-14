"""Tests for MCP server creation and wiring."""

from mcp_server_template.server import create_server


def test_create_server_returns_server():
    server = create_server()
    assert server is not None
    assert server.name == "mcp-server-template"
