"""Memory prompts — reusable templates for context-aware interactions.

Prompts:
- recall_context: Before answering, search memory for related past conversations
- continue_session: Resume a previous conversation session by ID
- cross_llm_context: Pull context from a different LLM's conversations into this one
"""

from mcp.types import GetPromptResult, Prompt, PromptArgument, PromptMessage, TextContent


def list_memory_prompts() -> list[Prompt]:
    return [
        Prompt(
            name="recall_context",
            description=(
                "Before answering a question, search memory for related past conversations "
                "and incorporate relevant context. Use this for continuity across sessions."
            ),
            arguments=[
                PromptArgument(
                    name="topic",
                    description="The topic or question to recall context for",
                    required=True,
                ),
                PromptArgument(
                    name="llm_source",
                    description="Optionally filter to a specific LLM's history (claude, gemini, chatgpt)",
                    required=False,
                ),
            ],
        ),
        Prompt(
            name="continue_session",
            description=(
                "Resume a previous conversation by loading its history. "
                "Use when you want to pick up where you left off in a specific session."
            ),
            arguments=[
                PromptArgument(
                    name="session_id",
                    description="The session ID to resume",
                    required=True,
                ),
            ],
        ),
        Prompt(
            name="cross_llm_context",
            description=(
                "Pull context from another LLM's conversations into this one. "
                "Use when you discussed something in ChatGPT and want Claude to know about it, "
                "or vice versa."
            ),
            arguments=[
                PromptArgument(
                    name="topic",
                    description="What you discussed in the other LLM",
                    required=True,
                ),
                PromptArgument(
                    name="source_llm",
                    description="Which LLM had the original conversation (claude, gemini, chatgpt)",
                    required=True,
                ),
            ],
        ),
    ]


async def handle_memory_prompt(name: str, arguments: dict | None) -> GetPromptResult:
    args = arguments or {}

    match name:
        case "recall_context":
            topic = args.get("topic", "")
            llm_filter = args.get("llm_source", "")
            filter_instruction = (
                f" Focus on conversations from {llm_filter}." if llm_filter else ""
            )
            return GetPromptResult(
                description=f"Recall context about: {topic}",
                messages=[
                    PromptMessage(
                        role="assistant",
                        content=TextContent(
                            type="text",
                            text=(
                                "I'll search your conversation history for relevant context "
                                "before answering."
                            ),
                        ),
                    ),
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=(
                                f"Before answering my question, use the search_memory tool to "
                                f"find past conversations related to: \"{topic}\"{filter_instruction}\n\n"
                                f"Then incorporate any relevant context from those past conversations "
                                f"into your response. If nothing relevant is found, just answer normally.\n\n"
                                f"My question/topic: {topic}"
                            ),
                        ),
                    ),
                ],
            )

        case "continue_session":
            session_id = args.get("session_id", "")
            return GetPromptResult(
                description=f"Continue session {session_id}",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=(
                                f"I want to continue a previous conversation. "
                                f"Use the search_memory tool with session_id=\"{session_id}\" "
                                f"to load the conversation history, then summarize where we left off "
                                f"and ask me how I'd like to continue."
                            ),
                        ),
                    ),
                ],
            )

        case "cross_llm_context":
            topic = args.get("topic", "")
            source_llm = args.get("source_llm", "")
            return GetPromptResult(
                description=f"Pull context from {source_llm} about {topic}",
                messages=[
                    PromptMessage(
                        role="assistant",
                        content=TextContent(
                            type="text",
                            text=(
                                f"I'll search your {source_llm} conversation history for context "
                                f"about \"{topic}\" and bring it into our conversation."
                            ),
                        ),
                    ),
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=(
                                f"I previously discussed \"{topic}\" with {source_llm}. "
                                f"Use search_memory with llm_source=\"{source_llm}\" and "
                                f"query=\"{topic}\" to find that conversation.\n\n"
                                f"Then:\n"
                                f"1. Summarize what was discussed\n"
                                f"2. Note any decisions or conclusions reached\n"
                                f"3. Ask me what I'd like to do next with this context"
                            ),
                        ),
                    ),
                ],
            )

        case _:
            raise ValueError(f"Unknown memory prompt: {name}")
