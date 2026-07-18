-- ProblemForge — Modern AI Playbooks, visible 5-point validation scores,
-- and the startup-community corpus.

-- Per-blueprint enrichment, generated once by the LLM and stored:
--   playbook          — does the problem still exist + how to solve it with
--                       AI today + full stack (design/coding/configuration/
--                       integration/testing) + marketing channels
--   validation        — the 5-Point Validation Framework result (shown to
--                       ALL users so they can judge how valid the idea is)
--   validation_score  — overall 0-100, denormalized for list views/sorting
alter table public.blueprints add column if not exists playbook jsonb;
alter table public.blueprints add column if not exists validation jsonb;
alter table public.blueprints add column if not exists validation_score int
  check (validation_score between 0 and 100);

create index if not exists blueprints_validation_score_idx
  on public.blueprints (validation_score desc nulls last);

-- Startup ideas people post publicly in communities (old.reddit). Unlike the
-- internal active-patent corpus, this data IS user-facing: matches are shown
-- with links back to the original public posts.
create table public.community_posts (
  id uuid primary key default gen_random_uuid(),
  source text not null default 'reddit',
  community text,             -- e.g. r/SomebodyMakeThis
  title text not null,
  url text unique not null,
  score int not null default 0,          -- upvotes
  num_comments int not null default 0,
  embedding vector(1536),
  ingested_at timestamptz not null default now()
);

create index community_posts_embedding_idx
  on public.community_posts using hnsw (embedding vector_cosine_ops);

alter table public.community_posts enable row level security;
-- service-role only at the database layer; rows reach users through the API

create or replace function public.match_community_posts(
  query_embedding vector(1536),
  match_count int default 3
)
returns table (
  id uuid,
  title text,
  url text,
  community text,
  score int,
  num_comments int,
  similarity float
)
language sql
stable
as $$
  select
    c.id, c.title, c.url, c.community, c.score, c.num_comments,
    1 - (c.embedding <=> query_embedding) as similarity
  from public.community_posts c
  where c.embedding is not null
  order by c.embedding <=> query_embedding
  limit match_count
$$;
