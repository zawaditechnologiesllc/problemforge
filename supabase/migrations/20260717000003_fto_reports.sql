-- ProblemForge — Freedom-to-Operate reports ($99 one-time)
-- Paid via Stripe Checkout (mode=payment); generated asynchronously; the PDF
-- lives in the private 'fto-reports' Storage bucket (created by the backend on
-- first use, or create it manually: Storage -> New bucket -> fto-reports, private).

create table public.fto_reports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  patent_number text not null,
  blueprint_id uuid references public.blueprints(id) on delete set null,
  status text not null default 'pending_payment'
    check (status in ('pending_payment', 'queued', 'processing', 'ready', 'failed')),
  stripe_session_id text,
  verification jsonb not null default '{}',
  report_path text,
  error text,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create index fto_reports_user_idx on public.fto_reports (user_id, created_at desc);

alter table public.fto_reports enable row level security;

create policy "Users can read their own FTO reports"
  on public.fto_reports for select
  using (auth.uid() = user_id);

-- writes go through the backend service role only
