# MCP Server Template

A personal MCP (Model Context Protocol) server template built with Python. Supports both stdio (local development) and SSE (production deployment) transports.

## Setup

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

## Running Locally

### stdio mode (for Claude Code, Claude Desktop, etc.)

```bash
mcp-server-template
```

### SSE mode (for remote/production use)

```bash
mcp-server-template --transport sse --port 8000
```

## Claude Code Configuration

Add to your Claude Code MCP settings (`~/.claude/settings.json` or project `.mcp.json`):

```json
{
  "mcpServers": {
    "my-server": {
      "command": "/path/to/.venv/bin/mcp-server-template"
    }
  }
}
```

## Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "/path/to/.venv/bin/mcp-server-template"
    }
  }
}
```

## Adding Tools

Edit `src/mcp_server_template/tools.py`:

1. Add a `Tool` definition to `list_tools()`
2. Add a handler case in `handle_tool_call()`

## Adding Resources

Edit `src/mcp_server_template/resources.py`:

1. Add a `Resource` definition to `list_resources()`
2. Add a handler case in `handle_resource()`

## Testing

```bash
pytest
```

## Production Deployment (Docker)

```bash
docker build -t mcp-server .
docker run -p 8000:8000 mcp-server
```

## Project Structure

```
src/mcp_server_template/
  __init__.py        # Package init
  server.py          # Server creation and entrypoint
  tools.py           # Tool definitions and handlers
  resources.py       # Resource definitions and handlers
  sse.py             # SSE transport for production
```
