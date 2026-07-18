"""Internal active-patent landscape corpus.

Ingests RECENT (active-era) patent filings into a separate, internal-only
table used exclusively to power an aggregate caution signal in the Validator.

Boundaries (deliberate and enforced):
- Stored in `active_patents`, which has RLS enabled with NO read policies and
  is never joined to blueprints — active patents can never surface as
  blueprints (the public-domain trigger on raw_patents is untouched).
- No API endpoint returns rows from this table. The Validator only receives
  an aggregate similarity level (none/elevated/high) and shows users a
  generic caution note — never patent numbers, titles, or any identifying
  detail.
"""

from datetime import date, timedelta, timezone, datetime

from ..config import settings
from ..db import get_db
from . import llm
from .patent_sources import enabled_sources

ACTIVE_STATUS = "Active-era filing (internal landscape corpus — never published)"


async def run_active_ingestion(
    years_back: int | None = None, limit_per_region: int = 40
) -> dict:
    """Fetch recent filings across all configured regions into the corpus."""
    db = get_db()
    years = years_back or settings.active_window_years
    hi = date.today()
    lo = hi - timedelta(days=365 * years)
    stats = {"fetched": 0, "inserted": 0, "failed": 0}

    for source in enabled_sources():
        try:
            rows = await source.fetch_by_filing_range(lo, hi, limit=limit_per_region)
        except Exception:
            stats["failed"] += 1
            continue
        stats["fetched"] += len(rows)
        for row in rows:
            try:
                exists = (
                    db.table("active_patents")
                    .select("id")
                    .eq("patent_number", row["patent_number"])
                    .limit(1)
                    .execute()
                    .data
                )
                if exists:
                    continue
                text = f"{row['title']}. {row.get('abstract') or ''}"[:4000]
                embedding = await llm.embed(text)
                db.table("active_patents").insert(
                    {
                        "source": row["source"],
                        "jurisdiction": row.get("jurisdiction"),
                        "patent_number": row["patent_number"],
                        "title": row["title"],
                        "abstract": row.get("abstract"),
                        "filing_date": row.get("filing_date"),
                        "embedding": embedding,
                    }
                ).execute()
                stats["inserted"] += 1
            except Exception:
                stats["failed"] += 1

    db.table("ingestion_runs").insert(
        {
            "source": "active-landscape",
            "fetched": stats["fetched"],
            "inserted": stats["inserted"],
            "failed": stats["failed"],
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()
    return stats


def landscape_signal(db, embedding: list[float]) -> dict | None:
    """Aggregate-only similarity signal against the active corpus.

    Returns a level and a generic note — never identifying details.
    """
    try:
        result = db.rpc(
            "match_active_patents",
            {"query_embedding": embedding, "match_count": 3},
        ).execute()
        top = max((row.get("similarity") or 0 for row in result.data or []), default=0)
    except Exception:
        return None

    if top >= 0.60:
        level = "high"
    elif top >= 0.45:
        level = "elevated"
    else:
        level = "none"

    signal: dict = {"level": level}
    if level != "none":
        signal["note"] = (
            "Our internal patent-landscape check found recent, active-era "
            "filings with concepts similar to your idea. The expired "
            "blueprints shown here remain public domain and free to build on "
            "— but if you plan to patent or heavily commercialize a novel "
            "variation, consider a professional prior-art search first."
        )
    return signal
