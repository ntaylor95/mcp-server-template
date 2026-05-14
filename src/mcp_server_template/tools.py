"""Tool definitions for the MCP server.

Add your custom tools here. Each tool needs:
1. A Tool definition in list_tools()
2. A handler in handle_tool_call()
"""

import logging

from mcp.types import TextContent, Tool

logger = logging.getLogger(__name__)


def list_tools() -> list[Tool]:
    return [
        Tool(
            name="hello",
            description="A simple greeting tool that says hello",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name to greet",
                    }
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="add_numbers",
            description="Add two numbers together",
            inputSchema={
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"},
                },
                "required": ["a", "b"],
            },
        ),
    ]


async def handle_tool_call(name: str, arguments: dict) -> list[TextContent]:
    logger.debug("Calling tool %s with arguments %s", name, arguments)

    match name:
        case "hello":
            if "name" not in arguments:
                raise ValueError("Missing required argument: name")
            greeting = f"Hello, {arguments['name']}! Welcome to the MCP server."
            return [TextContent(type="text", text=greeting)]

        case "add_numbers":
            if "a" not in arguments or "b" not in arguments:
                raise ValueError("Missing required arguments: a, b")
            result = arguments["a"] + arguments["b"]
            return [TextContent(type="text", text=str(result))]

        case _:
            raise ValueError(f"Unknown tool: {name}")
