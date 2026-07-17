"""Patent source adapters.

Every source implements the same PatentSource interface and returns the same
normalized candidate shape, so the ingestion pipeline is source-agnostic:

    {
      "source": "uspto" | "bigquery" | "lens" | "epo",
      "patent_number": "US7156808B2",
      "title": str,
      "abstract": str | None,
      "filing_date": "YYYY-MM-DD" | None,
      "legal_status": str,
    }

A source activates automatically when its credentials are present in the
environment (see .env.example). Every candidate still passes the app-level
public-domain check AND the database trigger gate before being stored.
"""

from .base import PatentSource, is_public_domain, twenty_years_ago
from .bigquery import BigQuerySource
from .epo import EPOSource
from .lens import LensSource
from .uspto import USPTOSource

__all__ = [
    "PatentSource",
    "USPTOSource",
    "BigQuerySource",
    "LensSource",
    "EPOSource",
    "all_sources",
    "enabled_sources",
    "is_public_domain",
    "twenty_years_ago",
]


def all_sources() -> list[PatentSource]:
    return [USPTOSource(), BigQuerySource(), LensSource(), EPOSource()]


def enabled_sources() -> list[PatentSource]:
    return [source for source in all_sources() if source.is_configured()]
