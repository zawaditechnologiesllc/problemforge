"""Patent source adapters.

Two layers:

1. **Providers** — the four adapters that actually speak to external APIs
   (USPTO/PatentsView, Google Patents BigQuery, Lens.org, EPO OPS). Each
   implements `fetch_by_filing_range` and inherits the public-domain-gated
   `fetch_expired_candidates` from the base class.
2. **Regional sources** — 20 jurisdiction-scoped sources (see regions.py)
   that route to the best configured provider for that region, with
   automatic fallback. Ingestion iterates these.

Normalized candidate shape returned everywhere:

    {
      "source": "uspto" | "bigquery" | "lens" | "epo",
      "jurisdiction": "US" | "EP" | "JP" | ...,   (regional sources only)
      "patent_number": "US7156808B2",
      "title": str,
      "abstract": str | None,
      "filing_date": "YYYY-MM-DD" | None,
      "legal_status": str,                        (expired candidates only)
    }

Every expired candidate still passes the app-level public-domain check AND
the database trigger gate before being stored.
"""

from .base import (
    PatentSource,
    is_public_domain,
    normalize_patent_number,
    twenty_years_ago,
)
from .bigquery import BigQuerySource
from .epo import EPOSource
from .lens import LensSource
from .regions import REGIONS, RegionalSource, build_regional_sources
from .uspto import USPTOSource

__all__ = [
    "PatentSource",
    "USPTOSource",
    "BigQuerySource",
    "LensSource",
    "EPOSource",
    "RegionalSource",
    "REGIONS",
    "all_sources",
    "enabled_sources",
    "provider_sources",
    "is_public_domain",
    "normalize_patent_number",
    "twenty_years_ago",
]


def provider_sources() -> list[PatentSource]:
    """The four provider adapters (for diagnostics/credential checks)."""
    return [USPTOSource(), BigQuerySource(), LensSource(), EPOSource()]


def all_sources() -> list[RegionalSource]:
    """All 20 regional sources, configured or not."""
    return build_regional_sources()


def enabled_sources() -> list[RegionalSource]:
    """Regional sources whose backing provider has credentials."""
    return [source for source in all_sources() if source.is_configured()]
