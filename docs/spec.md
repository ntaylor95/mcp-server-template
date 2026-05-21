# Enterprise Policy Knowledge Base — Project Spec

**Owner:** Nicole Taylor (n.taylor@tricentis.com)
**Hard deadline:** Late June 2026
**Branch:** `feature/policy-kb-milvus-ingestion` from `mcp-server-template`

---

## What We Are Building

A knowledge base that lets Tricentis sales and internal staff ask plain-language questions about company policy and get answers grounded in the original source documents. Users interact via a chat UI; answers always cite the specific SharePoint document they came from.

The system has two distinct pipelines:

### Ingestion Pipeline (run once per doc, or on update)

```
SharePoint (policy folder)
    → Docling       (PDF/DOCX → structured text)
    → LLM           (split into discrete topics)
    → Embed topics  (one embedding per topic)
    → Milvus Lite   (store embeddings + metadata)
```

### Query Pipeline (per user request)

```
User question (chat UI)
    → Milvus semantic search    (find most relevant topic)
    → SharePoint fetch          (re-fetch source doc using caller's SSO credentials)
    → Docling                   (re-process fetched doc)
    → LLM                       (answer question grounded in doc)
    → Response + source citation (returned to UI)
```

### Key Design Constraints

| Constraint | Reason |
|---|---|
| **Documents are split into individual topics — never stored as whole-document embeddings** | Enables precise retrieval at the topic level, not the document level |
| Milvus stores embeddings/topics only — never used as content source | Doc content must always come from SharePoint at query time |
| All doc fetches at query time use the **requesting user's SSO credentials** | SharePoint permissions are enforced at retrieval, not ingestion |
| Must support detecting SharePoint doc updates and re-embedding changed docs | Policies change; embeddings must stay current |

### Topic-Level Chunking (not document-level)

This is a core design decision worth stating explicitly: **we do not embed whole documents or fixed-size text chunks into Milvus. We use an LLM to decompose each document into individual policy topics, and each topic becomes its own Milvus entry.**

A single "Employee Benefits Policy" document might produce 15 separate entries:
- Dental coverage
- Vision coverage
- PTO accrual rules
- Vacation day limits
- 401k matching
- Parental leave
- …and so on

This matters because semantic search works at the granularity of what's stored. If a user asks *"how many vacation days do I get?"*, Milvus can return the exact vacation topic entry rather than the entire 40-page handbook. The LLM answerer then gets a tightly scoped context — the relevant section of the source document — rather than having to reason over the whole thing.

Fixed-size text chunking (e.g. 1024 tokens) is used only as a **pre-processing step** to feed manageable pieces to the topic-extraction LLM. The Docling chunks are never stored in Milvus directly — only the LLM-identified topics are.

---

## Architecture Decisions

### Authentication: On-Behalf-Of (OBO) OAuth Flow

Selected as the most secure option. When the server runs in production (`AUTH_MODE=obo`):
- The SSE transport reads the caller's `Authorization: Bearer <token>` header
- The token is stored in a `contextvars.ContextVar` (request-scoped)
- Each SharePoint fetch exchanges that token for a Graph-scoped token via Azure AD OBO
- The server never stores or caches user tokens

Dev modes (`AUTH_MODE=interactive`, `AUTH_MODE=device_code`) use MSAL's public client flows with a local token cache (`~/.mcp_policy_kb_tokens`, mode `0o600`).

Required Azure app registration:
- Delegated permission: `Sites.Read.All` on Microsoft Graph
- OBO grant enabled
- Required env vars: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` (OBO only)

### SharePoint Access: Microsoft Graph API

All SharePoint operations go through `https://graph.microsoft.com/v1.0`. The configured policy folder is:

```
Site:   https://tricentisgmbh.sharepoint.com/sites/Tricentis
Folder: 01 - Tricentis Policies/Information Security and IT Policies/01 - Current Information Security Policies
```

Env vars: `SHAREPOINT_SITE_URL`, `SHAREPOINT_POLICIES_FOLDER`

### Vector Store: Milvus Lite → Milvus

POC uses Milvus Lite (local `.db` file, no server). Production will use a managed Milvus instance. The schema is not yet defined but will store:
- Topic embedding (vector)
- Source document item ID (for SharePoint re-fetch)
- Source document name + web URL (for citations)
- Topic summary text
- Last-modified timestamp (for update detection)

### Change Detection: Graph API Delta Queries

`sharepoint.get_delta(delta_link)` uses the [Microsoft Graph delta query API](https://learn.microsoft.com/en-us/graph/delta-query-overview):
- First call (no token): returns all files + initial `delta_link`
- Subsequent calls: returns only changed/deleted files since last checkpoint
- Store `delta_link` between ingestion runs (Milvus metadata or a sidecar file)

### UI: React Chat Frontend

Vite + React + TypeScript, served separately from the Python server. Talks to a `/api/ask` REST endpoint on the Python server. The Vite dev server proxies `/api` to `http://localhost:8000`.

### LLM / Embeddings

Not yet decided. Likely Azure OpenAI (consistent with existing Tricentis M365 tenancy). See the reference implementation section below for specific model choices that have already been validated.

### Future: Copilot Studio Integration

License request in progress. When available, Copilot Studio will become the primary interface and will handle OAuth delegation natively. The OBO auth pattern implemented here maps directly to that model.

---

## Reference Implementation: `hr-policy-bot`

A closely related MCP server exists at `/Users/n.taylor/Documents/Repos/hr-policy-bot`. It solves the same RAG problem against local HR policy PDFs (instead of SharePoint) and is a direct reference for the pieces still to be built. Key patterns to carry forward:

### Module structure (`lib/`)

The hr-policy-bot separates each concern into its own module. We should follow the same pattern under `src/mcp_server_template/`:

| hr-policy-bot | Our equivalent | Purpose |
|---|---|---|
| `lib/docling_loader.py` | `docling_loader.py` | PDF/DOCX → text chunks via Docling |
| `lib/summarizer.py` | `summarizer.py` | LLM splits doc into discrete policy topics |
| `lib/embedder.py` | `embedder.py` | Embedding generation (with caching) |
| `lib/milvus_store.py` | `milvus_store.py` | Milvus collection schema + search |
| `lib/policy_answerer.py` | `policy_answerer.py` | Full RAG: search → fetch → LLM → citations |
| `lib/llm_client.py` | `llm_client.py` | Singleton LLM/embedding client |
| `lib/import_tracker.py` | *(not needed — we use Graph delta queries instead)* | |

### Docling chunking

The hr-policy-bot uses Docling with the OpenAI `cl100k_base` tokenizer at **1024 token chunks**. This is the validated chunk size for this type of policy content — use the same setting.

### LLM topic splitting (summarizer pattern)

Rather than naively splitting by paragraph, the hr-policy-bot sends each Docling chunk to an LLM with a prompt that extracts one or more **discrete policy summaries** per chunk. A single chunk from a handbook often covers multiple distinct policies — the LLM detects this and creates separate entries for each, each with its own summary and policy type. This is the pattern to follow for our ingestion pipeline.

Key output fields per topic entry (adapt for our use case, drop jurisdiction since all docs are Tricentis-global):
- `summary` — concise description of what the policy covers
- `policy_type` — e.g. "Access Control", "Incident Response", "Data Classification"
- `source_item_id` — SharePoint drive item ID (our addition, not in hr-policy-bot)

### Embeddings

Validated model: **Azure OpenAI `text-embedding-3-small`** (1536 dimensions). The hr-policy-bot uses this for both content and jurisdiction vectors; we will use it for content only (no jurisdiction vector needed — all our docs are Tricentis-wide).

The hr-policy-bot caches jurisdiction embeddings since the same jurisdiction string appears across many chunks. We should apply the same caching approach to any repeated metadata strings we embed.

### LLM model tiers (`config.json` pattern)

The hr-policy-bot defines three client tiers in config:

| Tier | Used for | Model |
|---|---|---|
| `small` | Topic extraction, summarization | `gpt-4.1-nano` |
| `regular` | Policy answers (RAG) | `gpt-4.1-mini` |
| `embeddings` | Content embeddings | `text-embedding-3-small` |

This tiered approach keeps costs low — expensive models only where needed. Follow the same pattern via a `config.json` or env vars.

### RAG answer pattern (`policy_answerer.py`)

The answer pipeline in hr-policy-bot:
1. Embed the user's question
2. Semantic search Milvus → top-N matches
3. Pass the retrieved policy chunks + the original question to the `regular` LLM
4. Return answer with source citations

Our pipeline differs in step 2.5: after finding the relevant topic in Milvus we must **re-fetch the full source document from SharePoint** (using the caller's SSO token) and re-run it through Docling before passing to the LLM. This is required by our security constraint (Milvus is search-only, not content source). The hr-policy-bot skips this step because it stores the full text locally.

### MCP transport: Streamable HTTP vs SSE

The hr-policy-bot uses **Streamable HTTP** (`/mcp` endpoint, MCP spec 2025-03-26) rather than SSE. Streamable HTTP is the newer and preferred transport — Claude Desktop, Cursor, and Copilot Studio all support it. Our template uses SSE, which works fine for now. We should consider migrating to Streamable HTTP before the Copilot Studio integration.

### Incremental ingestion

The hr-policy-bot tracks processed files in a SQLite `import_tracker.db` (keyed by file path + modification time). We use the **Graph API delta query** instead (`sharepoint.get_delta()`), which is cleaner for SharePoint because Microsoft maintains the change log server-side. No SQLite tracker needed.

---

## What Is Built

### `src/mcp_server_template/auth.py`
Full authentication module. Three modes (OBO, interactive, device_code). Token propagation via `contextvars.ContextVar`. MSAL token cache with `0o600` permissions. `AuthError` exception class.

### `src/mcp_server_template/sharepoint.py`
Microsoft Graph API client. Three public async functions:
- `list_policy_files()` — list all files in the configured policy folder
- `download_file(item_id)` — fetch raw bytes, always with caller's live SSO credentials
- `get_delta(delta_link)` — detect additions, modifications, and deletions since last run

Returns typed `PolicyFile` and `DeltaResult` dataclasses. The `PolicyFile.web_url` field is the SharePoint browser URL to include as a source citation in answers.

### `src/mcp_server_template/sse.py`
Updated SSE transport:
- Extracts `Authorization: Bearer` token from each SSE request and sets the `ContextVar`
- Adds `POST /api/ask` endpoint (stubbed — returns placeholder response)
- CORS configured for Vite dev server (`http://localhost:5173`)

### `ui/` — React Chat Frontend
- `src/App.tsx` — full chat component with message history, typing indicator, source citation display, auto-resizing textarea
- `src/api.ts` — typed fetch wrapper for `/api/ask`
- `src/App.css` — Tricentis-branded styles (red `#c8102e` header)
- `vite.config.ts` — proxies `/api` to `http://localhost:8000`

### `.env.example`
Documents all required env vars with descriptions. Safe to commit (no values).

### `pyproject.toml`
Added `msal>=1.28.0` and `pymilvus>=3.0.0` to dependencies.

### `~/.claude/settings.json`
Deny rules added for `pip`, `pip3`, `python -m pip`, `python3 -m pip` — project uses `uv` exclusively.

---

## What Is Left

### 1. Ingestion Pipeline — `scripts/ingest.py`

CLI script following the hr-policy-bot pattern:

```
Full run (first time or --force):
  sharepoint.list_policy_files()
      → for each file: download_file(item_id)
      → docling_loader: chunk at 1024 tokens (cl100k_base tokenizer)
      → summarizer: LLM extracts N topic entries per chunk
      → embedder: text-embedding-3-small (1536 dim) per topic
      → milvus_store: upsert all topics
  store delta_link to disk (delta_link.txt or similar)

Incremental run (default):
  sharepoint.get_delta(stored_delta_link)
      → re-ingest changed files (same pipeline as above)
      → delete Milvus entries for removed files (by source_item_id)
  update stored delta_link
```

The hr-policy-bot uses `--force` and `--drop` flags — implement the same CLI options.

Dependencies to add: `docling`, `litellm` or `openai`

### 2. Docling Loader — `src/mcp_server_template/docling_loader.py`

Port from `hr-policy-bot/lib/docling_loader.py`. Key parameters:
- Tokenizer: `cl100k_base` (OpenAI)
- Chunk size: 1024 tokens
- Input: raw bytes (from `sharepoint.download_file()`)
- Output: `list[str]` of text chunks

### 3. LLM + Embedding Client — `src/mcp_server_template/llm_client.py`

Port the tiered client pattern from `hr-policy-bot/lib/llm_client.py`. Three tiers via `config.json`:

| Tier | Purpose | Model |
|---|---|---|
| `small` | Topic extraction during ingestion | `gpt-4.1-nano` |
| `regular` | Answering questions (RAG) | `gpt-4.1-mini` |
| `embeddings` | Content vectors | `text-embedding-3-small` (1536 dim) |

Functions needed:
- `embed(text: str) -> list[float]`
- `complete(prompt: str, tier: str) -> str`

### 4. Summarizer — `src/mcp_server_template/summarizer.py`

Port from `hr-policy-bot/lib/summarizer.py`. Sends each Docling chunk to the `small` LLM to extract one or more discrete policy topic entries. A single chunk may describe multiple policies — the LLM detects this and creates separate entries.

Output per topic:
```python
@dataclass
class PolicyTopic:
    summary: str        # what this policy covers
    policy_type: str    # e.g. "Access Control", "Incident Response"
    source_item_id: str # SharePoint drive item ID
    source_name: str    # filename
    source_web_url: str # SharePoint browser URL
```

### 5. Milvus Store — `src/mcp_server_template/milvus_store.py`

Port from `hr-policy-bot/lib/milvus_store.py`, simplified (single vector, no jurisdiction):

Collection schema:
- `id` (INT64, primary key, auto-id)
- `embedding` (FloatVector, dim=1536)
- `source_item_id` (VARCHAR — SharePoint item ID for re-fetch)
- `source_name` (VARCHAR — filename)
- `source_web_url` (VARCHAR — SharePoint browser URL)
- `topic_text` (VARCHAR — the summary stored as searchable text)
- `policy_type` (VARCHAR)
- `last_modified` (VARCHAR — ISO timestamp)

Key operations: `create_collection()`, `upsert(topics, embeddings)`, `search(query_embedding, top_k) -> list[PolicyTopic]`, `delete_by_source_item_id(item_id)`.

### 6. Policy Answerer — `src/mcp_server_template/policy_answerer.py`

Port from `hr-policy-bot/lib/policy_answerer.py`, with the critical difference that we re-fetch from SharePoint rather than reading stored text:

```
embed(question)
    → milvus_store.search() → top match (has source_item_id)
    → sharepoint.download_file(source_item_id)   ← SSO-gated
    → docling_loader.chunk(raw_bytes)
    → llm_client.complete(chunks + question, tier="regular")
    → return answer + source citation
```

### 7. Wire up `/api/ask` and MCP tool

- Replace stub in `sse.py` with `policy_answerer.answer(question)`
- Add `ask_policy_question` tool in `tools.py` (same logic, for MCP callers)

### 5. MCP Tool — `src/mcp_server_template/tools.py`

Add `ask_policy_question` tool wrapping the query pipeline. This is what Copilot Studio and Claude Desktop will call. Remove or keep the template example tools as appropriate.

### 6. Azure App Registration

Before the OBO flow can be tested end-to-end, an Azure AD app registration is needed:
- Register app in the Tricentis Azure tenant
- Add `Sites.Read.All` delegated permission on Microsoft Graph
- Create a client secret
- Populate `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` in `.env`

### 7. Production Milvus

Swap `pymilvus` connection from Milvus Lite (local `.db` file) to a managed Milvus instance. Connection details TBD.

### 8. UI Improvements (post-POC)

- Add SSO login flow so the browser acquires a token and passes it to `/api/ask`
- Token forwarding: `/api/ask` should receive and forward the user's Bearer token to the SharePoint fetch (right now the stub doesn't touch auth at all)
- Error handling for auth failures (expired token, insufficient permissions)
- Markdown rendering for answers

### 9. Copilot Studio Integration

Once the license is available, register the MCP server as a connector in Copilot Studio. The OBO auth pattern is already in place.

---

## Running Locally

```bash
# Install Python dependencies
uv sync

# Install UI dependencies
cd ui && npm install

# Copy and fill in env vars
cp .env.example .env
# Edit .env with AZURE_TENANT_ID, AZURE_CLIENT_ID, SHAREPOINT_SITE_URL, etc.

# Terminal 1 — Python server (port 8000)
uv run mcp-server-template --transport sse

# Terminal 2 — React dev server (port 5173, proxies /api to 8000)
cd ui && npm run dev
```

Open `http://localhost:5173`.

---

## File Map

```
src/mcp_server_template/
  auth.py              ✅ OBO + dev auth, token ContextVar
  sharepoint.py        ✅ Graph API client (list, download, delta)
  sse.py               ✅ SSE transport + /api/ask stub + CORS
  server.py            ✅ MCP server wiring (unchanged from template)
  tools.py             ⬜ add ask_policy_question tool
  llm_client.py        ⬜ tiered Azure OpenAI client (small/regular/embeddings)
  docling_loader.py    ⬜ PDF/DOCX → 1024-token chunks
  summarizer.py        ⬜ LLM topic extraction per chunk
  embedder.py          ⬜ text-embedding-3-small wrapper
  milvus_store.py      ⬜ collection schema + search + upsert/delete
  policy_answerer.py   ⬜ full RAG pipeline (search → SharePoint → Docling → LLM)

scripts/
  ingest.py            ⬜ CLI ingestion script (full + incremental)

ui/
  src/App.tsx          ✅ chat component
  src/api.ts           ✅ fetch wrapper
  src/App.css          ✅ Tricentis-branded styles
  vite.config.ts       ✅ /api proxy

docs/
  spec.md              ✅ this file

config.json            ⬜ LLM model tier config (small/regular/embeddings)
.env.example           ✅ env var documentation
pyproject.toml         ✅ msal, pymilvus added
uv.lock                ✅
```
