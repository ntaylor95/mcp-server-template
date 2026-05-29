SSO credential delegation at query time.

  The constraint says: fetch the source doc using the caller's SSO credentials. But an MCP server is a daemon — it doesn't
  inherently know who the calling user is or hold their token. This needs a concrete answer before we build the query pipeline:

  Option: Client passes access token as a tool argument
  How it works: UI acquires a SharePoint-scoped token and passes it to the MCP tool call
  Trade-off: Simple to build; token leaks into MCP tool args/logs
  ────────────────────────────────────────
  Option: HTTP header forwarding (SSE transport)
  How it works: UI includes Authorization header; SSE server reads it and scopes the downstream call
  Trade-off: Cleaner separation; requires SSE transport (not stdio)
  ────────────────────────────────────────
  Option: On-behalf-of OAuth flow (server-side)
  How it works: Server holds a client secret and exchanges the user's token for a SharePoint token via Azure AD OBO
  Trade-off: Proper enterprise pattern; more setup (Azure app registration, OBO grant)
  ────────────────────────────────────────
  Option: Copilot Studio delegation
  How it works: When you get there, Copilot Studio handles OAuth natively
  Trade-off: Future-proof, but not available yet

  Given the timeline and that Copilot Studio is coming, OBO is the right long-term answer but requires an Azure app registration.
  If that's blocked, HTTP header forwarding with SSE transport is a good POC pattern that maps cleanly to OBO later.

  ---
  Other gaps to confirm
  
  1. Embedding model — Azure OpenAI, OpenAI API, or something local/self-hosted?
  2. LLM for topic splitting and answering — same question. Azure OpenAI would be natural if you're already in the tenant.
  3. UI stack — given the June deadline, Gradio or Streamlit is much faster than a custom FastAPI frontend. Fine with either
  though.
  4. SharePoint update detection — Microsoft Graph has a delta query / change notification (webhook) API. Polling is simpler for
  POC; webhooks are better for production. Which phase does "must support" belong to?

  Once you have answers to #1 (auth delegation) and #2 (LLM/embedding provider), we can scaffold the two pipelines in parallel.
  What's the current state on the Azure app registration / OBO grant, and which LLM endpoint are you targeting?