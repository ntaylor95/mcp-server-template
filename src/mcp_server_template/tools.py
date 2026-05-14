"""Tool definitions for the MCP server.

Add your custom tools here. Each tool needs:
1. A Tool definition in list_tools()
2. A handler in handle_tool_call()

Tools are LLM-invoked functions. The LLM sees the name, description, and
input schema, then decides when to call them. Think of these as POST endpoints
whose responses are designed for LLM consumption.

Example patterns included:
- Simple input/output (hello, add_numbers)
- External API call (fetch_weather)
- Data transformation (format_json)
- System/env interaction (get_env_info)
"""

import json
import logging
import platform
import sys
from datetime import datetime, timezone

from mcp.types import TextContent, Tool

logger = logging.getLogger(__name__)


def list_tools() -> list[Tool]:
    return [
        # --- Example: Simple input/output ---
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
        # --- Example: Computation ---
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
        # --- Example: External API call (stub) ---
        Tool(
            name="fetch_weather",
            description="Fetch current weather for a city (stub — replace with real API call)",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, e.g. 'San Francisco'",
                    },
                    "units": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature units (default: fahrenheit)",
                    },
                },
                "required": ["city"],
            },
        ),
        # --- Example: Data transformation ---
        Tool(
            name="format_json",
            description="Pretty-print and validate a JSON string",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {
                        "type": "string",
                        "description": "Raw JSON string to format",
                    },
                    "indent": {
                        "type": "integer",
                        "description": "Indentation level (default: 2)",
                    },
                },
                "required": ["data"],
            },
        ),
        # --- Example: System/environment info ---
        Tool(
            name="get_env_info",
            description="Return system environment information (Python version, OS, timestamp)",
            inputSchema={
                "type": "object",
                "properties": {},
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

        case "fetch_weather":
            if "city" not in arguments:
                raise ValueError("Missing required argument: city")
            city = arguments["city"]
            units = arguments.get("units", "fahrenheit")
            # STUB: Replace this with a real API call (e.g., OpenWeatherMap, WeatherAPI)
            # Example with httpx:
            #   async with httpx.AsyncClient() as client:
            #       resp = await client.get(f"https://api.weather.example/v1?city={city}")
            #       data = resp.json()
            stub_response = {
                "city": city,
                "temperature": 72 if units == "fahrenheit" else 22,
                "units": units,
                "condition": "sunny",
                "note": "This is stub data. Replace with a real weather API.",
            }
            return [TextContent(type="text", text=json.dumps(stub_response, indent=2))]

        case "format_json":
            if "data" not in arguments:
                raise ValueError("Missing required argument: data")
            indent = arguments.get("indent", 2)
            try:
                parsed = json.loads(arguments["data"])
                formatted = json.dumps(parsed, indent=indent, sort_keys=True)
                return [TextContent(type="text", text=formatted)]
            except json.JSONDecodeError as e:
                return [TextContent(type="text", text=f"Invalid JSON: {e}")]

        case "get_env_info":
            info = {
                "python_version": sys.version,
                "platform": platform.platform(),
                "architecture": platform.machine(),
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            }
            return [TextContent(type="text", text=json.dumps(info, indent=2))]

        case _:
            raise ValueError(f"Unknown tool: {name}")
