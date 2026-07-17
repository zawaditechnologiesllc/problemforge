"""Patent source adapters.

Each source implements the same shape — fetch_expired_candidates() returning
normalized dicts — so adding BigQuery/Lens/EPO later is additive, not a rewrite.
MVP ships the USPTO adapter via the PatentsView search API.
"""

import json
from datetime import date, timedelta

import httpx

from ..config import settings

PATENTSVIEW_URL = "https://search.patentsview.org/api/v1/patent/"


def _twenty_years_ago(days_window: int) -> tuple[date, date]:
    """Window of filing dates that just crossed the 20-year statutory term."""
    today = date.today()
    try:
        hi = today.replace(year=today.year - 20)
    except ValueError:  # Feb 29
        hi = today.replace(year=today.year - 20, day=28)
    lo = hi - timedelta(days=days_window)
    return lo, hi


async def fetch_expired_candidates(
    days_window: int = 7,
    limit: int = 100,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[dict]:
    """Patents whose earliest filing date fell 20 years ago this week.

    These have aged out of the statutory patent term and are public domain.
    Requires a free PatentsView API key (USPTO_API_KEY). `transport` lets
    tests inject an httpx.MockTransport.
    """
    if not settings.uspto_api_key:
        raise RuntimeError("USPTO_API_KEY is not configured")

    lo, hi = _twenty_years_ago(days_window)
    query = {
        "_and": [
            {"_gte": {"patent_earliest_application_date": lo.isoformat()}},
            {"_lte": {"patent_earliest_application_date": hi.isoformat()}},
        ]
    }
    async with httpx.AsyncClient(timeout=60, transport=transport) as client:
        resp = await client.get(
            PATENTSVIEW_URL,
            headers={"X-Api-Key": settings.uspto_api_key},
            params={
                "q": json.dumps(query),
                "f": json.dumps(
                    [
                        "patent_id",
                        "patent_title",
                        "patent_abstract",
                        "patent_date",
                        "patent_earliest_application_date",
                    ]
                ),
                "o": json.dumps({"size": limit}),
            },
        )
        resp.raise_for_status()
        payload = resp.json()

    results = []
    for p in payload.get("patents") or []:
        results.append(
            {
                "source": "uspto",
                "patent_number": f"US{p['patent_id']}",
                "title": p.get("patent_title") or "Untitled patent",
                "abstract": p.get("patent_abstract"),
                "filing_date": p.get("patent_earliest_application_date"),
                "legal_status": "Expired - statutory term (filed more than 20 years ago)",
            }
        )
    return results


def is_public_domain(patent: dict) -> bool:
    """App-level mirror of the database gate — belt and suspenders."""
    filing = patent.get("filing_date")
    status = (patent.get("legal_status") or "").lower()
    if "expired" in status:
        return True
    if filing:
        try:
            filed = date.fromisoformat(str(filing))
            lo, hi = _twenty_years_ago(0)
            return filed <= hi
        except ValueError:
            return False
    return False
