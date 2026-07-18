-- ProblemForge — admin role + editable site settings (footer, contact, etc.)

alter table public.profiles
  add column if not exists is_admin boolean not null default false;

-- Key/value site settings editable from the admin panel. Nothing here is
-- secret — it is public site chrome (footer address, contact email, links).
create table public.site_settings (
  key text primary key,
  value jsonb not null default '{}',
  updated_at timestamptz not null default now()
);

alter table public.site_settings enable row level security;

create policy "Site settings are publicly readable"
  on public.site_settings for select
  using (true);
-- writes go through the backend service role (admin endpoints) only

insert into public.site_settings (key, value) values (
  'footer',
  jsonb_build_object(
    'company_name', 'Zawadi Technologies LLC',
    'product_name', 'ProblemForge',
    'tagline', 'Validated startup problems mined from expired, public-domain patents across 20 regions.',
    'address', '',
    'contact_email', '',
    'links', jsonb_build_array()
  )
) on conflict (key) do nothing;

-- Grant the first admin manually after sign-up (no hardcoded emails in code):
--   update public.profiles set is_admin = true where email = 'you@yourcompany.com';
