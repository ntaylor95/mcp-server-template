"""Resource definitions for the MCP server.

Add your custom resources here. Resources expose data that LLMs can read.

Resources are like GET endpoints — they expose data the LLM can browse or
reference. Unlike tools, resources are read-only and don't perform actions.

Example patterns included:
- Static text (server info)
- Dynamic/computed data (server status)
- Structured config (settings as JSON)
- File-based content (stub for reading from disk/DB)
"""

import json
import platform
import sys
from datetime import datetime, timezone

from mcp.types import Resource


def list_resources() -> list[Resource]:
    return [
        # --- Example: Static info ---
        Resource(
            uri="template://info",
            name="Server Info",
            description="Information about this MCP server",
            mimeType="text/plain",
        ),
        # --- Example: Dynamic status ---
        Resource(
            uri="template://status",
            name="Server Status",
            description="Current server status including uptime and environment",
            mimeType="application/json",
        ),
        # --- Example: Configuration data ---
        Resource(
            uri="template://config",
            name="Server Config",
            description="Server configuration and supported capabilities",
            mimeType="application/json",
        ),
        # --- Example: Stub for file/DB content ---
        Resource(
            uri="template://notes",
            name="Notes",
            description="Stub for user notes (replace with file or DB read)",
            mimeType="text/plain",
        ),
    ]


async def handle_resource(uri: str) -> str:
    uri_str = str(uri)

    match uri_str:
        case "template://info":
            return "This is a personal MCP server built from mcp-server-template."

        case "template://status":
            status = {
                "status": "running",
                "python_version": sys.version.split()[0],
                "platform": platform.system(),
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            }
            return json.dumps(status, indent=2)

        case "template://config":
            config = {
                "server_name": "mcp-server-template",
                "version": "0.2.0",
                "transports": ["stdio", "sse"],
                "capabilities": {
                    "tools": True,
                    "resources": True,
                    "prompts": True,
                },
            }
            return json.dumps(config, indent=2)

        case "template://notes":
            # STUB: Replace with actual file read or database query
            # Example:
            #   from pathlib import Path
            #   return Path("~/notes.md").expanduser().read_text()
            return "No notes yet. Replace this handler with a file or database read."

        case _:
            raise ValueError(f"Unknown resource: {uri_str}")
