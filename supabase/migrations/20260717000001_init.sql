-- ProblemForge — initial schema
-- Run via the Supabase SQL editor or `supabase db push`.

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
create extension if not exists vector;
create extension if not exists pg_trgm;

-- ---------------------------------------------------------------------------
-- Raw ingested patent data
-- ---------------------------------------------------------------------------
create table public.raw_patents (
  id uuid primary key default gen_random_uuid(),
  source text not null check (source in ('uspto', 'bigquery', 'lens', 'epo', 'seed')),
  patent_number text unique not null,
  title text not null,
  abstract text,
  full_text text,
  filing_date date,
  legal_status text,
  domain text check (domain in ('software', 'mechanical', 'medical')),
  drawing_urls text[] not null default '{}',
  public_domain_verified_at timestamptz,
  ingested_at timestamptz not null default now()
);

-- The public-domain filter is a hard, database-level gate — never only a UI
-- toggle. A patent row cannot exist unless it was filed 20+ years ago or its
-- source legal status marks it as expired.
create or replace function public.assert_public_domain()
returns trigger
language plpgsql
as $$
begin
  if not (
    (new.filing_date is not null and new.filing_date <= (current_date - interval '20 years'))
    or (new.legal_status is not null and new.legal_status ilike '%expired%')
  ) then
    raise exception 'PUBLIC_DOMAIN_GATE: patent % is not verifiably public domain (filing_date=%, legal_status=%)',
      new.patent_number, new.filing_date, new.legal_status;
  end if;
  new.public_domain_verified_at := now();
  return new;
end;
$$;

create trigger raw_patents_public_domain_gate
before insert or update on public.raw_patents
for each row execute function public.assert_public_domain();

-- ---------------------------------------------------------------------------
-- AI-translated Idea Blueprints
-- ---------------------------------------------------------------------------
create table public.blueprints (
  id uuid primary key default gen_random_uuid(),
  raw_patent_id uuid references public.raw_patents(id) on delete cascade,
  patent_number text,
  title text not null,
  domain text not null check (domain in ('software', 'mechanical', 'medical')),
  human_problem text not null,
  expired_logic text not null,
  build_plan text not null,
  master_prompt text not null,
  buildability_score int check (buildability_score between 0 and 100),
  demand_signal_score int check (demand_signal_score between 0 and 100),
  embedding vector(1536), -- embeds human_problem, used by the Validator
  public_domain_verified boolean not null default true,
  is_public boolean not null default true,
  created_at timestamptz not null default now()
);

create index blueprints_domain_idx on public.blueprints (domain);
create index blueprints_buildability_idx on public.blueprints (buildability_score desc);
create index blueprints_created_idx on public.blueprints (created_at desc);
create index blueprints_title_trgm_idx on public.blueprints using gin (title gin_trgm_ops);
create index blueprints_problem_trgm_idx on public.blueprints using gin (human_problem gin_trgm_ops);
create index blueprints_embedding_idx on public.blueprints using hnsw (embedding vector_cosine_ops);

-- ---------------------------------------------------------------------------
-- User profiles (extends Supabase auth.users)
-- ---------------------------------------------------------------------------
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  tier text not null default 'free' check (tier in ('free', 'builder', 'pro')),
  stripe_customer_id text,
  stripe_subscription_id text,
  monthly_search_count int not null default 0,
  monthly_validate_count int not null default 0,
  usage_reset_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------------------
-- Usage tracking (rate limiting + billing analytics)
-- ---------------------------------------------------------------------------
create table public.usage_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete set null,
  event_type text not null check (event_type in ('search', 'copy_prompt', 'validator_run', 'api_call', 'export', 'fto_report')),
  blueprint_id uuid references public.blueprints(id) on delete set null,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create index usage_events_user_idx on public.usage_events (user_id, created_at desc);

-- ---------------------------------------------------------------------------
-- Saved / bookmarked blueprints
-- ---------------------------------------------------------------------------
create table public.saved_blueprints (
  user_id uuid not null references public.profiles(id) on delete cascade,
  blueprint_id uuid not null references public.blueprints(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, blueprint_id)
);

-- ---------------------------------------------------------------------------
-- Developer API keys (Pro tier)
-- ---------------------------------------------------------------------------
create table public.api_keys (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  name text not null default 'default',
  key_prefix text not null,
  key_hash text not null unique, -- sha256 of the full key; plaintext is never stored
  created_at timestamptz not null default now(),
  last_used_at timestamptz,
  revoked_at timestamptz
);

create index api_keys_user_idx on public.api_keys (user_id);

-- ---------------------------------------------------------------------------
-- Ingestion run log (monitoring)
-- ---------------------------------------------------------------------------
create table public.ingestion_runs (
  id uuid primary key default gen_random_uuid(),
  source text,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  fetched int not null default 0,
  inserted int not null default 0,
  translated int not null default 0,
  failed int not null default 0,
  notes text
);

-- ---------------------------------------------------------------------------
-- Validator: vector similarity search over blueprint problem embeddings
-- ---------------------------------------------------------------------------
create or replace function public.match_blueprints(
  query_embedding vector(1536),
  match_count int default 5
)
returns table (
  id uuid,
  title text,
  domain text,
  patent_number text,
  human_problem text,
  expired_logic text,
  buildability_score int,
  demand_signal_score int,
  similarity float
)
language sql
stable
as $$
  select
    b.id, b.title, b.domain, b.patent_number, b.human_problem, b.expired_logic,
    b.buildability_score, b.demand_signal_score,
    1 - (b.embedding <=> query_embedding) as similarity
  from public.blueprints b
  where b.is_public and b.embedding is not null
  order by b.embedding <=> query_embedding
  limit match_count
$$;

-- Trigram fallback used when no embeddings provider is configured.
create or replace function public.match_blueprints_text(
  query_text text,
  match_count int default 5
)
returns table (
  id uuid,
  title text,
  domain text,
  patent_number text,
  human_problem text,
  expired_logic text,
  buildability_score int,
  demand_signal_score int,
  similarity float
)
language sql
stable
as $$
  select
    b.id, b.title, b.domain, b.patent_number, b.human_problem, b.expired_logic,
    b.buildability_score, b.demand_signal_score,
    greatest(
      similarity(b.title, query_text),
      similarity(b.human_problem, query_text)
    )::float as similarity
  from public.blueprints b
  where b.is_public
  order by 9 desc
  limit match_count
$$;

-- ---------------------------------------------------------------------------
-- Row Level Security
-- The FastAPI backend uses the service-role key (bypasses RLS). These
-- policies cover direct client access via the anon/authenticated keys.
-- ---------------------------------------------------------------------------
alter table public.raw_patents enable row level security;
alter table public.blueprints enable row level security;
alter table public.profiles enable row level security;
alter table public.usage_events enable row level security;
alter table public.saved_blueprints enable row level security;
alter table public.api_keys enable row level security;
alter table public.ingestion_runs enable row level security;

create policy "Public blueprints are readable by everyone"
  on public.blueprints for select
  using (is_public);

create policy "Users can read their own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users can read their own saved blueprints"
  on public.saved_blueprints for select
  using (auth.uid() = user_id);

-- raw_patents, usage_events, api_keys, ingestion_runs: service-role only (no policies).
