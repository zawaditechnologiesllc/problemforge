# ProblemForge

**Find validated startup problems from expired patents.**

ProblemForge mines expired and abandoned patents — inventions that are now
public domain — and uses an LLM pipeline to translate each one into a
scannable **Idea Blueprint**: the real human problem it solved, the
now-free-to-copy core logic, a modern 3-step build plan, and a ready-to-paste
**master prompt** for AI coding tools like Cursor and Windsurf.

```
Expired patent → AI translation → Idea Blueprint → "Copy Master Prompt" → MVP in Cursor
```

## Architecture

| Piece | Tech | Deploys to |
|---|---|---|
| `frontend/` | Next.js 14 (App Router) · TypeScript · Tailwind CSS | **Vercel** |
| `backend/` | FastAPI · Python 3.11 (REST API + Stripe + LLM pipeline) | **Render** (`render.yaml`) |
| `backend/worker/` | Weekly patent ingestion + embedding backfill | **Render cron** |
| `supabase/` | Postgres + pgvector schema, RLS, seed data | **Supabase** |

```
[Weekly cron worker]
  → Patent source adapters (all behind one interface, auto-enabled by env creds):
      USPTO/PatentsView · Google Patents BigQuery · Lens.org · EPO OPS
  → raw_patents  (hard public-domain gate: Postgres trigger)
  → LLM translation (DeepSeek via OpenRouter) → 4-section blueprint
  → embeddings (pgvector) → blueprints table
                                  │
        [Next.js on Vercel] ⇄ [FastAPI on Render] ⇄ [Supabase Postgres + Auth + Storage]
                                  │
                          [Stripe Checkout/Portal/Webhooks]
                          (subscriptions + $99 one-time FTO reports → PDF)
```

### Patent data sources — 20 regions, 4 providers

Very few national patent offices expose practical public APIs, so the source
layer has two levels. **Providers** are the adapters that speak to real
external APIs; **regional sources** are 20 jurisdiction-scoped sources that
route to the best configured provider for that region, with automatic
fallback:

| Provider | Module | Credentials (env) | Coverage |
|---|---|---|---|
| USPTO (PatentsView) | `patent_sources/uspto.py` | `USPTO_API_KEY` ([free key](https://patentsview.org/apis/keyrequest)) | US |
| Google Patents Public Data (BigQuery) | `patent_sources/bigquery.py` | `GOOGLE_SERVICE_ACCOUNT_JSON` (BigQuery Job User role) | 100+ jurisdictions |
| Lens.org | `patent_sources/lens.py` | `LENS_API_KEY` | 100+ jurisdictions |
| EPO Open Patent Services (DOCDB) | `patent_sources/epo.py` | `EPO_OPS_KEY` + `EPO_OPS_SECRET` | Europe + worldwide |

**The 20 regions** (`patent_sources/regions.py`): US, Europe (EPO-wide), UK,
Germany, France, Netherlands, Sweden, Japan, South Korea, China, Taiwan,
Canada, Australia, New Zealand, India, Singapore, Israel, Brazil, Mexico,
South Africa — the major innovation economies plus the emerging startup
markets where building from public-domain engineering has the most leverage.
Credentials for **any one** global provider (Lens, BigQuery, or EPO) light up
all 20 regions at once; US prefers PatentsView and Europe prefers EPO OPS
when those are configured.

Ingestion iterates every enabled regional source, stamps each patent with its
jurisdiction, and dedupes on patent number. All candidates pass the
app-level public-domain check **and** the database trigger gate.

### Ingestion coverage: timeless → the 20-year boundary

Old does not mean obsolete — a mechanism patented in the 1960s can still be
the right solution today (plenty of 1970s engineering still flies). The only
hard boundary is legal, not chronological: a patent qualifies once it is in
the public domain. Two ingestion modes share the same pipeline:

- **Weekly cron** (`worker/ingest.py`) — picks up filings that crossed the
  20-year statutory boundary in the last week, across all regions.
- **Historical backfill** (`worker/backfill_history.py`) — walks the entire
  eligible range from `INGEST_BACKFILL_START` (default **1790-01-01**, the
  start of US patent records) up to today minus 20 years. Pre-1980 decades
  are walked in year-sized windows (records are sparse), recent decades
  month-sized. Idempotent and resumable — rerun it and it continues where
  the data left off.

### The 5-Point Validation Framework

Every Validator run pressure-tests the idea against five pillars (inspired by
[this validation framework](https://www.rapidnative.com/tools/app-idea-validator)),
each scored 0–100 with a concrete recommendation:

1. **Market Size** — are enough people actively searching for or discussing
   the problem? Assessed by demographics, with the **best demographic to
   target** named.
2. **Competition** — do existing solutions have proven demand? Names the
   **gaps to differentiate on**, grounded in real community questions.
3. **Feasibility** — can an MVP ship in 2–3 months with no-code tools or a
   small team? Includes the smallest shippable scope.
4. **Monetization Potential** — is there a concrete revenue model?
   **Recommends the best one** (e.g. subscription for ongoing value, premium
   B2B pricing).
5. **Uniqueness** — what makes it compelling? Better UX or a focused niche is
   enough; it doesn't need to be a new invention.

Implemented in `backend/app/services/framework.py`: LLM-generated
(strict-JSON validated, graceful null when no LLM key), grounded in the
expired-patent matches and community questions, and **cached 24h by idea
hash** so repeat runs are free.

### Community demand signals (no API keys)

`backend/app/services/demand.py` collects **real questions real people ask**
from public `old.reddit.com` and Quora search pages — plain HTTP with an
honest User-Agent, one request per source per query, results cached 24 hours.
They feed three places: the Validator's "Real questions from real people"
list, the framework's Market Size / Competition evidence, and
`demand_signal_score` on newly ingested blueprints. Both scrapers are
best-effort by design (Quora frequently serves bots a login wall → empty
result, never an error). Keep volume tiny and review each site's terms
before scaling this up; set `DEMAND_SIGNALS_ENABLED=false` to turn it off.

### Caching (cost control)

`backend/app/services/cache.py` — automatic backend selection:

- **Redis** when `REDIS_URL` is set. Recommended: **Upstash Redis**
  (serverless, generous free tier, `rediss://` URL) or **Render Key Value**
  (same-datacenter as the API). Cloudflare KV or Memcached work too if you
  swap the client.
- **In-process TTL cache** otherwise — zero setup for dev/single instance.

What's cached: embeddings 7 days (identical text → identical vector; every
repeat Validator run is a free API call), framework analyses 24h, demand
signals 24h. Two further cost levers already in place: blueprints themselves
are translated once and stored forever in Postgres (the DB is the ultimate
cache), and the translator prompt shares a fixed system prefix so
provider-side prompt caching (e.g. DeepSeek cache-hit pricing) applies.

### Internal active-patent landscape (Validator signal)

A separate, **internal-only** corpus (`active_patents`) of recent, active-era
filings powers an aggregate caution signal in the Validator: when a
submitted idea is highly similar to recent filings, the user sees a generic
"recent patent-landscape activity detected" note advising a professional
prior-art search. Hard boundaries, by design:

- Never joined to blueprints — the public-domain trigger gate is untouched,
  so nothing in this corpus can ever surface as a blueprint.
- No API endpoint returns its rows; the similarity RPC returns ids +
  scores only and is not executable by client roles.
- Users see only the aggregate level and note — never patent numbers,
  titles, or any identifying detail.
- Toggle the user-facing note with `ACTIVE_SIGNAL_ENABLED`.

Refresh it monthly with `python -m worker.ingest_active` (cron included in
`render.yaml`).

## Features

- **Homepage** — hero, frustration-first search, category pills, featured blueprint cards
- **Browse/Search** — filter sidebar (buildability slider, verified public-domain toggle, sort), responsive list view
- **Blueprint detail** — four-section dashboard (Human Problem / Expired Logic / Build Plan / Master Prompt) with locked/blurred state for free users; locked content **never leaves the server**
- **Validator ("Collision Checker")** — pgvector similarity search of your idea against every blueprint (trigram text fallback when no embeddings key is configured), plus the **5-Point Validation Framework** and real community demand signals (below)
- **Auth** — Supabase email/password + Google OAuth
- **Billing** — Stripe Checkout + Customer Portal + webhooks driving `profiles.tier`
- **Account dashboard** — usage meters, saved blueprints, API keys, billing management
- **Developer API** — `X-API-Key` auth against `/api/v1/*` (Pro: 5,000 req/mo; Enterprise: unlimited), bulk CSV export on Enterprise
- Fully responsive — mobile and desktop layouts throughout

## Pricing tiers

| | Free | **Builder — $19/mo** | Pro — $49/mo | Enterprise — $150/mo |
|---|---|---|---|---|
| Searches / month | 50 | 500 | 2,500 | Unlimited |
| Human Problem + Expired Logic | ✅ | ✅ | ✅ | ✅ |
| Full build plans + master prompts | — | ✅ | ✅ | ✅ |
| Verified Public Domain filter | — | ✅ | ✅ | ✅ |
| Validator runs / month | 5 | 100 | 500 | Unlimited |
| Developer API + keys | — | — | 5,000 req/mo | Unlimited API calls |
| Bulk data export (CSV) | — | — | — | ✅ |
| Priority support | — | — | — | ✅ |

All limits are enforced **server-side** (`backend/app/tiers.py` is the single
source of truth; API-key traffic is metered per request).

### Freedom-to-Operate reports ($99 one-time)

Fully implemented: order from any blueprint page or the account dashboard →
Stripe Checkout (mode=payment) → the webhook queues an async job that
re-verifies the patent's expired status (statutory-term math + recorded legal
status + a live USPTO lookup), adds an LLM plain-language analysis, renders a
PDF, and stores it in a **private** Supabase Storage bucket. Users download
via short-lived signed URLs; status is tracked
(queued → processing → ready/failed with retry). Every report carries the
required disclaimer: an AI-generated informational summary, **not legal
advice**.

## Non-negotiable guardrails

1. A patent row **cannot exist** unless it was filed 20+ years ago or its
   source status marks it expired — enforced by a Postgres trigger
   (`assert_public_domain`), not a UI toggle, and mirrored in the worker.
2. LLM and Stripe secrets live only in backend env vars — never client-side.
3. Tier gating happens in the API: free/anonymous responses simply omit
   `build_plan` and `master_prompt`.
4. Blueprint content and FTO reports are informational, not legal advice, and
   both the UI and every generated PDF say so.

## Security posture

- **Payments:** Stripe Checkout/Portal only — no card data touches the app;
  webhooks are signature-verified and idempotent; prices are mapped
  server-side (the client never chooses an amount).
- **Auth:** Supabase JWTs verified server-side (HS256 secret or Auth API);
  API keys stored as SHA-256 hashes with one-time plaintext display and
  revocation; per-request metering.
- **Database:** RLS on every table; the browser only ever holds the anon key;
  the service-role key exists only on the backend.
- **API:** per-IP rate limiting (120 req/min) + tier quotas; security headers
  (HSTS, nosniff, frame-deny, referrer/permissions policy) on both the
  FastAPI service and the Next.js app; CORS restricted to the frontend origin.
- **Storage:** FTO PDFs live in a private bucket, served via signed URLs that
  expire in 1 hour.
- **Data purity:** locked content (build plans, master prompts) never leaves
  the server for unentitled users.

## Local development

```bash
# 1. Database — create a Supabase project, then in the SQL editor run:
#    supabase/migrations/20260717000001_init.sql, then supabase/seed.sql

# 2. Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in Supabase + Stripe keys
uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd frontend
npm install
cp .env.example .env.local   # point NEXT_PUBLIC_API_URL at http://localhost:8000
npm run dev
```

Optional workers (need at least one patent-source credential, plus
`LLM_API_KEY` / `EMBEDDINGS_API_KEY` for translation/vectors):

```bash
cd backend
python -m worker.check_sources         # diagnose 4 providers + 20-region routing + LLM + Stripe + DB
python -m worker.backfill_embeddings   # embed the seed blueprints (enables vector Validator)
python -m worker.ingest                # one weekly-style pass across all configured regions
python -m worker.backfill_history      # timeless backfill -> the 20-year boundary (resumable)
python -m worker.ingest_active         # refresh the internal active-landscape corpus
```

Backend tests (all 4 source adapters, FTO verification + PDF, parser, tiers):

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

## Deploying

Step-by-step instructions for Supabase → Render → Vercel → Stripe are in
**[DEPLOYMENT.md](./DEPLOYMENT.md)**.

## Policy pages

The frontend ships complete, product-specific policy pages, linked from the
footer and the signup flow: `/terms`, `/privacy`, `/refunds`,
`/acceptable-use`, `/disclaimer`. Before launch, set your real contact email
and operating entity in `frontend/lib/site.ts` and have counsel review the
pages — they are a strong starting point, not legal advice.

## Notes

- Seed blueprints are hand-curated examples of the 20+ year-old patent era
  this product mines; live ingestion replaces/augments them.
- Model strings (`TRANSLATOR_MODEL`, `CODER_MODEL`, `EMBEDDING_MODEL`) are env
  config — swapping providers through an OpenAI-compatible aggregator is a
  one-line change.
