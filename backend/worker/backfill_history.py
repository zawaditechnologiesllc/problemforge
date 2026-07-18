"""Historical backfill: walk the full public-domain filing range — timeless.

Coverage runs from INGEST_BACKFILL_START (default 1790-01-01, the start of
US patent records) up to today minus 20 years. Old does not mean obsolete: a
mechanism patented in the 1960s can still be the right solution today, and
everything in this range is public domain by definition. Pre-1980 filings are
walked in year-sized windows (records are sparse), recent decades in
month-sized windows. Idempotent: patents already ingested are skipped, so
the job is resumable — rerun it and it continues where the data left off.

Usage:
  python -m worker.backfill_history                       # full range, all regions
  python -m worker.backfill_history --start 1965-01 --end 1975-12
  python -m worker.backfill_history --regions us,ep,jp --per-window 25
"""

import argparse
import asyncio
from datetime import date, timedelta

from app.config import settings
from app.services import llm
from app.services.ingestion import run_ingestion  # noqa: F401 (weekly variant)
from app.services.patent_sources import enabled_sources, is_public_domain
from app.db import get_db


def _windows(start: date, end: date):
    """Year-sized windows before 1980 (sparse records), month-sized after."""
    cursor = start.replace(day=1)
    while cursor <= end:
        if cursor.year < 1980:
            nxt = date(cursor.year + 1, 1, 1)
        elif cursor.month == 12:
            nxt = cursor.replace(year=cursor.year + 1, month=1)
        else:
            nxt = cursor.replace(month=cursor.month + 1)
        yield cursor, min(nxt - timedelta(days=1), end)
        cursor = nxt


async def _process_window(source, lo: date, hi: date, per_window: int, db) -> dict:
    stats = {"fetched": 0, "inserted": 0, "translated": 0, "failed": 0}
    candidates = await source.fetch_by_filing_range(lo, hi, limit=per_window)
    stats["fetched"] = len(candidates)
    for candidate in candidates:
        try:
            if not is_public_domain(
                {"filing_date": candidate.get("filing_date"), "legal_status": candidate.get("legal_status")}
            ):
                continue
            candidate.setdefault(
                "legal_status",
                "Expired - statutory term (filed more than 20 years ago)",
            )
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
        except Exception:
            stats["failed"] += 1
    return stats


async def main_async(args) -> None:
    db = get_db()
    start = date.fromisoformat(
        (args.start or settings.ingest_backfill_start[:7]) + "-01"
        if len(args.start or settings.ingest_backfill_start) == 7
        else (args.start or settings.ingest_backfill_start)
    )
    default_end = date.today().replace(year=date.today().year - 20)
    end = (
        date.fromisoformat(args.end + "-28") if args.end else default_end
    )
    end = min(end, default_end)  # never cross into non-public-domain territory

    sources = enabled_sources()
    if args.regions:
        wanted = {code.strip().lower() for code in args.regions.split(",")}
        sources = [s for s in sources if s.name in wanted]
    if not sources:
        print("No configured sources match — set provider credentials first.")
        return

    print(f"Backfilling {start} -> {end} across {len(sources)} region(s)")
    for source in sources:
        totals = {"fetched": 0, "inserted": 0, "translated": 0, "failed": 0}
        for lo, hi in _windows(start, end):
            stats = await _process_window(source, lo, hi, args.per_window, db)
            for key in totals:
                totals[key] += stats[key]
        print(f"  [{source.region.code}] {totals}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", help="YYYY-MM or YYYY-MM-DD (default: INGEST_BACKFILL_START)")
    parser.add_argument("--end", help="YYYY-MM (default: today minus 20 years)")
    parser.add_argument("--regions", help="comma-separated region codes, e.g. us,ep,jp")
    parser.add_argument("--per-window", type=int, default=25, help="max patents per month-window per region")
    asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    main()
