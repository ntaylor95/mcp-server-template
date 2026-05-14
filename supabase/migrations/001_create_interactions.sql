-- Enable pgvector extension
create extension if not exists vector;

-- Core interactions table
create table interactions (
    id uuid primary key default gen_random_uuid(),
    session_id text not null,
    llm_source text not null check (llm_source in ('claude', 'gemini', 'chatgpt', 'other')),
    role text not null check (role in ('user', 'assistant', 'system')),
    content text not null,
    embedding vector(1536),  -- OpenAI text-embedding-3-small dimension
    metadata jsonb default '{}',
    token_count integer,
    created_at timestamptz default now()
);

-- Indexes for common query patterns
create index idx_interactions_session on interactions (session_id);
create index idx_interactions_llm_source on interactions (llm_source);
create index idx_interactions_created_at on interactions (created_at desc);
create index idx_interactions_metadata on interactions using gin (metadata);

-- HNSW index for fast vector similarity search
-- (cosine distance is best for normalized embeddings)
create index idx_interactions_embedding on interactions
    using hnsw (embedding vector_cosine_ops)
    with (m = 16, ef_construction = 64);

-- Function: semantic search with filters
create or replace function search_interactions(
    query_embedding vector(1536),
    match_count int default 10,
    filter_llm_source text default null,
    filter_session_id text default null,
    filter_after timestamptz default null
)
returns table (
    id uuid,
    session_id text,
    llm_source text,
    role text,
    content text,
    metadata jsonb,
    token_count integer,
    created_at timestamptz,
    similarity float
)
language plpgsql
as $$
begin
    return query
    select
        i.id,
        i.session_id,
        i.llm_source,
        i.role,
        i.content,
        i.metadata,
        i.token_count,
        i.created_at,
        1 - (i.embedding <=> query_embedding) as similarity
    from interactions i
    where
        i.embedding is not null
        and (filter_llm_source is null or i.llm_source = filter_llm_source)
        and (filter_session_id is null or i.session_id = filter_session_id)
        and (filter_after is null or i.created_at >= filter_after)
    order by i.embedding <=> query_embedding
    limit match_count;
end;
$$;

-- View: usage stats per LLM source
create or replace view usage_stats as
select
    llm_source,
    count(*) as total_messages,
    count(distinct session_id) as total_sessions,
    sum(token_count) as total_tokens,
    max(created_at) as last_active,
    min(created_at) as first_active
from interactions
group by llm_source;
