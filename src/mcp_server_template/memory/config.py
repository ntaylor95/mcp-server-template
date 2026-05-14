"""Configuration for the memory module.

Reads from environment variables. Set these in your .env file:
    SUPABASE_URL=https://your-project.supabase.co
    SUPABASE_KEY=your-service-role-key
    OPENAI_API_KEY=your-openai-key  (for embeddings)
"""

import os


def get_supabase_url() -> str:
    url = os.environ.get("SUPABASE_URL")
    if not url:
        raise RuntimeError("SUPABASE_URL environment variable is required")
    return url


def get_supabase_key() -> str:
    key = os.environ.get("SUPABASE_KEY")
    if not key:
        raise RuntimeError("SUPABASE_KEY environment variable is required")
    return key


def get_openai_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY environment variable is required (for embeddings)")
    return key


EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIMENSIONS = 1536
