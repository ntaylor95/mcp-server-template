# Tricentis Policy Assistant

An MCP server and chat UI that answers questions about Tricentis company policies. Users ask plain-language questions and receive answers grounded in the original SharePoint source documents, with a direct citation link back to the policy file.

Designed to cover the full range of Tricentis policy content, including:
- Information Security and IT policies
- Corporate policies
- Benefits and HR policies

> **Status:** POC in progress — auth and SharePoint client are built; ingestion pipeline and query pipeline are next.
> See [`docs/spec.md`](docs/spec.md) for the full project spec and remaining work.

## How It Works

```
Ingestion (run once per doc / on update)
  SharePoint → Docling → LLM topic split → Embed → Milvus Lite

Query (per user request)
  Question → Milvus search → SharePoint re-fetch (SSO) → Docling → LLM → Answer + citation
```

Milvus is used for semantic search only. Document content is always re-fetched from SharePoint at query time using the requesting user's own SSO credentials — SharePoint permissions are enforced at retrieval, not ingestion.

## Stack

- **Python** + [MCP](https://modelcontextprotocol.io) (SSE transport)
- **Milvus Lite** (POC) → Milvus (production)
- **Docling** for document parsing
- **Azure OpenAI** for embeddings and answers
- **Microsoft Graph API** for SharePoint access
- **React + Vite** chat UI

## Setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Node 18+
- Azure AD app registration with `Sites.Read.All` delegated permission (see [Authentication](#authentication))

### Install

```bash
# Python dependencies
uv sync

# UI dependencies
cd ui && npm install
```

### Configure

```bash
cp .env.example .env
```

Edit `.env`:

```bash
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-app-client-id
SHAREPOINT_SITE_URL=https://tricentisgmbh.sharepoint.com/sites/Tricentis
SHAREPOINT_POLICIES_FOLDER=01 - Tricentis Policies/Information Security and IT Policies/01 - Current Information Security Policies

# For local dev (opens browser for login):
AUTH_MODE=interactive
```

### Run

```bash
# Terminal 1 — Python server (port 8000)
uv run mcp-server-template --transport sse

# Terminal 2 — React chat UI (port 5173)
cd ui && npm run dev
```

Open `http://localhost:5173`.

## Authentication

Three modes, set via `AUTH_MODE`:

| Mode | When to use | Requirements |
|---|---|---|
| `interactive` | Local dev — opens a browser window on first run, then caches the token | `AZURE_TENANT_ID`, `AZURE_CLIENT_ID` |
| `device_code` | Headless dev (SSH, CI) — prints a URL + code to authenticate | `AZURE_TENANT_ID`, `AZURE_CLIENT_ID` |
| `obo` | Production — exchanges the caller's Bearer token for a SharePoint token via Azure AD On-Behalf-Of | All of the above + `AZURE_CLIENT_SECRET` |

The Azure app registration needs:
- **Delegated permission:** `Sites.Read.All` on Microsoft Graph
- **OBO grant** enabled (for production)

## Project Structure

```
src/mcp_server_template/
  server.py            MCP server entrypoint
  auth.py              Azure AD auth (OBO + dev flows)
  sharepoint.py        Microsoft Graph API client
  sse.py               SSE transport + /api/ask endpoint
  tools.py             MCP tools (ask_policy_question — coming soon)
  llm_client.py        Azure OpenAI client — coming soon
  docling_loader.py    Document chunking — coming soon
  summarizer.py        LLM topic extraction — coming soon
  milvus_store.py      Vector store — coming soon
  policy_answerer.py   Full RAG pipeline — coming soon

scripts/
  ingest.py            Ingestion CLI — coming soon

ui/
  src/App.tsx          Chat component
  src/api.ts           API client

docs/
  spec.md              Full project spec, design decisions, and remaining work
```

## MCP Tool (coming soon)

Once the query pipeline is wired up, the server will expose an `ask_policy_question` tool usable from Claude Desktop, Cursor, or Copilot Studio:

```json
{
  "mcpServers": {
    "policy-assistant": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

## Testing

```bash
uv run pytest
```
