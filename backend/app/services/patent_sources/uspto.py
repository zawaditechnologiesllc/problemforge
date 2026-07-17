"""USPTO source via the PatentsView search API (primary MVP source).

Free API key: https://patentsview.org/apis/keyrequest -> USPTO_API_KEY.
"""

import json
import re

import httpx

from ...config import settings
from .base import PatentSource, twenty_years_ago

PATENTSVIEW_URL = "https://search.patentsview.org/api/v1/patent/"

_FIELDS = [
    "patent_id",
    "patent_title",
    "patent_abstract",
    "patent_date",
    "patent_earliest_application_date",
]


class USPTOSource(PatentSource):
    name = "uspto"

    def is_configured(self) -> bool:
        return bool(settings.uspto_api_key)

    async def fetch_expired_candidates(
        self,
        days_window: int = 7,
        limit: int = 100,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> list[dict]:
        if not self.is_configured():
            raise RuntimeError("USPTO_API_KEY is not configured")

        lo, hi = twenty_years_ago(days_window)
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
                    "f": json.dumps(_FIELDS),
                    "o": json.dumps({"size": limit}),
                },
            )
            resp.raise_for_status()
            payload = resp.json()

        results = []
        for p in payload.get("patents") or []:
            results.append(
                {
                    "source": self.name,
                    "patent_number": f"US{p['patent_id']}",
                    "title": p.get("patent_title") or "Untitled patent",
                    "abstract": p.get("patent_abstract"),
                    "filing_date": p.get("patent_earliest_application_date"),
                    "legal_status": "Expired - statutory term (filed more than 20 years ago)",
                }
            )
        return results

    async def fetch_by_number(
        self,
        patent_number: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> dict | None:
        """Live lookup of a single US patent, used by FTO re-verification."""
        if not self.is_configured():
            return None
        match = re.match(r"^US(\d+)", patent_number.upper())
        if not match:
            return None
        async with httpx.AsyncClient(timeout=30, transport=transport) as client:
            resp = await client.get(
                PATENTSVIEW_URL,
                headers={"X-Api-Key": settings.uspto_api_key},
                params={
                    "q": json.dumps({"patent_id": match.group(1)}),
                    "f": json.dumps(_FIELDS),
                },
            )
            resp.raise_for_status()
            patents = resp.json().get("patents") or []
        if not patents:
            return None
        p = patents[0]
        return {
            "source": self.name,
            "patent_number": f"US{p['patent_id']}",
            "title": p.get("patent_title"),
            "abstract": p.get("patent_abstract"),
            "filing_date": p.get("patent_earliest_application_date"),
            "grant_date": p.get("patent_date"),
        }
