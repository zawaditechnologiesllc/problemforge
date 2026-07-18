"""Lens.org patent source (broad global coverage — backs most regional sources).

API token: https://www.lens.org/lens/user/subscriptions -> LENS_API_KEY.
"""

from datetime import date

import httpx

from ...config import settings
from .base import PatentSource

LENS_SEARCH_URL = "https://api.lens.org/patent/search"


def _first_english(entries: list | None) -> str | None:
    for entry in entries or []:
        if isinstance(entry, dict) and entry.get("lang") in (None, "en"):
            text = entry.get("text")
            if text:
                return text
    if entries and isinstance(entries[0], dict):
        return entries[0].get("text")
    return None


class LensSource(PatentSource):
    name = "lens"

    def is_configured(self) -> bool:
        return bool(settings.lens_api_key)

    async def fetch_by_filing_range(
        self,
        lo: date,
        hi: date,
        limit: int = 100,
        jurisdiction: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> list[dict]:
        if not self.is_configured():
            raise RuntimeError("LENS_API_KEY is not configured")

        body = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"jurisdiction": jurisdiction or "US"}},
                        {
                            "range": {
                                "earliest_claim_date": {
                                    "gte": lo.isoformat(),
                                    "lte": hi.isoformat(),
                                }
                            }
                        },
                    ]
                }
            },
            "size": min(limit, 100),
            "include": [
                "lens_id",
                "jurisdiction",
                "doc_number",
                "kind",
                "earliest_claim_date",
                "biblio.invention_title",
                "abstract",
                "legal_status",
            ],
        }
        async with httpx.AsyncClient(timeout=60, transport=transport) as client:
            resp = await client.post(
                LENS_SEARCH_URL,
                headers={"Authorization": f"Bearer {settings.lens_api_key}"},
                json=body,
            )
            resp.raise_for_status()
            payload = resp.json()

        results = []
        for item in payload.get("data") or []:
            doc_number = item.get("doc_number")
            if not doc_number:
                continue
            item_jurisdiction = item.get("jurisdiction") or jurisdiction or "US"
            kind = item.get("kind") or ""
            record = {
                "source": self.name,
                "patent_number": f"{item_jurisdiction}{doc_number}{kind}",
                "title": _first_english(
                    (item.get("biblio") or {}).get("invention_title")
                )
                or "Untitled patent",
                "abstract": _first_english(item.get("abstract")),
                "filing_date": item.get("earliest_claim_date"),
            }
            # Pass through the SOURCE's own expiry status when it has one —
            # the base class gates on it; we never stamp expiry ourselves here.
            source_status = (item.get("legal_status") or {}).get("patent_status")
            if source_status and source_status.upper() in ("EXPIRED", "LAPSED", "CEASED"):
                record["legal_status"] = (
                    f"Expired - {source_status.lower()} (Lens.org legal status)"
                )
            results.append(record)
        return results
