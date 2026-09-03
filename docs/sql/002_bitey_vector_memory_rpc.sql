-- Bitey IA — canonical semantic memory search
-- Target project: dedicated Bitey IA Supabase project only.
-- Requires pgvector and the existing bitey.memories.embedding column.
-- The embedding dimension is intentionally provider-neutral; callers must use
-- vectors compatible with the stored vectors.

create or replace function bitey.match_memories(query_embedding vector, match_count integer default 8)
returns table (
  id uuid,
  session_id uuid,
  memory_type text,
  content text,
  summary text,
  source text,
  confidence numeric,
  importance numeric,
  metadata jsonb,
  similarity double precision,
  created_at timestamptz
)
language sql
stable
as $$
  select
    m.id,
    m.session_id,
    m.memory_type,
    m.content,
    m.summary,
    m.source,
    m.confidence,
    m.importance,
    m.metadata,
    1 - (m.embedding <=> query_embedding) as similarity,
    m.created_at
  from bitey.memories m
  where m.embedding is not null
  order by m.embedding <=> query_embedding
  limit greatest(1, least(match_count, 50));
$$;
