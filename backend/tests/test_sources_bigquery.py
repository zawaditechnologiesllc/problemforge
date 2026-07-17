"""Tests for the Google Patents BigQuery adapter (service-account OAuth + query)."""

import asyncio
import json

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.config import settings
from app.services.patent_sources import BigQuerySource


def _fake_service_account() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return json.dumps(
        {
            "type": "service_account",
            "project_id": "test-project",
            "client_email": "ingest@test-project.iam.gserviceaccount.com",
            "private_key": pem,
        }
    )


def test_requires_credentials(monkeypatch):
    monkeypatch.setattr(settings, "google_service_account_json", "")
    with pytest.raises(RuntimeError, match="GOOGLE_SERVICE_ACCOUNT_JSON"):
        asyncio.run(BigQuerySource().fetch_expired_candidates())


def test_oauth_flow_and_query_normalization(monkeypatch):
    monkeypatch.setattr(
        settings, "google_service_account_json", _fake_service_account()
    )
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "oauth2.googleapis.com":
            body = dict(httpx.QueryParams(request.content.decode()))
            captured["grant_type"] = body.get("grant_type")
            captured["assertion"] = body.get("assertion")
            return httpx.Response(
                200, json={"access_token": "fake-token", "expires_in": 3600}
            )
        # BigQuery jobs.query
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "jobComplete": True,
                "rows": [
                    {
                        "f": [
                            {"v": "US-6934691-B1"},
                            {"v": "Group payment system"},
                            {"v": "Splits shared bills."},
                            {"v": "20020214"},
                        ]
                    },
                    {"f": [{"v": None}, {"v": None}, {"v": None}, {"v": None}]},
                ],
            },
        )

    rows = asyncio.run(
        BigQuerySource().fetch_expired_candidates(
            days_window=7, limit=10, transport=httpx.MockTransport(handler)
        )
    )

    # OAuth: signed JWT-bearer exchange, token used on the query call
    assert captured["grant_type"] == "urn:ietf:params:oauth:grant-type:jwt-bearer"
    assert captured["assertion"].count(".") == 2  # a signed JWT
    assert captured["auth"] == "Bearer fake-token"
    # Query: parameterized with yyyymmdd ints against the public dataset
    body = captured["body"]
    assert "patents-public-data.patents.publications" in body["query"]
    params = {p["name"]: p["parameterValue"]["value"] for p in body["queryParameters"]}
    assert len(params["lo"]) == 8 and len(params["hi"]) == 8
    assert params["lim"] == "10"
    # Normalization: dashes stripped, date formatted, empty row skipped
    assert rows == [
        {
            "source": "bigquery",
            "patent_number": "US6934691B1",
            "title": "Group payment system",
            "abstract": "Splits shared bills.",
            "filing_date": "2002-02-14",
            "legal_status": "Expired - statutory term (filed more than 20 years ago)",
        }
    ]


def test_rejects_invalid_credentials_json(monkeypatch):
    monkeypatch.setattr(settings, "google_service_account_json", "{not json")
    with pytest.raises(RuntimeError, match="not valid JSON"):
        asyncio.run(BigQuerySource().fetch_expired_candidates())
