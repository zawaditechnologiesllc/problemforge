"""Bulk-generate Modern AI Playbooks + 5-point validations for blueprints
that don't have them yet (e.g. the seed catalog, or after a big backfill).

Each blueprint costs roughly two LLM calls (playbook + validation), done once
and stored forever. Requires LLM_API_KEY.

Usage: python -m worker.backfill_enrichment [--limit 50]
"""

import argparse
import asyncio

from app.db import get_db
from app.services.playbook import generate_enrichment


async def main_async(limit: int) -> None:
    db = get_db()
    rows = (
        db.table("blueprints")
        .select("id, title")
        .is_("playbook", "null")
        .eq("is_public", True)
        .limit(limit)
        .execute()
        .data
    )
    print(f"Enriching {len(rows)} blueprint(s)...")
    done = 0
    for row in rows:
        ok = await generate_enrichment(row["id"])
        done += 1 if ok else 0
        print(f"  [{'ok' if ok else 'skip'}] {row['title']}")
    print(f"Enriched {done}/{len(rows)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=50)
    asyncio.run(main_async(parser.parse_args().limit))


if __name__ == "__main__":
    main()
