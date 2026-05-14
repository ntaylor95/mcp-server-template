"""Resource definitions for the MCP server.

Add your custom resources here. Resources expose data that LLMs can read.
"""

from mcp.types import Resource


def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="template://info",
            name="Server Info",
            description="Information about this MCP server",
            mimeType="text/plain",
        ),
    ]


async def handle_resource(uri: str) -> str:
    uri_str = str(uri)

    match uri_str:
        case "template://info":
            return "This is a personal MCP server built from mcp-server-template."
        case _:
            raise ValueError(f"Unknown resource: {uri_str}")
