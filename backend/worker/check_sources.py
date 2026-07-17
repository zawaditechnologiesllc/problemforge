"""Diagnostics for the data-collection pipeline and billing configuration.

Checks connectivity and configuration for every external dependency —
all four patent sources (USPTO, BigQuery, Lens, EPO), the LLM, embeddings,
Supabase, and Stripe prices — without writing anything to the database.

Usage: python -m worker.check_sources
Exit code 0 = nothing failed (warnings are okay), 1 = at least one failure.
"""

import asyncio
import sys

import httpx

from app.config import settings
from app.services.patent_sources import all_sources

_CREDENTIALS_HINT = {
    "uspto": "set USPTO_API_KEY (free key: patentsview.org/apis/keyrequest)",
    "bigquery": "set GOOGLE_SERVICE_ACCOUNT_JSON (GCP service account with BigQuery Job User)",
    "lens": "set LENS_API_KEY (lens.org subscriptions page)",
    "epo": "set EPO_OPS_KEY and EPO_OPS_SECRET (developers.epo.org)",
}


async def check_source(source) -> tuple[str, str]:
    if not source.is_configured():
        return ("WARN", f"not configured — {_CREDENTIALS_HINT[source.name]}")
    try:
        rows = await source.fetch_expired_candidates(days_window=3, limit=3)
        return ("PASS", f"live query OK — {len(rows)} candidates in a 3-day window 20 years back")
    except httpx.HTTPStatusError as exc:
        return ("FAIL", f"rejected the request: HTTP {exc.response.status_code}")
    except Exception as exc:
        return ("FAIL", f"query failed: {exc}")


async def check_llm() -> tuple[str, str]:
    if not settings.llm_api_key:
        return ("WARN", "LLM_API_KEY not set — ingestion translation and FTO analysis degrade to fallbacks")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.translator_model,
                    "messages": [{"role": "user", "content": "Reply with the word: ok"}],
                    "max_tokens": 5,
                },
            )
        if response.status_code == 200:
            return ("PASS", f"chat completion OK via {settings.llm_base_url} ({settings.translator_model})")
        return ("FAIL", f"LLM endpoint returned HTTP {response.status_code}: {response.text[:200]}")
    except Exception as exc:
        return ("FAIL", f"cannot reach LLM endpoint: {exc}")


async def check_embeddings() -> tuple[str, str]:
    if not settings.embeddings_api_key:
        return ("WARN", "EMBEDDINGS_API_KEY not set — Validator uses trigram text fallback")
    try:
        from app.services.llm import embed

        vector = await embed("connectivity check")
        if vector and len(vector) == 1536:
            return ("PASS", f"embeddings OK ({settings.embedding_model}, {len(vector)} dims)")
        return ("FAIL", f"unexpected embedding shape: {None if vector is None else len(vector)} dims (schema expects 1536)")
    except Exception as exc:
        return ("FAIL", f"embeddings request failed: {exc}")


def check_supabase() -> tuple[str, str]:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return ("WARN", "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set — worker cannot write")
    try:
        from app.db import get_db

        count = (
            get_db().table("raw_patents").select("id", count="exact").limit(1).execute().count
        )
        return ("PASS", f"database reachable — {count} raw patents stored")
    except Exception as exc:
        return ("FAIL", f"database check failed: {exc}")


def check_stripe() -> tuple[str, str]:
    if not settings.stripe_secret_key:
        return ("WARN", "STRIPE_SECRET_KEY not set — billing disabled")
    try:
        import stripe

        stripe.api_key = settings.stripe_secret_key
        prices = {
            "builder": settings.stripe_price_builder,
            "pro": settings.stripe_price_pro,
            "enterprise": settings.stripe_price_enterprise,
            "fto": settings.stripe_price_fto,
        }
        missing = [name for name, price in prices.items() if not price]
        checked = 0
        for name, price in prices.items():
            if price:
                stripe.Price.retrieve(price)
                checked += 1
        note = f"key valid, {checked} price(s) verified"
        if missing:
            return ("WARN", f"{note}; missing price ids: {', '.join(missing)}")
        return ("PASS", note)
    except Exception as exc:
        return ("FAIL", f"Stripe check failed: {exc}")


async def main_async() -> int:
    checks: list[tuple[str, tuple[str, str]]] = []
    for source in all_sources():
        checks.append((f"Patent source: {source.name}", await check_source(source)))
    checks.append(("LLM translation", await check_llm()))
    checks.append(("Embeddings", await check_embeddings()))
    checks.append(("Supabase", check_supabase()))
    checks.append(("Stripe", check_stripe()))

    print("\nProblemForge data-source & billing diagnostics")
    print("-" * 64)
    failed = False
    for name, (status, message) in checks:
        print(f"[{status:>4}] {name}: {message}")
        if status == "FAIL":
            failed = True
    print("-" * 64)
    print("Ingestion uses every configured source; at least one is required.")
    return 1 if failed else 0


def main() -> None:
    sys.exit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
