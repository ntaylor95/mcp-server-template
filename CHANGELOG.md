# Changelog

## For the skill, here is what I added          

  1. Clarifying questions for ambiguous cases — four follow-up questions Claude should ask when the decision tree doesn't resolve cleanly.       
   
  2. "Who initiates" as the primary fork — restructured the decision tree so the first question is "who starts it?" (user = prompt, LLM =        
  tool/resource). This is the conceptual key that was buried before.                                                                           
                                                                                                                                               
  3. Anti-patterns table — five common mistakes like overloaded tools, resources that need params, and vague descriptions.

  4. Description writing guidance — rules for writing descriptions that help the LLM decide when to call something. This is the highest-leverage
  prompt engineering surface in the whole MCP system.

  5. Input schema design section — when to use required vs optional, naming conventions, type selection (use enums for fixed sets, flatten nested
   objects).

  6. Output format instruction — tells Claude exactly how to present its recommendation: classification → closest example → draft description →
  schema sketch → offer to implement.

## Tools, Prompts and Resources

Here's what was added:                                                                                                      
                                                                                                                                               
  Tools (5 examples):                                                                                                                            
                                                                                                                                                 
  ┌─────────────────────┬───────────────┬────────────────────────────────────────┐                                                               
  │       Pattern       │     Tool      │              Description               │                                                               
  ├─────────────────────┼───────────────┼────────────────────────────────────────┤                                                               
  │ Simple I/O          │ hello         │ Basic string input → string output     │                                                               
  ├─────────────────────┼───────────────┼────────────────────────────────────────┤                                                               
  │ Computation         │ add_numbers   │ Numeric processing                     │                                                               
  ├─────────────────────┼───────────────┼────────────────────────────────────────┤
  │ External API (stub) │ fetch_weather │ Shows where to plug in httpx calls     │
  ├─────────────────────┼───────────────┼────────────────────────────────────────┤
  │ Data transformation │ format_json   │ Parse, validate, reformat              │
  ├─────────────────────┼───────────────┼────────────────────────────────────────┤
  │ System info         │ get_env_info  │ No-arg tool returning environment data │
  └─────────────────────┴───────────────┴────────────────────────────────────────┘

  Resources (4 examples):

  ┌──────────────────┬───────────────────┬────────────────────────────────────┐
  │     Pattern      │        URI        │            Description             │
  ├──────────────────┼───────────────────┼────────────────────────────────────┤
  │ Static text      │ template://info   │ Hardcoded string                   │
  ├──────────────────┼───────────────────┼────────────────────────────────────┤
  │ Dynamic/computed │ template://status │ Runtime data (timestamp, version)  │
  ├──────────────────┼───────────────────┼────────────────────────────────────┤
  │ Config exposure  │ template://config │ Server capabilities as JSON        │
  ├──────────────────┼───────────────────┼────────────────────────────────────┤
  │ File/DB stub     │ template://notes  │ Placeholder for real storage reads │
  └──────────────────┴───────────────────┴────────────────────────────────────┘

  Prompts (4 examples):

  ┌─────────────────────┬─────────────────┬───────────────────────────────────────┐
  │       Pattern       │     Prompt      │              Description              │
  ├─────────────────────┼─────────────────┼───────────────────────────────────────┤
  │ Single-turn         │ summarize       │ One user message with filled text     │
  ├─────────────────────┼─────────────────┼───────────────────────────────────────┤
  │ System + user       │ code_review     │ Multi-message with assistant preamble │
  ├─────────────────────┼─────────────────┼───────────────────────────────────────┤
  │ Configurable        │ explain_concept │ Optional level arg with default       │
  ├─────────────────────┼─────────────────┼───────────────────────────────────────┤
  │ Multi-step workflow │ debug_error     │ Structured debugging template         │
  └─────────────────────┴─────────────────┴───────────────────────────────────────┘

  Each file has docstrings explaining the patterns so it's easy to copy/adapt when building real tools.

## After review, we fixed

Here's a summary of what I filled in:

  ┌──────────────────────────────┬─────────────────────────────────────────────────────────────────────────┐                                     
  │             Gap              │                                   Fix                                   │
  ├──────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤                                     
  │ Missing prompts support      │ Added prompts.py with a summarize prompt template, wired into server.py │                                   
  ├──────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤                                   
  │ No input validation in tools │ Added KeyError-preventing checks before accessing arguments             │
  ├──────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ No logging                   │ Added logging throughout with a --log-level CLI flag                    │
  ├──────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ No health check for SSE      │ Added /health endpoint returning {"status": "ok"}                       │
  ├──────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ Tests only covered tools     │ Added test_resources.py, test_prompts.py, test_server.py                │
  ├──────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ Missing type annotation      │ Added type hint to handle_resource(uri: str)                            │
  ├──────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ No py.typed marker           │ Created empty py.typed file for PEP 561 compliance                      │
  ├──────────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ Dockerfile not hardened      │ Multi-stage build, non-root user, HEALTHCHECK instruction               │
  └──────────────────────────────┴─────────────────────────────────────────────────────────────────────────┘

  Still worth considering for a future pass:
  - Adding a LICENSE file (depends on your intent — MIT is common for templates)
  - Pinning the Docker base image to a specific digest for reproducible builds
  - Adding a docker-compose.yml if you plan to run alongside other services

## [0.2.0] - 2026-05-14

### Added
- **Prompts support** — New `prompts.py` module with a `summarize` prompt template, wired into the server. MCP's third core primitive is now covered.
- **Logging** — Structured logging throughout the server with a `--log-level` CLI flag (DEBUG, INFO, WARNING, ERROR).
- **Health check endpoint** — `/health` route in SSE mode returning `{"status": "ok"}` for container orchestrator liveness probes.
- **Input validation in tools** — `handle_tool_call` now validates required arguments before accessing them, preventing unhandled `KeyError` crashes.
- **Test coverage for resources, prompts, and server wiring** — Added `test_resources.py`, `test_prompts.py`, and `test_server.py`.
- **`py.typed` marker** — PEP 561 compliance for downstream type checking.
- **Dockerfile hardening** — Multi-stage build, non-root `appuser`, and `HEALTHCHECK` instruction.

### Fixed
- **Missing type annotation** — `handle_resource(uri)` now has a proper `uri: str` type hint.

## [0.1.0] - Initial release

### Added
- MCP server with stdio and SSE transports.
- `hello` and `add_numbers` example tools.
- `template://info` example resource.
- Dockerfile for production deployment.
- Basic test suite for tools.
