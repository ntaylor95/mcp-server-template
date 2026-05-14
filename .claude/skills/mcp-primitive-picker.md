# MCP Primitive Picker

Help the user determine whether they need a **Tool**, **Resource**, or **Prompt** for their MCP server use case, then guide them to implement it well.

## Trigger

Use this skill when the user says things like:
- "I want to add..."
- "How should I expose..."
- "Should this be a tool or resource?"
- "I need the LLM to..."
- "What primitive should I use for..."

## Interview Flow

Ask the user: **"What do you want the LLM to be able to do?"**

If their answer is ambiguous, ask these clarifying questions:
1. **"Who starts it?"** — Does the LLM decide to call it (tool/resource), or does the user select it from a menu (prompt)?
2. **"Does it change anything?"** — Does it write, mutate, or trigger something (tool), or just read (resource)?
3. **"Is the input dynamic?"** — Does it need runtime parameters (tool), or is it a known URI (resource)?
4. **"Is it about WHAT to do or HOW to respond?"** — Action = tool. Response structure = prompt.

Then classify based on their answer using this decision tree:

### Decision Tree

```
WHO INITIATES IT?
├── The USER picks it from a list → PROMPT (user-initiated template)
└── The LLM decides at runtime → continue below

DOES IT CHANGE STATE or PRODUCE SIDE EFFECTS?
├── Yes → TOOL (LLM-initiated action)
│   Examples: send an email, run a query, create a file, call an API, compute something
└── No, it just reads → RESOURCE (LLM-initiated read)
    Examples: config values, database records, file contents, system status, documentation

DOES IT STRUCTURE HOW THE LLM SHOULD RESPOND?
└── Yes → PROMPT (reusable conversation template)
    Examples: "review this code", "explain like I'm 5", "debug this error step by step"
```

**Key conceptual difference:**
- **Tools** = LLM calls when it needs to DO something
- **Resources** = LLM reads when it needs to KNOW something
- **Prompts** = User selects when they want a specific INTERACTION pattern

### Quick Reference

| Signal in user's description | Primitive | Why |
|------------------------------|-----------|-----|
| "fetch", "get", "call", "run", "send", "create", "delete", "update" | **Tool** | Action verb = side effect |
| "show", "expose", "read", "look up", "make available" | **Resource** | Passive data access |
| "template", "always ask like this", "structured response", "workflow" | **Prompt** | Shapes the conversation |

### Edge Cases

- **"Look up X and return it"** → If it requires parameters and logic (like a search), it's a **Tool**. If it's a static/predictable URI the LLM browses, it's a **Resource**.
- **"Format the response as..."** → That's a **Prompt** — it controls output structure.
- **"Read a file and summarize it"** → Two primitives: **Resource** (expose the file) + **Prompt** (summarize template). Or a **Tool** if the file path is dynamic.

### Combination Patterns

Sometimes you need more than one:

| Use Case | Primitives |
|----------|-----------|
| "Query a DB and explain results" | Tool (query) + Prompt (explanation template) |
| "Let the LLM read my config, then act on it" | Resource (config) + Tool (action) |
| "Always analyze code the same way" | Prompt (structure) + Tool (if it runs linters, etc.) |

### Anti-Patterns (Common Mistakes)

| Mistake | Why it's wrong | Fix |
|---------|---------------|-----|
| Resource that requires complex parameters | Resources are browsed by URI, not queried | Make it a Tool |
| Tool that only returns static data | Tools imply action; static reads waste a "call" | Make it a Resource |
| One tool that does 5 things based on an "action" param | LLM can't reason about overloaded tools well | Split into separate tools |
| Prompt with no arguments | It's just a system message at that point | Hardcode it in your app logic |
| Tool with vague description | LLM won't know when to call it | Be specific about when/why (see below) |

## Writing Good Descriptions (Critical)

The `description` field is the most important prompt engineering surface in your MCP server. It's what the LLM reads to decide **when** to use your tool/resource/prompt.

**Rules:**
1. **State WHEN to use it**, not just what it does
   - Bad: `"Gets weather data"`
   - Good: `"Fetch current weather for a city when the user asks about weather, temperature, or outdoor conditions"`

2. **State what it returns** so the LLM knows if it's useful
   - Bad: `"Queries the database"`
   - Good: `"Query the users table and return matching records as JSON with id, name, and email fields"`

3. **State limitations** so the LLM doesn't misuse it
   - Good: `"Search documents by keyword (max 50 results, text fields only, does not search attachments)"`

4. **For prompts**, describe the interaction pattern
   - Good: `"Step-by-step debugging workflow that identifies root cause, suggests fixes, and explains prevention"`

## Designing Input Schemas

Once you pick the primitive, design the inputs:

**Required vs Optional:**
- Required = the tool literally cannot function without it
- Optional = has a sensible default or enhances the output

**Naming:**
- Use descriptive names the LLM can reason about: `city` not `q`, `error_message` not `input`
- Add `description` to every property — this is context for the LLM

**Types:**
- Use `enum` when there's a fixed set of valid values (helps LLM pick correctly)
- Use `string` with a description for freeform input
- Avoid deeply nested objects — flatten when possible

## After Classification

Once determined, point the user to the relevant file and show them the matching example pattern:

- **Tool** → `src/mcp_server_template/tools.py`
  - Simple I/O: `hello`
  - Computation: `add_numbers`
  - External API: `fetch_weather`
  - Data transform: `format_json`
  - System info: `get_env_info`

- **Resource** → `src/mcp_server_template/resources.py`
  - Static text: `template://info`
  - Dynamic status: `template://status`
  - Config data: `template://config`
  - File/DB stub: `template://notes`

- **Prompt** → `src/mcp_server_template/prompts.py`
  - Single-turn: `summarize`
  - Multi-message: `code_review`
  - Configurable: `explain_concept`
  - Multi-step: `debug_error`

## Output Format

When presenting your recommendation to the user, structure it as:

1. **Classification** — which primitive and why (one sentence)
2. **Closest example** — which pattern in the codebase to copy from
3. **Suggested description** — draft a good description they can use
4. **Schema sketch** — outline the input properties with types
5. **Offer to implement** — ask if they want you to add it to the relevant file
