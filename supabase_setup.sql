-- 1. Enable the pgvector extension
create extension if not exists vector;

-- 2. Create the documents table
create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  content text,
  metadata jsonb,
  embedding vector(3072) -- Gemini gemini-embedding-2 uses 3072 dimensions
);

-- 3. Create the match_documents function for similarity search
create or replace function match_documents (
  query_embedding vector(3072),
  match_count int DEFAULT null,
  filter jsonb DEFAULT '{}'
) returns table (
  id uuid,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
#variable_conflict use_column
begin
  return query
  select
    id,
    content,
    metadata,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where metadata @> filter
  order by documents.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- 4. Disable Row Level Security so the backend can read/write using the Anon key
alter table documents disable row level security;
