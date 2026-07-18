"""20 regional patent sources covering the markets where ProblemForge is
needed most.

Only a handful of patent offices expose practical public APIs, but the four
provider adapters (USPTO/PatentsView, Google Patents BigQuery, Lens.org,
EPO OPS/DOCDB) collectively index 100+ jurisdictions. Each region below is a
first-class source that routes to the best configured provider for that
jurisdiction, with automatic fallback — so credentials for ANY global
provider (Lens, BigQuery, or EPO) light up every region at once.
"""

from dataclasses import dataclass
from datetime import date

import httpx

from .base import PatentSource
from .bigquery import BigQuerySource
from .epo import EPOSource
from .lens import LensSource
from .uspto import USPTOSource


@dataclass(frozen=True)
class Region:
    code: str          # jurisdiction code used by the providers
    display_name: str
    providers: tuple[str, ...]  # provider preference order


# The 20 regions: the majors (US, Europe, East Asia) plus the emerging
# startup markets — India, Southeast Asia, Latin America, Africa — where
# building from public-domain engineering has the most leverage.
REGIONS: tuple[Region, ...] = (
    Region("US", "United States", ("uspto", "lens", "bigquery")),
    Region("EP", "Europe (EPO-wide)", ("epo", "lens", "bigquery")),
    Region("GB", "United Kingdom", ("lens", "bigquery", "epo")),
    Region("DE", "Germany", ("lens", "bigquery", "epo")),
    Region("FR", "France", ("lens", "bigquery", "epo")),
    Region("NL", "Netherlands", ("lens", "bigquery", "epo")),
    Region("SE", "Sweden", ("lens", "bigquery", "epo")),
    Region("JP", "Japan", ("lens", "bigquery", "epo")),
    Region("KR", "South Korea", ("lens", "bigquery", "epo")),
    Region("CN", "China", ("lens", "bigquery", "epo")),
    Region("TW", "Taiwan", ("lens", "bigquery", "epo")),
    Region("CA", "Canada", ("lens", "bigquery", "epo")),
    Region("AU", "Australia", ("lens", "bigquery", "epo")),
    Region("NZ", "New Zealand", ("lens", "bigquery", "epo")),
    Region("IN", "India", ("lens", "bigquery", "epo")),
    Region("SG", "Singapore", ("lens", "bigquery", "epo")),
    Region("IL", "Israel", ("lens", "bigquery", "epo")),
    Region("BR", "Brazil", ("lens", "bigquery", "epo")),
    Region("MX", "Mexico", ("lens", "bigquery", "epo")),
    Region("ZA", "South Africa", ("lens", "bigquery", "epo")),
)


class RegionalSource(PatentSource):
    """A jurisdiction-scoped source backed by the best configured provider."""

    def __init__(self, region: Region, providers: dict[str, PatentSource]):
        self.region = region
        self.name = region.code.lower()
        self._providers = providers

    @property
    def display_name(self) -> str:
        return self.region.display_name

    def provider(self) -> PatentSource | None:
        for provider_name in self.region.providers:
            provider = self._providers.get(provider_name)
            if provider and provider.is_configured():
                return provider
        return None

    def is_configured(self) -> bool:
        return self.provider() is not None

    async def fetch_by_filing_range(
        self,
        lo: date,
        hi: date,
        limit: int = 100,
        jurisdiction: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> list[dict]:
        provider = self.provider()
        if provider is None:
            raise RuntimeError(
                f"No provider configured for region {self.region.code} — "
                "set LENS_API_KEY, GOOGLE_SERVICE_ACCOUNT_JSON, or EPO OPS credentials"
            )
        rows = await provider.fetch_by_filing_range(
            lo,
            hi,
            limit=limit,
            jurisdiction=jurisdiction or self.region.code,
            transport=transport,
        )
        for row in rows:
            row["jurisdiction"] = self.region.code
        return rows


def build_regional_sources() -> list[RegionalSource]:
    providers: dict[str, PatentSource] = {
        "uspto": USPTOSource(),
        "bigquery": BigQuerySource(),
        "lens": LensSource(),
        "epo": EPOSource(),
    }
    return [RegionalSource(region, providers) for region in REGIONS]
