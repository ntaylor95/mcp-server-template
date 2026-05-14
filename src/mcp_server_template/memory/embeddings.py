"""Embedding generation for semantic search.

Uses OpenAI's text-embedding-3-small by default.
Swap this out for Voyage, Cohere, or local models as needed.
"""

import logging

import httpx

from mcp_server_template.memory.config import EMBEDDING_MODEL, get_openai_api_key

logger = logging.getLogger(__name__)


async def generate_embedding(text: str) -> list[float]:
    """Generate an embedding vector for the given text."""
    api_key = get_openai_api_key()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": EMBEDDING_MODEL,
                "input": text,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]
