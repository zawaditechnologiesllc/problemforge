"""EPO Open Patent Services (OPS) source — European + DOCDB worldwide coverage.

Register an app at https://developers.epo.org -> consumer key/secret ->
EPO_OPS_KEY / EPO_OPS_SECRET. OAuth2 client-credentials flow.

OPS is searched by publication date (publication lags filing by ~18 months),
then every hit is filtered by its actual application date against the
requested filing range — the base class applies the 20-year public-domain
gate on top of that.
"""

import base64
import time
from datetime import date, timedelta

import httpx

from ...config import settings
from .base import PatentSource

TOKEN_URL = "https://ops.epo.org/3.2/auth/accesstoken"
SEARCH_URL = "https://ops.epo.org/3.2/rest-services/published-data/search/biblio"
PUBLICATION_LAG = timedelta(days=548)  # ~18 months from filing to publication


def _as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _text(value) -> str | None:
    """OPS JSON wraps leaf text as {"$": "..."}."""
    if isinstance(value, dict):
        return value.get("$")
    return value if isinstance(value, str) else None


class EPOSource(PatentSource):
    name = "epo"

    def __init__(self) -> None:
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def is_configured(self) -> bool:
        return bool(settings.epo_ops_key and settings.epo_ops_secret)

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        basic = base64.b64encode(
            f"{settings.epo_ops_key}:{settings.epo_ops_secret}".encode()
        ).decode()
        resp = await client.post(
            TOKEN_URL,
            headers={"Authorization": f"Basic {basic}"},
            data={"grant_type": "client_credentials"},
        )
        resp.raise_for_status()
        payload = resp.json()
        self._token = payload["access_token"]
        self._token_expires_at = time.time() + int(payload.get("expires_in", 1200))
        return self._token

    async def fetch_by_filing_range(
        self,
        lo: date,
        hi: date,
        limit: int = 100,
        jurisdiction: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> list[dict]:
        if not self.is_configured():
            raise RuntimeError("EPO_OPS_KEY / EPO_OPS_SECRET are not configured")

        pub_lo = lo + PUBLICATION_LAG
        pub_hi = hi + PUBLICATION_LAG
        cql = (
            f'pd within "{pub_lo.strftime("%Y%m%d")} {pub_hi.strftime("%Y%m%d")}"'
            f" and pn={jurisdiction or 'EP'}"
        )
        async with httpx.AsyncClient(timeout=60, transport=transport) as client:
            token = await self._access_token(client)
            resp = await client.get(
                SEARCH_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
                params={"q": cql, "Range": f"1-{min(limit, 100)}"},
            )
            resp.raise_for_status()
            payload = resp.json()

        documents = _as_list(
            (
                ((payload.get("ops:world-patent-data") or {}).get("ops:biblio-search") or {})
                .get("ops:search-result", {})
                .get("exchange-documents")
            )
        )
        results = []
        for wrapper in documents:
            doc = (wrapper or {}).get("exchange-document") or wrapper or {}
            if not isinstance(doc, dict):
                continue
            country = doc.get("@country") or jurisdiction or "EP"
            number = doc.get("@doc-number")
            kind = doc.get("@kind") or ""
            if not number:
                continue
            biblio = doc.get("bibliographic-data") or {}

            filing_date = None
            app_ref = biblio.get("application-reference") or {}
            for doc_id in _as_list(app_ref.get("document-id")):
                raw = _text((doc_id or {}).get("date"))
                if raw and len(raw) == 8:
                    filing_date = f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"
                    break

            # Publication-date search is approximate; keep only documents whose
            # actual application date sits inside the requested filing range.
            if not filing_date:
                continue
            try:
                filed = date.fromisoformat(filing_date)
            except ValueError:
                continue
            if not (lo <= filed <= hi):
                continue

            title = None
            for entry in _as_list(biblio.get("invention-title")):
                if isinstance(entry, dict) and entry.get("@lang") in (None, "en"):
                    title = _text(entry)
                    if title:
                        break
            abstract = None
            for entry in _as_list(doc.get("abstract")):
                if isinstance(entry, dict):
                    paragraphs = [_text(p) for p in _as_list(entry.get("p"))]
                    abstract = " ".join(p for p in paragraphs if p) or None
                    if abstract:
                        break

            results.append(
                {
                    "source": self.name,
                    "patent_number": f"{country}{number}{kind}",
                    "title": title or "Untitled patent",
                    "abstract": abstract,
                    "filing_date": filing_date,
                }
            )
        return results
