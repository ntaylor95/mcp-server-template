"""Prompt definitions for the MCP server.

Add your custom prompts here. Prompts are reusable templates that
LLMs can use to structure their interactions.
"""

from mcp.types import GetPromptResult, Prompt, PromptArgument, PromptMessage, TextContent


def list_prompts() -> list[Prompt]:
    return [
        Prompt(
            name="summarize",
            description="Summarize the provided text concisely",
            arguments=[
                PromptArgument(
                    name="text",
                    description="The text to summarize",
                    required=True,
                ),
            ],
        ),
    ]


async def handle_prompt(name: str, arguments: dict | None) -> GetPromptResult:
    match name:
        case "summarize":
            text = (arguments or {}).get("text", "")
            return GetPromptResult(
                description="Summarize the provided text",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"Please provide a concise summary of the following text:\n\n{text}",
                        ),
                    ),
                ],
            )
        case _:
            raise ValueError(f"Unknown prompt: {name}")
