"""Diagnostics for the data-collection pipeline.

Checks connectivity and configuration for every external data source the
ingestion worker depends on, without writing anything to the database.

Usage: python -m worker.check_sources
Exit code 0 = nothing failed (warnings are okay), 1 = at least one failure.
"""

import asyncio
import sys

import httpx

from app.config import settings
from app.services import patents


async def check_uspto() -> tuple[str, str]:
    if settings.uspto_api_key:
        try:
            rows = await patents.fetch_expired_candidates(days_window=3, limit=5)
            return (
                "PASS",
                f"PatentsView query OK — {len(rows)} candidate patents in a 3-day window 20 years back",
            )
        except httpx.HTTPStatusError as exc:
            return ("FAIL", f"PatentsView rejected the request: HTTP {exc.response.status_code}")
        except Exception as exc:
            return ("FAIL", f"PatentsView query failed: {exc}")
    # No key configured: still verify the endpoint is reachable.
    try:
        response = httpx.get(patents.PATENTSVIEW_URL, timeout=15)
        if response.status_code in (401, 403):
            return (
                "WARN",
                f"endpoint reachable (HTTP {response.status_code}) but USPTO_API_KEY is not set — "
                "request a free key at patentsview.org/apis/keyrequest",
            )
        return ("WARN", f"endpoint responded HTTP {response.status_code}; set USPTO_API_KEY for a real check")
    except Exception as exc:
        return ("FAIL", f"cannot reach PatentsView: {exc}")


async def check_llm() -> tuple[str, str]:
    if not settings.llm_api_key:
        return ("WARN", "LLM_API_KEY not set — ingestion translation will not run")
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


async def main_async() -> int:
    checks = [
        ("USPTO / PatentsView", await check_uspto()),
        ("LLM translation", await check_llm()),
        ("Embeddings", await check_embeddings()),
        ("Supabase", check_supabase()),
    ]
    print("\nProblemForge data-source diagnostics")
    print("-" * 60)
    failed = False
    for name, (status, message) in checks:
        print(f"[{status:>4}] {name}: {message}")
        if status == "FAIL":
            failed = True
    print("-" * 60)
    print("Note: BigQuery / Lens.org / EPO OPS adapters are post-MVP (not implemented).")
    return 1 if failed else 0


def main() -> None:
    sys.exit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
