"""Weekly ingestion pipeline: patent sources -> LLM translation -> blueprints.

Iterates every configured source (USPTO, BigQuery, Lens, EPO), dedupes on
patent_number, and is gated twice: here in code and by the
assert_public_domain trigger in Postgres.
"""

import asyncio
from datetime import datetime, timezone

from ..db import get_db
from . import llm
from .patent_sources import enabled_sources, is_public_domain


async def run_ingestion(days_window: int = 7, limit_per_source: int = 50) -> dict:
    db = get_db()
    totals = {"fetched": 0, "inserted": 0, "translated": 0, "failed": 0}
    sources = enabled_sources()
    if not sources:
        print("No patent sources configured — set USPTO_API_KEY (and/or "
              "GOOGLE_SERVICE_ACCOUNT_JSON, LENS_API_KEY, EPO_OPS_KEY/SECRET).")
        return totals

    for source in sources:
        run = (
            db.table("ingestion_runs").insert({"source": source.name}).execute().data[0]
        )
        stats = {"fetched": 0, "inserted": 0, "translated": 0, "failed": 0}
        notes: list[str] = []

        try:
            candidates = await source.fetch_expired_candidates(days_window, limit_per_source)
            stats["fetched"] = len(candidates)

            for candidate in candidates:
                try:
                    if not is_public_domain(candidate):
                        continue

                    existing = (
                        db.table("raw_patents")
                        .select("id")
                        .eq("patent_number", candidate["patent_number"])
                        .limit(1)
                        .execute()
                        .data
                    )
                    if existing:
                        continue

                    domain = await llm.classify_domain(
                        candidate["title"], candidate.get("abstract") or ""
                    )
                    raw = (
                        db.table("raw_patents")
                        .insert({**candidate, "domain": domain})
                        .execute()
                        .data[0]
                    )
                    stats["inserted"] += 1

                    blueprint = await llm.translate_patent(
                        candidate["title"], candidate.get("abstract") or "", domain
                    )
                    if not blueprint:
                        stats["failed"] += 1
                        notes.append(f"parse failed: {candidate['patent_number']}")
                        continue

                    embedding = await llm.embed(blueprint["human_problem"])
                    db.table("blueprints").insert(
                        {
                            "raw_patent_id": raw["id"],
                            "patent_number": candidate["patent_number"],
                            "title": candidate["title"],
                            "domain": domain,
                            **blueprint,
                            "buildability_score": 70,
                            "embedding": embedding,
                        }
                    ).execute()
                    stats["translated"] += 1
                except Exception as exc:  # keep the batch going
                    stats["failed"] += 1
                    notes.append(f"{candidate.get('patent_number')}: {exc}")
        except Exception as exc:
            notes.append(f"source aborted: {exc}")

        db.table("ingestion_runs").update(
            {
                **stats,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "notes": "\n".join(notes)[:5000] or None,
            }
        ).eq("id", run["id"]).execute()
        for key in totals:
            totals[key] += stats[key]

    return totals


async def backfill_embeddings(batch: int = 50) -> int:
    """Embed blueprints that don't have vectors yet (e.g. seed rows)."""
    db = get_db()
    rows = (
        db.table("blueprints")
        .select("id, human_problem")
        .is_("embedding", "null")
        .limit(batch)
        .execute()
        .data
    )
    done = 0
    for row in rows:
        vector = await llm.embed(row["human_problem"])
        if vector is None:
            raise RuntimeError("EMBEDDINGS_API_KEY is not configured")
        db.table("blueprints").update({"embedding": vector}).eq(
            "id", row["id"]
        ).execute()
        done += 1
        await asyncio.sleep(0.2)  # gentle on rate limits
    return done
