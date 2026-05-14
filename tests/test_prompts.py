"""Tests for MCP server prompts."""

import pytest
from mcp_server_template.prompts import handle_prompt, list_prompts


def test_list_prompts_returns_prompts():
    prompts = list_prompts()
    assert len(prompts) >= 1
    names = [p.name for p in prompts]
    assert "summarize" in names


@pytest.mark.asyncio
async def test_summarize_prompt():
    result = await handle_prompt("summarize", {"text": "Hello world"})
    assert result.messages
    assert "Hello world" in result.messages[0].content.text


@pytest.mark.asyncio
async def test_unknown_prompt_raises():
    with pytest.raises(ValueError, match="Unknown prompt"):
        await handle_prompt("nonexistent", {})
