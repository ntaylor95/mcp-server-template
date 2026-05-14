# What Is an MCP Server?

A good mental model: **an API endpoint that returns responses designed for LLM consumption.**

The LLM calls it, gets structured text back, and reasons over it.

## Key Differences from a Traditional API

1. **The LLM decides when to call it.** You don't wire up routes manually — you declare capabilities (tools, resources, prompts) and the LLM picks which to invoke based on context.

2. **It's bidirectional over a persistent connection** (stdio pipe or SSE stream), not request/response HTTP. The host (Claude Code, Claude Desktop) maintains a session with your server.

3. **Three primitives, not just endpoints:**
   - **Tools** — LLM-invoked functions (closest to the "API endpoint" analogy)
   - **Resources** — data the LLM can read on demand (more like a GET endpoint it browses)
   - **Prompts** — reusable prompt templates the user/LLM can select

## TL;DR

Think of it as "an API the LLM calls, whose responses are designed for LLM consumption." The transport and discovery layer is just different from REST.
