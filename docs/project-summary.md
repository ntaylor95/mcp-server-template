Project: Enterprise Policy Knowledge Base
Branch from: mcp-template repo
Goal:
Build an enterprise-ready knowledge base for the sales org (hard deadline: late June). Users ask questions about company policy, the system finds the right answer, and returns it — grounded in the original source document.
Architecture:
Ingestion Pipeline (run once per doc / on update)

Pull policy documents from SharePoint
Pre-process each doc with Docling (github.com/docling-project/docling)
Use an LLM to split the doc into individual topics
Embed each topic separately and store in Milvus (start with Milvus Lite for POC)

Query Pipeline (per user request)

User asks a question via UI
Milvus semantic search finds the most relevant topic entry
Fetch the original source doc from SharePoint using the caller's SSO credentials (not from Milvus — Milvus is search only)
Re-process fetched doc through Docling
Pass processed doc + question to LLM
Return answer to user

Deliverables:

MCP server wrapping the query pipeline
Simple UI for asking policy questions
Ingestion script for SharePoint → Docling → LLM topic split → Milvus
Eventually integrate with Copilot Studio (license request in progress)

Key Constraints:

Milvus stores embeddings/topics only — never used as the content source
All doc retrieval at query time must use the requesting user's SSO credentials (security requirement)
Pattern must also support detecting SharePoint doc updates and re-processing/re-embedding changed docs

Stack:

Python
Milvus Lite (POC) → Milvus (production)
Docling
MCP (from existing mcp-template)
SharePoint (via SSO/Microsoft 365)