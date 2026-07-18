# ProblemForge — Pre-Launch Audit (CTO sign-off)

A Zawadi Technologies LLC product. This is the cross-check of everything
that must be true before taking real users and real money. Items marked ✅
are **verified in code/tests in this repo**; items marked ☐ are **operator
actions** that can only be done in the live environments.

---

## 1. Security — verified

Automated security smoke suite: `backend/tests/test_security.py`
(20 checks, runs on every test pass). Verified:

- ✅ Every protected endpoint (account, API keys, export, FTO, support,
  billing, all admin routes) returns 401 to anonymous callers.
- ✅ Admin routes return 403 to signed-in **non-admin** users; the admin
  task runner only executes a fixed allow-list (arbitrary task names → 404).
- ✅ Security headers (HSTS, nosniff, frame-deny, referrer/permissions
  policy) on every API response; equivalents configured on the Next.js app.
- ✅ CORS: unknown origins get no `Access-Control-Allow-Origin`; only the
  configured frontend origin (+ Vercel previews) are allowed.
- ✅ Stripe webhooks refuse to process without a configured secret (503)
  and reject forged signatures (400). Prices are mapped server-side — the
  client can never choose an amount. Webhook handling is idempotent.
- ✅ Input validation: Validator payload bounds enforced (422); search
  queries sanitized against PostgREST filter injection; FTO patent numbers
  format-validated.
- ✅ Per-IP rate limiter trips under burst (429 + Retry-After) while
  /healthz stays exempt; monthly tier quotas are DB-backed.
- ✅ Locked content (build plans, master prompts, playbooks) is nulled
  server-side for unentitled users — it never reaches the client.
- ✅ API keys stored as SHA-256 hashes, plaintext shown once; FTO PDFs in a
  private bucket behind 1-hour signed URLs; RLS on every table; the
  service-role key exists only on the backend; secrets scan of project code
  is clean (env-driven everywhere).
- ✅ Internal corpora (active patents) unreachable by client roles, RPC
  execute revoked.

Operator actions:
- ☐ Keep Stripe in **test mode** until the full smoke checklist passes;
  then rotate to live keys.
- ☐ Enable Supabase **leaked-password protection** and set OTP/reset link
  expiry (Auth → Settings).
- ☐ Add error monitoring (Sentry free tier on both apps) and uptime
  monitoring (UptimeRobot on `/healthz` + homepage). The system logs to
  stdout — Render/Vercel capture it, but nobody pages you without a monitor.

## 2. Legal — in place (one caveat)

- ✅ Terms of Service — including AI-content accuracy limits, IP license,
  liability cap, **copyright/IP takedown procedure**, **governing law,
  informal-resolution-first, individual-claims clause**.
- ✅ Privacy Policy — data inventory, AI-provider processing disclosure,
  subprocessors, retention, GDPR/CCPA rights, essential-cookies-only.
- ✅ Billing & Refunds — cycles, cancellation, 14-day first-charge refund,
  FTO refund rules, dispute path (chargeback deflection).
- ✅ Acceptable Use + Disclaimer (not-legal-advice everywhere it matters:
  site, policies, FTO PDFs, validator).
- ✅ **Functioning** GDPR/CCPA erasure: self-serve account deletion
  (Account → Billing) that cancels the Stripe subscription and cascades all
  data; disclosed in the Privacy Policy.
- ✅ Signup consent line; policy links in footer; CAN-SPAM-style footer and
  transactional-only email.
- ✅ Public-domain gate enforced at the database (the core product-liability
  control), re-verified for paid FTO reports, with NOT VERIFIED as an
  honest failure mode.
- ☐ **Have a lawyer review the policy pages before launch.** They are
  thorough and product-specific, but they were not written by counsel, and
  "make sure I don't get sued" is a bar no software can guarantee — this
  review plus the disclaimers is how you actually minimize that risk.
  While there, have counsel confirm the governing-law jurisdiction wording
  matches where Zawadi Technologies LLC is registered.
- ☐ Set the real contact email + address in Admin → Site Footer (feeds the
  policies' contact lines).

## 3. Capacity — 1,000 users/hour: verified with wide margin

Measured (this repo, single uvicorn worker, full middleware stack):
**457 req/s sustained, 2,000/2,000 requests OK** ≈ 1.6M requests/hour.

Target math: 1,000 users/hour at a generous ~30 requests/session ≈ 8.3
req/s sustained — **~55× below measured app throughput**. Deployment
headroom on top of that:

- `render.yaml` now starts **2 uvicorn workers**; scale Render instances
  horizontally beyond that (tier quotas are DB-backed and multi-instance
  safe; the in-memory IP limiter becomes per-instance, which only loosens it).
- Vercel/Next static + ISR pages serve from CDN — homepage traffic barely
  touches the API.
- Supabase (PostgREST over HTTP, indexed queries) comfortably serves this
  scale on the starter tier; no connection-pool exhaustion by design.
- Redis caching (embeddings/framework/demand) keeps LLM spend flat as
  traffic grows — set `REDIS_URL` before launch.

Honest caveats: the measurement is app-layer on this build machine; a Render
starter instance has less CPU (even at one-fifth the throughput there is
>10× headroom), and DB-bound endpoints add per-request latency, not less
capacity. First real bottleneck you'll meet is **LLM cost**, not requests.

- ☐ After deploy, re-run a 1–2 minute burst against the Render URL
  (`hey`/`k6` or the script in this audit) and confirm p95 < 500ms on
  `/api/v1/blueprints`.

## 4. SEO / AEO / GEO — verified against a production build

Checked by booting `next start` and fetching raw HTML (what Googlebot sees):

- ✅ `/robots.txt` — public content open to all crawlers, AI crawlers
  (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, CCBot, …) explicitly
  allowed; account/admin/auth disallowed; sitemap declared.
- ✅ `/sitemap.xml` — valid XML, static pages + up to 500 blueprint pages
  refreshed hourly (URLs bake from `NEXT_PUBLIC_SITE_URL` at build).
- ✅ `/llms.txt` — AI-assistant site summary with key facts + citation
  guidance.
- ✅ Homepage raw HTML carries: canonical, meta description, OpenGraph,
  Twitter card, and `Organization` + `WebSite` (SearchAction) JSON-LD.
- ✅ Blueprint pages are server-rendered with unique metadata + `TechArticle`
  and `BreadcrumbList` JSON-LD — every blueprint is an indexable long-tail
  landing page. Failed lookups noindex themselves.
- ✅ Google's current fundamentals: crawlable server-rendered HTML,
  mobile-first responsive, HTTPS + HSTS, no doorway/duplicate pages,
  original (LLM-assisted but source-grounded) content, honest metadata, no
  cloaking, Core-Web-Vitals-friendly static-first pages.

On **300k users/year (~820/day)**: nobody can guarantee a traffic number,
and you should distrust anyone who does. What's in place is the machine
that can get there: every ingested patent becomes an indexed landing page,
so the catalog compounds. The levers that decide whether it happens:
- ☐ Run the historical backfill to thousands of blueprints (content volume
  is the single biggest driver).
- ☐ Submit the sitemap in Google Search Console + Bing Webmaster Tools;
  watch coverage weekly and fix anything excluded.
- ☐ Publish/share in the startup communities the product already scrapes
  (be helpful, not spammy) and launch on Product Hunt — SEO compounds
  faster with an initial traffic seed.

## 5. Revenue path — armed

- ✅ Free → Builder $19 → Pro $49 → Enterprise $150 subscriptions, $99 FTO
  reports; all server-side gated; checkout/portal/webhooks tested by suite.
- ✅ Support chat → admin Messages (retention), reply-by-email loop.
- ✅ Admin panel: tier grants, blueprint curation, footer/contact editing,
  worker ops, business overview.
- ☐ Flip Stripe to live mode, re-create the 4 prices, update the 4 price
  env vars + webhook secret, and run one real $19 checkout + refund.

## 6. Go-live sequence (one page)

1. Supabase: run migrations 1→7 + seed; enable Google OAuth; set auth URLs.
2. Resend: verify domain (DKIM/SPF/DMARC), Supabase SMTP, paste the 5
   templates (`emails/README.md`); mail-tester 9+/10.
3. Render: deploy blueprint; set all env vars (incl. `REDIS_URL`,
   email vars, at least one patent-source credential); `/healthz` green.
4. Vercel: root dir `frontend`, env vars incl. production
   `NEXT_PUBLIC_SITE_URL`; deploy.
5. Stripe: 4 prices + webhook; test-mode checkout for each plan + FTO.
6. Sign up → grant admin (SQL) → Admin → Site Footer (real contact/address).
7. Workers: `check_sources` → `backfill_embeddings` → `ingest` →
   `ingest_community` → `ingest_active` → `backfill_enrichment` → start
   `backfill_history` in chunks.
8. Walk the full smoke checklist in DEPLOYMENT.md.
9. Search Console + Bing: submit sitemap. Sentry + UptimeRobot on.
10. Counsel reviews policies → flip Stripe live → announce.
