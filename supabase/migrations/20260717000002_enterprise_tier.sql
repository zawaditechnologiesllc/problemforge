-- ProblemForge — Enterprise tier ($150/mo) + metered API requests
-- Adds the 'enterprise' tier (unlimited API calls, bulk export, priority
-- support) and the monthly counter that meters Pro-tier API-key requests.

alter table public.profiles drop constraint if exists profiles_tier_check;
alter table public.profiles add constraint profiles_tier_check
  check (tier in ('free', 'builder', 'pro', 'enterprise'));

alter table public.profiles
  add column if not exists monthly_api_count int not null default 0;
