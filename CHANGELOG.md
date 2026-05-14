# Changelog

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
