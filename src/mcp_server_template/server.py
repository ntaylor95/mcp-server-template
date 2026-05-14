"""Main MCP server definition."""

import argparse
import logging

from dotenv import load_dotenv

load_dotenv()

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import GetPromptResult, TextContent, Tool

from mcp_server_template.tools import handle_tool_call, list_tools
from mcp_server_template.resources import handle_resource, list_resources
from mcp_server_template.prompts import handle_prompt, list_prompts
from mcp_server_template.memory.tools import handle_memory_tool_call, list_memory_tools
from mcp_server_template.memory.resources import handle_memory_resource, list_memory_resources
from mcp_server_template.memory.prompts import handle_memory_prompt, list_memory_prompts

logger = logging.getLogger(__name__)


def create_server() -> Server:
    server = Server("mcp-server-template")

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return list_tools() + list_memory_tools()

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict) -> list[TextContent]:
        # Route to memory tools if applicable
        memory_tool_names = {t.name for t in list_memory_tools()}
        if name in memory_tool_names:
            return await handle_memory_tool_call(name, arguments)
        return await handle_tool_call(name, arguments)

    @server.list_resources()
    async def _list_resources():
        return list_resources() + list_memory_resources()

    @server.read_resource()
    async def _read_resource(uri):
        uri_str = str(uri)
        if uri_str.startswith("memory://"):
            return await handle_memory_resource(uri)
        return await handle_resource(uri)

    @server.list_prompts()
    async def _list_prompts():
        return list_prompts() + list_memory_prompts()

    @server.get_prompt()
    async def _get_prompt(name: str, arguments: dict | None) -> GetPromptResult:
        memory_prompt_names = {p.name for p in list_memory_prompts()}
        if name in memory_prompt_names:
            return await handle_memory_prompt(name, arguments)
        return await handle_prompt(name, arguments)

    return server


def main():
    parser = argparse.ArgumentParser(description="MCP Server Template")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport mechanism (default: stdio)",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host for SSE transport (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port for SSE transport (default: 8000)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    server = create_server()
    logger.info("Starting MCP server (transport=%s)", args.transport)

    if args.transport == "stdio":
        import asyncio

        async def run_stdio():
            async with stdio_server() as (read_stream, write_stream):
                await server.run(read_stream, write_stream, server.create_initialization_options())

        asyncio.run(run_stdio())
    else:
        from mcp_server_template.sse import run_sse_server

        run_sse_server(server, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
