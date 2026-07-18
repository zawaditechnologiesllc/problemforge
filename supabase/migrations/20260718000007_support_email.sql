-- ProblemForge — support chat (site widget -> admin panel Messages)

create table public.support_threads (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  subject text,
  status text not null default 'open' check (status in ('open', 'closed')),
  created_at timestamptz not null default now(),
  last_message_at timestamptz not null default now()
);

create index support_threads_status_idx
  on public.support_threads (status, last_message_at desc);
create index support_threads_user_idx
  on public.support_threads (user_id, last_message_at desc);

create table public.support_messages (
  id uuid primary key default gen_random_uuid(),
  thread_id uuid not null references public.support_threads(id) on delete cascade,
  sender text not null check (sender in ('user', 'admin')),
  body text not null,
  created_at timestamptz not null default now(),
  read_at timestamptz
);

create index support_messages_thread_idx
  on public.support_messages (thread_id, created_at);

alter table public.support_threads enable row level security;
alter table public.support_messages enable row level security;
-- service-role only at the database layer; access is mediated by the API
