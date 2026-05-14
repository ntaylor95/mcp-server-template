"""Tests for MCP server prompts."""

import pytest
from mcp_server_template.prompts import handle_prompt, list_prompts


def test_list_prompts_returns_prompts():
    prompts = list_prompts()
    names = [p.name for p in prompts]
    assert "summarize" in names
    assert "code_review" in names
    assert "explain_concept" in names
    assert "debug_error" in names


@pytest.mark.asyncio
async def test_summarize_prompt():
    result = await handle_prompt("summarize", {"text": "Hello world"})
    assert result.messages
    assert "Hello world" in result.messages[0].content.text


@pytest.mark.asyncio
async def test_code_review_prompt():
    result = await handle_prompt("code_review", {"code": "x = 1", "language": "python"})
    assert len(result.messages) == 2
    assert "python" in result.description
    assert "x = 1" in result.messages[1].content.text


@pytest.mark.asyncio
async def test_explain_concept_prompt():
    result = await handle_prompt("explain_concept", {"concept": "recursion", "level": "beginner"})
    assert "recursion" in result.messages[0].content.text
    assert "beginner" in result.messages[0].content.text


@pytest.mark.asyncio
async def test_debug_error_prompt():
    result = await handle_prompt(
        "debug_error",
        {"error_message": "KeyError: 'foo'", "context": "parsing config"},
    )
    assert len(result.messages) == 2
    assert "KeyError" in result.messages[1].content.text
    assert "parsing config" in result.messages[1].content.text


@pytest.mark.asyncio
async def test_unknown_prompt_raises():
    with pytest.raises(ValueError, match="Unknown prompt"):
        await handle_prompt("nonexistent", {})
