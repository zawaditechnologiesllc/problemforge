"""Tests for the EPO OPS adapter (OAuth + nested JSON parsing + local gate)."""

import asyncio
import base64
from datetime import timedelta

import httpx
import pytest

from app.config import settings
from app.services.patent_sources import EPOSource, twenty_years_ago


def _exchange_document(number: str, filing_yyyymmdd: str) -> dict:
    return {
        "exchange-document": {
            "@country": "EP",
            "@doc-number": number,
            "@kind": "A1",
            "bibliographic-data": {
                "application-reference": {
                    "document-id": [
                        {"date": {"$": filing_yyyymmdd}},
                    ]
                },
                "invention-title": [
                    {"@lang": "de", "$": "Vorrichtung"},
                    {"@lang": "en", "$": "A useful device"},
                ],
            },
            "abstract": {"p": {"$": "Does something useful."}},
        }
    }


def test_requires_credentials(monkeypatch):
    monkeypatch.setattr(settings, "epo_ops_key", "")
    monkeypatch.setattr(settings, "epo_ops_secret", "")
    with pytest.raises(RuntimeError, match="EPO_OPS_KEY"):
        asyncio.run(EPOSource().fetch_expired_candidates())


def test_oauth_search_and_filing_date_gate(monkeypatch):
    monkeypatch.setattr(settings, "epo_ops_key", "consumer-key")
    monkeypatch.setattr(settings, "epo_ops_secret", "consumer-secret")
    captured: dict = {}

    # A filing inside this week's 20-years-ago discovery window
    lo, hi = twenty_years_ago(7)
    in_window = (hi - timedelta(days=2)).strftime("%Y%m%d")
    in_window_iso = (hi - timedelta(days=2)).isoformat()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/accesstoken"):
            captured["basic"] = request.headers.get("authorization")
            return httpx.Response(
                200, json={"access_token": "ops-token", "expires_in": 1200}
            )
        captured["bearer"] = request.headers.get("authorization")
        captured["params"] = dict(httpx.QueryParams(request.url.query))
        return httpx.Response(
            200,
            json={
                "ops:world-patent-data": {
                    "ops:biblio-search": {
                        "ops:search-result": {
                            "exchange-documents": [
                                _exchange_document("1500000", in_window),
                                # Filed too recently -> must be filtered out
                                _exchange_document("2900000", "20150610"),
                            ]
                        }
                    }
                }
            },
        )

    rows = asyncio.run(
        EPOSource().fetch_expired_candidates(
            days_window=7, limit=10, transport=httpx.MockTransport(handler)
        )
    )

    expected_basic = base64.b64encode(b"consumer-key:consumer-secret").decode()
    assert captured["basic"] == f"Basic {expected_basic}"
    assert captured["bearer"] == "Bearer ops-token"
    assert 'pd within' in captured["params"]["q"] and "pn=EP" in captured["params"]["q"]
    # Only the patent whose application date crossed the 20-year term survives
    assert rows == [
        {
            "source": "epo",
            "patent_number": "EP1500000A1",
            "title": "A useful device",
            "abstract": "Does something useful.",
            "filing_date": in_window_iso,
            "legal_status": "Expired - statutory term (filed more than 20 years ago)",
        }
    ]


def test_provider_registry(monkeypatch):
    from app.services.patent_sources import provider_sources

    assert [provider.name for provider in provider_sources()] == [
        "uspto",
        "bigquery",
        "lens",
        "epo",
    ]
