# Deploying ProblemForge

Order matters: **Supabase → Render (backend) → Vercel (frontend) → Stripe webhook**.
Each step produces values the next one needs.

---

## 1. Supabase (database + auth)

1. Create a project at [supabase.com](https://supabase.com) (any region).
2. **SQL Editor** → paste and run, in order:
   - `supabase/migrations/20260717000001_init.sql`
   - `supabase/seed.sql`
3. **Project Settings → API** — note these values:
   - `Project URL` → `SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_URL`
   - `anon` key → `SUPABASE_ANON_KEY` / `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `service_role` key → `SUPABASE_SERVICE_ROLE_KEY` (backend only, keep secret)
   - JWT secret (if your project shows one) → `SUPABASE_JWT_SECRET` (optional;
     the backend falls back to verifying tokens via the Auth API)
4. **Authentication → Providers**:
   - Email: enabled by default.
   - Google (optional): add your Google OAuth client ID/secret
     ([guide](https://supabase.com/docs/guides/auth/social-login/auth-google)).
5. **Authentication → URL Configuration** (come back after step 3 if needed):
   - Site URL: your Vercel URL, e.g. `https://problemforge.vercel.app`
   - Redirect URLs: `https://problemforge.vercel.app/auth/callback` and
     `http://localhost:3000/auth/callback`

## 2. Stripe (products first, webhook last)

1. **Products → Add product**, create three recurring monthly prices and one
   one-time price:
   - `ProblemForge Builder` — **$19/month** → copy Price ID → `STRIPE_PRICE_BUILDER`
   - `ProblemForge Pro` — **$49/month** → copy Price ID → `STRIPE_PRICE_PRO`
   - `ProblemForge Enterprise` — **$150/month** → copy Price ID → `STRIPE_PRICE_ENTERPRISE`
   - `Freedom-to-Operate Report` — **$99 one-time** → copy Price ID → `STRIPE_PRICE_FTO`
2. **Developers → API keys** → copy the Secret key → `STRIPE_SECRET_KEY`.
3. (Webhook comes in step 5, after the backend URL exists.)

## 3. Render (backend + cron)

1. Push this repo to GitHub (already done if you're reading this there).
2. Render dashboard → **New + → Blueprint** → connect the repo. Render reads
   `render.yaml` and creates:
   - `problemforge-api` — FastAPI web service (health check `/healthz`)
   - `problemforge-ingestion` — weekly cron (cron requires a paid plan; the
     app works fine without it — skip or delete the cron service if on free tier)
3. Fill in the env vars Render prompts for:

   | Var | Value |
   |---|---|
   | `FRONTEND_URL` | your Vercel URL (set a placeholder now, update after step 4) |
   | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY` | from step 1 |
   | `SUPABASE_JWT_SECRET` | optional (see step 1) |
   | `STRIPE_SECRET_KEY`, `STRIPE_PRICE_BUILDER`, `STRIPE_PRICE_PRO`, `STRIPE_PRICE_ENTERPRISE`, `STRIPE_PRICE_FTO` | from step 2 |
   | `STRIPE_WEBHOOK_SECRET` | placeholder for now — real value in step 5 |
   | `LLM_API_KEY` | OpenRouter key (ingestion translation + FTO analysis) |
   | `EMBEDDINGS_API_KEY` | OpenAI-compatible key (enables the vector Validator; optional — text fallback works without it) |
   | `USPTO_API_KEY` | free key from [patentsview.org](https://patentsview.org/apis/keyrequest) — primary patent source |
   | `GOOGLE_SERVICE_ACCOUNT_JSON` | optional — full GCP service-account JSON (one line) with the BigQuery Job User role, enables the Google Patents source |
   | `LENS_API_KEY` | optional — Lens.org API token, enables the Lens source |
   | `EPO_OPS_KEY` / `EPO_OPS_SECRET` | optional — EPO OPS app credentials from [developers.epo.org](https://developers.epo.org), enables the EPO source |

   Patent sources activate automatically when their credentials are present;
   ingestion needs at least one (USPTO recommended).

4. Deploy. Note the service URL, e.g. `https://problemforge-api.onrender.com`.
   Check `https://problemforge-api.onrender.com/healthz` returns `{"status":"ok"}`.

## 4. Vercel (frontend)

1. Vercel dashboard → **Add New → Project** → import the repo.
2. **Root Directory: `frontend`** (important). Framework preset: Next.js.
3. Environment variables:

   | Var | Value |
   |---|---|
   | `NEXT_PUBLIC_SUPABASE_URL` | from step 1 |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | from step 1 |
   | `NEXT_PUBLIC_API_URL` | the Render URL from step 3 (no trailing slash) |
   | `NEXT_PUBLIC_SITE_URL` | the Vercel production URL |

4. Deploy, note the production URL, then:
   - update `FRONTEND_URL` on the Render service to this URL (and redeploy),
   - set the Supabase Auth Site URL / Redirect URLs (step 1.5).

## 5. Stripe webhook

1. **Developers → Webhooks → Add endpoint**:
   - URL: `https://problemforge-api.onrender.com/api/v1/billing/webhook`
   - Events: `checkout.session.completed`,
     `customer.subscription.updated`, `customer.subscription.deleted`
2. Copy the signing secret (`whsec_...`) → set `STRIPE_WEBHOOK_SECRET` on the
   Render service → redeploy.
3. Test subscriptions: sign up on the site → Pricing → Start Builder Plan →
   pay with card `4242 4242 4242 4242` (test mode) → Account page should show
   the Builder badge within a few seconds.
4. Test FTO: open any blueprint → "Freedom-to-Operate Report — $99" → pay in
   test mode → Account → FTO Reports shows Queued → Generating → Ready with a
   PDF download. (The `checkout.session.completed` event you already
   subscribed to covers this — no extra webhook config.)

### Storage bucket for FTO PDFs

The backend auto-creates a **private** `fto-reports` bucket on first report.
If your Supabase project restricts bucket creation, create it manually:
Storage → New bucket → name `fto-reports` → Public **off**. Downloads use
1-hour signed URLs; no public access is ever required.

## 6. Post-deploy (optional but recommended)

From any machine with the backend env vars set (or Render's Shell tab):

```bash
cd backend
python -m worker.check_sources         # live-verify all 4 patent sources + LLM + embeddings + DB + Stripe prices
python -m worker.backfill_embeddings   # embed seed blueprints → vector Validator
python -m worker.ingest                # first live ingestion pass across all configured sources
```

## Smoke checklist

- [ ] `/healthz` on Render returns ok
- [ ] Homepage shows 6 seeded blueprint cards (mobile + desktop)
- [ ] Browse search returns results; filters and sort work
- [ ] Blueprint detail: sections 3–4 locked when signed out
- [ ] Sign up (email + Google), Account dashboard loads with Free badge
- [ ] Validator returns matches (text fallback is fine pre-embeddings)
- [ ] $19, $49, and $150 checkout flows complete in Stripe test mode; tier updates
- [ ] $99 FTO checkout completes; report goes Queued → Ready; PDF downloads and carries the not-legal-advice disclaimer
- [ ] Master prompt visible + copyable on a paid account
- [ ] Pro account can create an API key and `curl -H "X-API-Key: pf_live_..." $API/api/v1/blueprints`
- [ ] Enterprise account shows Unlimited usage bars and can download the CSV export
- [ ] `python -m worker.check_sources` passes on Render (all configured data sources live)
- [ ] API responses include security headers; burst traffic gets HTTP 429
