"""Google Patents Public Data source via the BigQuery REST API.

Auth: a GCP service account with the "BigQuery Job User" role. Put the full
service-account JSON (one line) in GOOGLE_SERVICE_ACCOUNT_JSON. No Google SDK
needed — we exchange a signed RS256 JWT for an access token and call the
jobs.query REST endpoint directly. Queries the public
`patents-public-data.patents.publications` dataset (querying is billed to
your project; the dataset itself is free).
"""

import json
import time

import httpx
import jwt

from ...config import settings
from .base import PatentSource, twenty_years_ago

TOKEN_URL = "https://oauth2.googleapis.com/token"
BIGQUERY_SCOPE = "https://www.googleapis.com/auth/bigquery"

QUERY_SQL = """
SELECT
  publication_number,
  (SELECT text FROM UNNEST(title_localized) WHERE language = 'en' LIMIT 1) AS title,
  (SELECT text FROM UNNEST(abstract_localized) WHERE language = 'en' LIMIT 1) AS abstract,
  filing_date
FROM `patents-public-data.patents.publications`
WHERE country_code = 'US'
  AND filing_date BETWEEN @lo AND @hi
  AND filing_date > 0
ORDER BY publication_number
LIMIT @lim
""".strip()


class BigQuerySource(PatentSource):
    name = "bigquery"

    def __init__(self) -> None:
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def is_configured(self) -> bool:
        return bool(settings.google_service_account_json)

    def _credentials(self) -> dict:
        try:
            return json.loads(settings.google_service_account_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON") from exc

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        creds = self._credentials()
        now = int(time.time())
        assertion = jwt.encode(
            {
                "iss": creds["client_email"],
                "scope": BIGQUERY_SCOPE,
                "aud": TOKEN_URL,
                "iat": now,
                "exp": now + 3600,
            },
            creds["private_key"],
            algorithm="RS256",
        )
        resp = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        self._token = payload["access_token"]
        self._token_expires_at = time.time() + int(payload.get("expires_in", 3600))
        return self._token

    async def fetch_expired_candidates(
        self,
        days_window: int = 7,
        limit: int = 100,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> list[dict]:
        if not self.is_configured():
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is not configured")

        creds = self._credentials()
        project = creds.get("project_id")
        if not project:
            raise RuntimeError("service account JSON is missing project_id")

        lo, hi = twenty_years_ago(days_window)
        body = {
            "query": QUERY_SQL,
            "useLegacySql": False,
            "parameterMode": "NAMED",
            "queryParameters": [
                _int_param("lo", int(lo.strftime("%Y%m%d"))),
                _int_param("hi", int(hi.strftime("%Y%m%d"))),
                _int_param("lim", limit),
            ],
            "timeoutMs": 60000,
            "maxResults": limit,
        }
        async with httpx.AsyncClient(timeout=90, transport=transport) as client:
            token = await self._access_token(client)
            resp = await client.post(
                f"https://bigquery.googleapis.com/bigquery/v2/projects/{project}/queries",
                headers={"Authorization": f"Bearer {token}"},
                json=body,
            )
            resp.raise_for_status()
            payload = resp.json()

        results = []
        for row in payload.get("rows") or []:
            cells = [cell.get("v") for cell in row.get("f", [])]
            if len(cells) < 4 or not cells[0]:
                continue
            publication_number = str(cells[0]).replace("-", "")
            filing_raw = str(cells[3] or "")
            filing_date = (
                f"{filing_raw[0:4]}-{filing_raw[4:6]}-{filing_raw[6:8]}"
                if len(filing_raw) == 8
                else None
            )
            results.append(
                {
                    "source": self.name,
                    "patent_number": publication_number,
                    "title": cells[1] or "Untitled patent",
                    "abstract": cells[2],
                    "filing_date": filing_date,
                    "legal_status": "Expired - statutory term (filed more than 20 years ago)",
                }
            )
        return results


def _int_param(name: str, value: int) -> dict:
    return {
        "name": name,
        "parameterType": {"type": "INT64"},
        "parameterValue": {"value": str(value)},
    }
