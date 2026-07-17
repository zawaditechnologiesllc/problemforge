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
  → USPTO/PatentsView adapter (filters: filed ≥20y ago OR expired for non-payment)
  → raw_patents  (hard public-domain gate: Postgres trigger)
  → LLM translation (DeepSeek via OpenRouter) → 4-section blueprint
  → embeddings (pgvector) → blueprints table
                                  │
        [Next.js on Vercel] ⇄ [FastAPI on Render] ⇄ [Supabase Postgres + Auth]
                                  │
                          [Stripe Checkout/Portal/Webhooks]
```

## Features

- **Homepage** — hero, frustration-first search, category pills, featured blueprint cards
- **Browse/Search** — filter sidebar (buildability slider, verified public-domain toggle, sort), responsive list view
- **Blueprint detail** — four-section dashboard (Human Problem / Expired Logic / Build Plan / Master Prompt) with locked/blurred state for free users; locked content **never leaves the server**
- **Validator ("Collision Checker")** — pgvector similarity search of your idea against every blueprint (trigram text fallback when no embeddings key is configured)
- **Auth** — Supabase email/password + Google OAuth
- **Billing** — Stripe Checkout + Customer Portal + webhooks driving `profiles.tier`
- **Account dashboard** — usage meters, saved blueprints, API keys, billing management
- **Developer API** — `X-API-Key` auth against `/api/v1/*` (Pro tier), plus bulk CSV export
- Fully responsive — mobile and desktop layouts throughout

## Pricing tiers

| | Free | **Builder — $19/mo** | Pro — $49/mo |
|---|---|---|---|
| Searches / month | 50 | 500 | 2,000 |
| Human Problem + Expired Logic | ✅ | ✅ | ✅ |
| Full build plans + master prompts | — | ✅ | ✅ |
| Verified Public Domain filter | — | ✅ | ✅ |
| Validator runs / month | 5 | 100 | 1,000 |
| Developer API + keys | — | — | ✅ |
| Bulk CSV export | — | — | ✅ |

All limits are enforced **server-side**. A $99 one-time Freedom-to-Operate
report is stubbed on the pricing page as "coming soon."

## Non-negotiable guardrails

1. A patent row **cannot exist** unless it was filed 20+ years ago or its
   source status marks it expired — enforced by a Postgres trigger
   (`assert_public_domain`), not a UI toggle, and mirrored in the worker.
2. LLM and Stripe secrets live only in backend env vars — never client-side.
3. Tier gating happens in the API: free/anonymous responses simply omit
   `build_plan` and `master_prompt`.
4. Blueprint content is informational, not legal advice, and the UI says so.

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

Optional workers (need `LLM_API_KEY` / `EMBEDDINGS_API_KEY` / `USPTO_API_KEY`):

```bash
cd backend
python -m worker.backfill_embeddings   # embed the seed blueprints (enables vector Validator)
python -m worker.ingest                # one ingestion pass from the USPTO
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
