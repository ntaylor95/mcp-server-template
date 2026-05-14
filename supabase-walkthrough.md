What pgvector gets you                                                                                               
                                                                                                                       
  Without pgvector, you can only retrieve conversations by exact match — give me the chat from Tuesday, give me all    
  chats containing the word "Terraform", filter by date range. That's traditional SQL.                                 

  With pgvector, you can retrieve by semantic similarity — "find conversations where I discussed deployment strategies"
   even if those exact words were never used. It works by:

  1. Converting text into embedding vectors (arrays of floats) via an embedding model
  2. Storing those vectors alongside your conversation rows
  3. Querying with cosine similarity: "find the 10 rows closest in meaning to this query"

  TL;DR: pgvector turns your database into a semantic search engine. Without it you have Ctrl+F. With it you have "find
   me related stuff."

  ---
  What MCP primitives does this need?

  This is a combination pattern. Let me walk the decision tree:

  ┌───────────────────────────────────┬─────────────────────┬──────────────────┬─────────────────────────────────┐
  │        What you need to do        │   Who initiates?    │   Side effect?   │            Primitive            │
  ├───────────────────────────────────┼─────────────────────┼──────────────────┼─────────────────────────────────┤
  │ Save a conversation to Supabase   │ LLM (after each     │ Yes (write)      │ Tool                            │
  │                                   │ interaction)        │                  │                                 │
  ├───────────────────────────────────┼─────────────────────┼──────────────────┼─────────────────────────────────┤
  │ Search past conversations by      │ LLM (when it needs  │ No (read, but    │ Tool (not a resource — it       │
  │ meaning                           │ context)            │ needs params)    │ requires dynamic query input)   │
  ├───────────────────────────────────┼─────────────────────┼──────────────────┼─────────────────────────────────┤
  │ Browse recent interactions or     │ LLM (passive read)  │ No               │ Resource                        │
  │ usage stats                       │                     │                  │                                 │
  ├───────────────────────────────────┼─────────────────────┼──────────────────┼─────────────────────────────────┤
  │ "Before answering, check if I've  │ User selects this   │ No               │ Prompt                          │
  │ discussed this before"            │ mode                │                  │                                 │
  └───────────────────────────────────┴─────────────────────┴──────────────────┴─────────────────────────────────┘

  So you'd likely build:

  - Tools:
    - save_interaction — store message + embedding to Supabase
    - search_memory — semantic search across past interactions
    - search_memory_by_metadata — filter by LLM source, date range, topic tags
  - Resources:
    - memory://recent — last N interactions (no params needed, just browse)
    - memory://stats — usage breakdown by LLM, token counts, topics
  - Prompts:
    - recall_context — "Before answering, search my memory for related past conversations and incorporate what you
  find"

  ---
  The key architecture question

  Do you want the MCP server itself to call the embedding model (to vectorize before storing), or do you want Supabase
  to handle that automatically with their AI/vector integration?

  Option A: MCP server calls OpenAI/Voyage embeddings → stores vector + text in Supabase
  Option B: Store raw text → Supabase edge function generates embeddings async

  This affects whether you need httpx calls to an embedding API in your tools, or if your tools just do straight SQL
  inserts and let Supabase handle the rest.