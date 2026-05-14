"""Prompt definitions for the MCP server.

Add your custom prompts here. Prompts are reusable templates that
LLMs can use to structure their interactions.

Prompts are pre-built message templates the user or LLM can select.
Think of them as saved "recipes" for common tasks — the LLM fills in
the arguments, and the prompt structures the conversation.

Example patterns included:
- Simple single-turn (summarize)
- Multi-turn with system message (code_review)
- Configurable with optional args (explain_concept)
- Multi-step workflow (debug_error)
"""

from mcp.types import GetPromptResult, Prompt, PromptArgument, PromptMessage, TextContent


def list_prompts() -> list[Prompt]:
    return [
        # --- Example: Simple single-turn ---
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
        # --- Example: Code review with system context ---
        Prompt(
            name="code_review",
            description="Review code for bugs, style issues, and improvements",
            arguments=[
                PromptArgument(
                    name="code",
                    description="The code to review",
                    required=True,
                ),
                PromptArgument(
                    name="language",
                    description="Programming language (e.g., python, typescript)",
                    required=False,
                ),
            ],
        ),
        # --- Example: Configurable explanation ---
        Prompt(
            name="explain_concept",
            description="Explain a technical concept at a specified level",
            arguments=[
                PromptArgument(
                    name="concept",
                    description="The concept to explain",
                    required=True,
                ),
                PromptArgument(
                    name="level",
                    description="Explanation level: beginner, intermediate, or expert (default: intermediate)",
                    required=False,
                ),
            ],
        ),
        # --- Example: Multi-step debugging workflow ---
        Prompt(
            name="debug_error",
            description="Help debug an error with structured analysis",
            arguments=[
                PromptArgument(
                    name="error_message",
                    description="The error message or stack trace",
                    required=True,
                ),
                PromptArgument(
                    name="context",
                    description="Additional context about what you were doing when the error occurred",
                    required=False,
                ),
            ],
        ),
    ]


async def handle_prompt(name: str, arguments: dict | None) -> GetPromptResult:
    args = arguments or {}

    match name:
        case "summarize":
            text = args.get("text", "")
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

        case "code_review":
            code = args.get("code", "")
            language = args.get("language", "")
            lang_hint = f" ({language})" if language else ""
            return GetPromptResult(
                description=f"Code review{lang_hint}",
                messages=[
                    PromptMessage(
                        role="assistant",
                        content=TextContent(
                            type="text",
                            text="I'll review this code for bugs, style issues, security concerns, and potential improvements.",
                        ),
                    ),
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"Please review the following{lang_hint} code:\n\n```{language}\n{code}\n```\n\nProvide feedback on:\n1. Bugs or correctness issues\n2. Style and readability\n3. Security concerns\n4. Suggested improvements",
                        ),
                    ),
                ],
            )

        case "explain_concept":
            concept = args.get("concept", "")
            level = args.get("level", "intermediate")
            return GetPromptResult(
                description=f"Explain {concept} at {level} level",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"Explain the concept of \"{concept}\" at a {level} level. "
                            f"Include a clear definition, how it works, and a practical example.",
                        ),
                    ),
                ],
            )

        case "debug_error":
            error_message = args.get("error_message", "")
            context = args.get("context", "")
            context_section = f"\n\nContext: {context}" if context else ""
            return GetPromptResult(
                description="Debug error analysis",
                messages=[
                    PromptMessage(
                        role="assistant",
                        content=TextContent(
                            type="text",
                            text="I'll help you debug this error. I'll analyze the root cause, suggest fixes, and explain how to prevent it.",
                        ),
                    ),
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"I'm getting this error:\n\n```\n{error_message}\n```{context_section}\n\nPlease:\n1. Identify the root cause\n2. Suggest a fix\n3. Explain how to prevent this in the future",
                        ),
                    ),
                ],
            )

        case _:
            raise ValueError(f"Unknown prompt: {name}")
