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

### Patent data sources

| Source | Module | Credentials (env) |
|---|---|---|
| USPTO (PatentsView) — primary | `patent_sources/uspto.py` | `USPTO_API_KEY` ([free key](https://patentsview.org/apis/keyrequest)) |
| Google Patents Public Data (BigQuery) | `patent_sources/bigquery.py` | `GOOGLE_SERVICE_ACCOUNT_JSON` (BigQuery Job User role) |
| Lens.org | `patent_sources/lens.py` | `LENS_API_KEY` |
| EPO Open Patent Services | `patent_sources/epo.py` | `EPO_OPS_KEY` + `EPO_OPS_SECRET` |

Each source implements the same `PatentSource` interface and returns the same
normalized shape; ingestion iterates every configured source and dedupes on
patent number. A source with no credentials is skipped. All candidates pass
the app-level public-domain check **and** the database trigger gate.

## Features

- **Homepage** — hero, frustration-first search, category pills, featured blueprint cards
- **Browse/Search** — filter sidebar (buildability slider, verified public-domain toggle, sort), responsive list view
- **Blueprint detail** — four-section dashboard (Human Problem / Expired Logic / Build Plan / Master Prompt) with locked/blurred state for free users; locked content **never leaves the server**
- **Validator ("Collision Checker")** — pgvector similarity search of your idea against every blueprint (trigram text fallback when no embeddings key is configured)
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
python -m worker.check_sources         # live-diagnose all 4 sources + LLM + Stripe + DB
python -m worker.backfill_embeddings   # embed the seed blueprints (enables vector Validator)
python -m worker.ingest                # one ingestion pass across all configured sources
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

## Notes

- Seed blueprints are hand-curated examples of the 20+ year-old patent era
  this product mines; live USPTO ingestion replaces/augments them.
- Model strings (`TRANSLATOR_MODEL`, `CODER_MODEL`, `EMBEDDING_MODEL`) are env
  config — swapping providers through an OpenAI-compatible aggregator is a
  one-line change.
