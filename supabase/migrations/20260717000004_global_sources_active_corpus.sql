-- ProblemForge — 20 regional sources + internal active-patent landscape corpus

-- Track which jurisdiction each ingested patent came from (US, EP, JP, ...)
alter table public.raw_patents add column if not exists jurisdiction text;
create index if not exists raw_patents_jurisdiction_idx
  on public.raw_patents (jurisdiction);

-- Internal-only corpus of RECENT (active-era) filings. Powers the Validator's
-- aggregate caution signal. Deliberately separate from raw_patents/blueprints:
-- it is NEVER joined to user-facing tables, has no read policies, and no API
-- endpoint returns its rows. The public-domain trigger gate on raw_patents is
-- untouched — nothing from this table can become a blueprint.
create table public.active_patents (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  jurisdiction text,
  patent_number text unique not null,
  title text not null,
  abstract text,
  filing_date date,
  embedding vector(1536),
  ingested_at timestamptz not null default now()
);

create index active_patents_embedding_idx
  on public.active_patents using hnsw (embedding vector_cosine_ops);

alter table public.active_patents enable row level security;
-- no policies: service-role only

-- Aggregate-only similarity probe: returns ids + similarity, never titles or
-- numbers, and is not executable by client roles at all.
create or replace function public.match_active_patents(
  query_embedding vector(1536),
  match_count int default 3
)
returns table (id uuid, similarity float)
language sql
stable
security definer
set search_path = public
as $$
  select a.id, 1 - (a.embedding <=> query_embedding) as similarity
  from public.active_patents a
  where a.embedding is not null
  order by a.embedding <=> query_embedding
  limit match_count
$$;

revoke execute on function public.match_active_patents(vector, int) from public;
revoke execute on function public.match_active_patents(vector, int) from anon;
revoke execute on function public.match_active_patents(vector, int) from authenticated;
