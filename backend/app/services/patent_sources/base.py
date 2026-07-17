"""Common interface + public-domain helpers shared by all patent sources."""

import re
from abc import ABC, abstractmethod
from datetime import date, timedelta

import httpx


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
    async def fetch_expired_candidates(
        self,
        days_window: int = 7,
        limit: int = 100,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> list[dict]:
        """Return normalized candidates that have aged into the public domain.

        `transport` lets tests inject an httpx.MockTransport.
        """
