"""Supabase database client for the memory module.

Handles all direct database operations: insert, query, and RPC calls.
"""

import logging
from datetime import datetime

import httpx

from mcp_server_template.memory.config import get_supabase_key, get_supabase_url

logger = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        "apikey": get_supabase_key(),
        "Authorization": f"Bearer {get_supabase_key()}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _base_url() -> str:
    return f"{get_supabase_url()}/rest/v1"


async def insert_interaction(
    session_id: str,
    llm_source: str,
    role: str,
    content: str,
    embedding: list[float] | None = None,
    metadata: dict | None = None,
    token_count: int | None = None,
) -> dict:
    """Insert a new interaction into the database."""
    payload = {
        "session_id": session_id,
        "llm_source": llm_source,
        "role": role,
        "content": content,
        "metadata": metadata or {},
    }
    if embedding:
        payload["embedding"] = embedding
    if token_count is not None:
        payload["token_count"] = token_count

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{_base_url()}/interactions",
            headers=_headers(),
            json=payload,
            timeout=15.0,
        )
        response.raise_for_status()
        rows = response.json()
        return rows[0] if rows else {}


async def semantic_search(
    query_embedding: list[float],
    match_count: int = 10,
    llm_source: str | None = None,
    session_id: str | None = None,
    after: datetime | None = None,
) -> list[dict]:
    """Search interactions by semantic similarity using the database RPC function."""
    params = {
        "query_embedding": query_embedding,
        "match_count": match_count,
    }
    if llm_source:
        params["filter_llm_source"] = llm_source
    if session_id:
        params["filter_session_id"] = session_id
    if after:
        params["filter_after"] = after.isoformat()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{get_supabase_url()}/rest/v1/rpc/search_interactions",
            headers=_headers(),
            json=params,
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()


async def get_recent_interactions(limit: int = 20) -> list[dict]:
    """Get the most recent interactions across all LLMs."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{_base_url()}/interactions",
            headers=_headers(),
            params={
                "select": "id,session_id,llm_source,role,content,metadata,token_count,created_at",
                "order": "created_at.desc",
                "limit": str(limit),
            },
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()


async def get_usage_stats() -> list[dict]:
    """Get usage statistics grouped by LLM source."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{_base_url()}/usage_stats",
            headers=_headers(),
            params={"select": "*"},
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()


async def search_by_metadata(
    filters: dict,
    limit: int = 20,
) -> list[dict]:
    """Search interactions by metadata fields (exact match)."""
    params = {
        "select": "id,session_id,llm_source,role,content,metadata,token_count,created_at",
        "order": "created_at.desc",
        "limit": str(limit),
    }
    # Supabase PostgREST JSON filtering
    for key, value in filters.items():
        params[f"metadata->>'{key}'"] = f"eq.{value}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{_base_url()}/interactions",
            headers=_headers(),
            params=params,
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()
