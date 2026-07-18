"""Common interface + public-domain helpers shared by all patent sources.

Providers implement `fetch_by_filing_range` (raw filing-date-range search).
The base class turns that into `fetch_expired_candidates` by applying the
20-year statutory window and the public-domain gate — so the gate logic lives
in exactly one place and can never be short-circuited by a status string a
provider assigns itself.
"""

import re
from abc import ABC, abstractmethod
from datetime import date, timedelta

import httpx

STATUTORY_EXPIRED_STATUS = "Expired - statutory term (filed more than 20 years ago)"


def twenty_years_ago(days_window: int) -> tuple[date, date]:
    """Window of filing dates that just crossed the 20-year statutory term."""
    today = date.today()
    try:
        hi = today.replace(year=today.year - 20)
    except ValueError:  # Feb 29
        hi = today.replace(year=today.year - 20, day=28)
    lo = hi - timedelta(days=days_window)
    return lo, hi


def is_public_domain(patent: dict) -> bool:
    """App-level mirror of the database trigger gate — belt and suspenders."""
    status = (patent.get("legal_status") or "").lower()
    if "expired" in status:
        return True
    filing = patent.get("filing_date")
    if filing:
        try:
            filed = date.fromisoformat(str(filing))
            _, hi = twenty_years_ago(0)
            return filed <= hi
        except ValueError:
            return False
    return False


def normalize_patent_number(raw: str) -> str:
    """US 7,156,808 B2 / US-7156808-B2 / us7156808b2 -> US7156808B2."""
    return re.sub(r"[\s,./-]", "", (raw or "")).upper()


class PatentSource(ABC):
    """A patent data source. Implementations must be side-effect free readers."""

    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        """True when the credentials this source needs are present."""

    @abstractmethod
    async def fetch_by_filing_range(
        self,
        lo: date,
        hi: date,
        limit: int = 100,
        jurisdiction: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> list[dict]:
        """Raw filing-date-range search. No expiry semantics — just the range.

        Used directly by the historical backfill and the internal active-
        landscape corpus; `transport` lets tests inject an httpx.MockTransport.
        """

    async def fetch_expired_candidates(
        self,
        days_window: int = 7,
        limit: int = 100,
        jurisdiction: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> list[dict]:
        """Normalized candidates that have verifiably aged into the public domain."""
        lo, hi = twenty_years_ago(days_window)
        rows = await self.fetch_by_filing_range(
            lo, hi, limit=limit, jurisdiction=jurisdiction, transport=transport
        )
        results = []
        for row in rows:
            # Gate on provider-supplied facts only (filing date or a status the
            # SOURCE reported) — never on a status we stamp ourselves.
            if not is_public_domain(
                {
                    "filing_date": row.get("filing_date"),
                    "legal_status": row.get("legal_status"),
                }
            ):
                continue
            if not row.get("legal_status"):
                row["legal_status"] = STATUTORY_EXPIRED_STATUS
            results.append(row)
        return results
