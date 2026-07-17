"""Tests for the USPTO/PatentsView adapter and the public-domain gate."""

import asyncio
import json
from datetime import date

import httpx
import pytest

from app.config import settings
from app.services import patents


def test_twenty_years_ago_window():
    lo, hi = patents._twenty_years_ago(7)
    assert date.today().year - hi.year == 20
    assert (hi - lo).days == 7


def test_fetch_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "uspto_api_key", "")
    with pytest.raises(RuntimeError, match="USPTO_API_KEY"):
        asyncio.run(patents.fetch_expired_candidates())


def test_fetch_expired_candidates_builds_query_and_normalizes(monkeypatch):
    monkeypatch.setattr(settings, "uspto_api_key", "test-key")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["params"] = dict(httpx.QueryParams(request.url.query))
        return httpx.Response(
            200,
            json={
                "patents": [
                    {
                        "patent_id": "7156808",
                        "patent_title": "Remote monitoring of therapy compliance",
                        "patent_abstract": "A home rehab compliance system.",
                        "patent_date": "2007-01-02",
                        "patent_earliest_application_date": "2004-06-15",
                    }
                ]
            },
        )

    rows = asyncio.run(
        patents.fetch_expired_candidates(
            days_window=7, limit=5, transport=httpx.MockTransport(handler)
        )
    )

    # Authenticates with the PatentsView key header
    assert captured["headers"].get("x-api-key") == "test-key"
    # Queries by earliest filing date, bounded to the 20-years-ago window
    query = json.loads(captured["params"]["q"])
    bounds = [list(clause.keys())[0] for clause in query["_and"]]
    assert bounds == ["_gte", "_lte"]
    for clause in query["_and"]:
        field = list(list(clause.values())[0].keys())[0]
        assert field == "patent_earliest_application_date"
    # Normalizes into the common adapter shape
    assert rows == [
        {
            "source": "uspto",
            "patent_number": "US7156808",
            "title": "Remote monitoring of therapy compliance",
            "abstract": "A home rehab compliance system.",
            "filing_date": "2004-06-15",
            "legal_status": "Expired - statutory term (filed more than 20 years ago)",
        }
    ]


def test_fetch_handles_empty_results(monkeypatch):
    monkeypatch.setattr(settings, "uspto_api_key", "test-key")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"patents": None})
    )
    rows = asyncio.run(patents.fetch_expired_candidates(transport=transport))
    assert rows == []


def test_fetch_raises_on_http_error(monkeypatch):
    monkeypatch.setattr(settings, "uspto_api_key", "bad-key")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(403, json={"error": "forbidden"})
    )
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(patents.fetch_expired_candidates(transport=transport))


def test_public_domain_gate():
    # Old filing date -> public domain
    assert patents.is_public_domain({"filing_date": "2001-01-01", "legal_status": None})
    # Explicitly expired status -> public domain
    assert patents.is_public_domain(
        {"filing_date": None, "legal_status": "Expired - lapsed for non-payment"}
    )
    # Recent filing, active status -> must be rejected
    assert not patents.is_public_domain(
        {"filing_date": "2020-01-01", "legal_status": "Active"}
    )
    # No evidence at all -> must be rejected
    assert not patents.is_public_domain({"filing_date": None, "legal_status": None})
    # Garbage date -> must be rejected
    assert not patents.is_public_domain(
        {"filing_date": "not-a-date", "legal_status": None}
    )
