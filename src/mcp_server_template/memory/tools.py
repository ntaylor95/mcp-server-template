"""Memory tools — LLM-invoked actions for saving and searching interactions.

Tools:
- save_interaction: Store a message with its embedding in Supabase
- search_memory: Semantic search across all past interactions
- search_by_metadata: Filter interactions by metadata fields (topic, tags, etc.)
"""

import json
import logging
import uuid

from mcp.types import TextContent, Tool

from mcp_server_template.memory.db import (
    insert_interaction,
    search_by_metadata as db_search_by_metadata,
    semantic_search,
)
from mcp_server_template.memory.embeddings import generate_embedding

logger = logging.getLogger(__name__)


def list_memory_tools() -> list[Tool]:
    return [
        Tool(
            name="save_interaction",
            description=(
                "Save an LLM interaction to persistent memory. Call this to store a conversation "
                "turn so it can be recalled later via semantic search. Include the LLM source "
                "(claude, gemini, chatgpt) and any relevant metadata tags."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The message content to save",
                    },
                    "role": {
                        "type": "string",
                        "enum": ["user", "assistant", "system"],
                        "description": "Who said this message",
                    },
                    "llm_source": {
                        "type": "string",
                        "enum": ["claude", "gemini", "chatgpt", "other"],
                        "description": "Which LLM this interaction is from",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session/conversation ID (auto-generated if omitted)",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Optional metadata: topic, tags, project, etc.",
                    },
                    "token_count": {
                        "type": "integer",
                        "description": "Optional token count for this message",
                    },
                },
                "required": ["content", "role", "llm_source"],
            },
        ),
        Tool(
            name="search_memory",
            description=(
                "Search past interactions by meaning using semantic similarity. "
                "Use this when you need to recall what was discussed previously, "
                "find related conversations, or check if a topic has been covered before. "
                "Returns the most relevant past messages ranked by similarity."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query to search for (e.g., 'deployment strategies we discussed')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default: 10)",
                    },
                    "llm_source": {
                        "type": "string",
                        "enum": ["claude", "gemini", "chatgpt", "other"],
                        "description": "Filter to a specific LLM's conversations only",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Filter to a specific session/conversation",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="search_memory_by_metadata",
            description=(
                "Search past interactions by metadata filters (exact match). "
                "Use when you want to find interactions tagged with a specific topic, "
                "project, or other structured metadata — not for fuzzy/semantic search."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "filters": {
                        "type": "object",
                        "description": "Key-value pairs to match in metadata (e.g., {\"topic\": \"terraform\", \"project\": \"infra\"})",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default: 20)",
                    },
                },
                "required": ["filters"],
            },
        ),
    ]


async def handle_memory_tool_call(name: str, arguments: dict) -> list[TextContent]:
    logger.debug("Memory tool %s called with %s", name, arguments)

    match name:
        case "save_interaction":
            content = arguments["content"]
            role = arguments["role"]
            llm_source = arguments["llm_source"]
            session_id = arguments.get("session_id", str(uuid.uuid4()))
            metadata = arguments.get("metadata", {})
            token_count = arguments.get("token_count")

            # Generate embedding for semantic search later
            embedding = await generate_embedding(content)

            result = await insert_interaction(
                session_id=session_id,
                llm_source=llm_source,
                role=role,
                content=content,
                embedding=embedding,
                metadata=metadata,
                token_count=token_count,
            )

            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "saved",
                    "id": result.get("id"),
                    "session_id": session_id,
                }, indent=2),
            )]

        case "search_memory":
            query = arguments["query"]
            limit = arguments.get("limit", 10)
            llm_source = arguments.get("llm_source")
            session_id = arguments.get("session_id")

            # Generate embedding for the search query
            query_embedding = await generate_embedding(query)

            results = await semantic_search(
                query_embedding=query_embedding,
                match_count=limit,
                llm_source=llm_source,
                session_id=session_id,
            )

            formatted = []
            for r in results:
                formatted.append({
                    "similarity": round(r["similarity"], 4),
                    "llm_source": r["llm_source"],
                    "role": r["role"],
                    "content": r["content"][:500],  # Truncate for readability
                    "session_id": r["session_id"],
                    "created_at": r["created_at"],
                    "metadata": r.get("metadata", {}),
                })

            return [TextContent(
                type="text",
                text=json.dumps({"results": formatted, "count": len(formatted)}, indent=2),
            )]

        case "search_memory_by_metadata":
            filters = arguments["filters"]
            limit = arguments.get("limit", 20)

            results = await db_search_by_metadata(filters=filters, limit=limit)

            formatted = []
            for r in results:
                formatted.append({
                    "llm_source": r["llm_source"],
                    "role": r["role"],
                    "content": r["content"][:500],
                    "session_id": r["session_id"],
                    "created_at": r["created_at"],
                    "metadata": r.get("metadata", {}),
                })

            return [TextContent(
                type="text",
                text=json.dumps({"results": formatted, "count": len(formatted)}, indent=2),
            )]

        case _:
            raise ValueError(f"Unknown memory tool: {name}")
