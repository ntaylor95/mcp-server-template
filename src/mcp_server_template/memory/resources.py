"""Memory resources — passive data the LLM can browse.

Resources:
- memory://recent: Last 20 interactions across all LLMs
- memory://stats: Usage statistics grouped by LLM source
"""

import json
import logging

from mcp.types import Resource

from mcp_server_template.memory.db import get_recent_interactions, get_usage_stats

logger = logging.getLogger(__name__)


def list_memory_resources() -> list[Resource]:
    return [
        Resource(
            uri="memory://recent",
            name="Recent Interactions",
            description="The 20 most recent interactions across all LLMs (Claude, Gemini, ChatGPT)",
            mimeType="application/json",
        ),
        Resource(
            uri="memory://stats",
            name="Usage Stats",
            description="Usage statistics: message counts, token totals, and session counts per LLM",
            mimeType="application/json",
        ),
    ]


async def handle_memory_resource(uri: str) -> str:
    uri_str = str(uri)

    match uri_str:
        case "memory://recent":
            interactions = await get_recent_interactions(limit=20)
            return json.dumps({"interactions": interactions, "count": len(interactions)}, indent=2)

        case "memory://stats":
            stats = await get_usage_stats()
            return json.dumps({"stats": stats}, indent=2)

        case _:
            raise ValueError(f"Unknown memory resource: {uri_str}")
