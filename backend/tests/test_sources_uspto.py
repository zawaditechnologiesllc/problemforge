"""Tests for the USPTO/PatentsView adapter and shared public-domain helpers."""

import asyncio
import json
from datetime import date

import httpx
import pytest

from app.config import settings
from app.services.patent_sources import USPTOSource
from app.services.patent_sources.base import (
    is_public_domain,
    normalize_patent_number,
    twenty_years_ago,
)


def test_twenty_years_ago_window():
    lo, hi = twenty_years_ago(7)
    assert date.today().year - hi.year == 20
    assert (hi - lo).days == 7


def test_normalize_patent_number():
    assert normalize_patent_number("US 7,156,808 B2") == "US7156808B2"
    assert normalize_patent_number("us-7156808-b2") == "US7156808B2"
    assert normalize_patent_number("EP1234567A1") == "EP1234567A1"


def test_fetch_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "uspto_api_key", "")
    with pytest.raises(RuntimeError, match="USPTO_API_KEY"):
        asyncio.run(USPTOSource().fetch_expired_candidates())


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
        USPTOSource().fetch_expired_candidates(
            days_window=7, limit=5, transport=httpx.MockTransport(handler)
        )
    )

    assert captured["headers"].get("x-api-key") == "test-key"
    query = json.loads(captured["params"]["q"])
    for clause in query["_and"]:
        field = list(list(clause.values())[0].keys())[0]
        assert field == "patent_earliest_application_date"
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


def test_fetch_by_number_used_for_fto_verification(monkeypatch):
    monkeypatch.setattr(settings, "uspto_api_key", "test-key")

    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(httpx.QueryParams(request.url.query))
        assert json.loads(params["q"]) == {"patent_id": "6934691"}
        return httpx.Response(
            200,
            json={
                "patents": [
                    {
                        "patent_id": "6934691",
                        "patent_title": "Group payment system",
                        "patent_earliest_application_date": "2002-02-14",
                        "patent_date": "2005-08-23",
                    }
                ]
            },
        )

    result = asyncio.run(
        USPTOSource().fetch_by_number("US6934691B1", transport=httpx.MockTransport(handler))
    )
    assert result is not None
    assert result["filing_date"] == "2002-02-14"


def test_fetch_by_number_non_us_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "uspto_api_key", "test-key")
    assert asyncio.run(USPTOSource().fetch_by_number("EP1234567A1")) is None


def test_fetch_raises_on_http_error(monkeypatch):
    monkeypatch.setattr(settings, "uspto_api_key", "bad-key")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(403, json={"error": "forbidden"})
    )
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(USPTOSource().fetch_expired_candidates(transport=transport))


def test_public_domain_gate():
    assert is_public_domain({"filing_date": "2001-01-01", "legal_status": None})
    assert is_public_domain(
        {"filing_date": None, "legal_status": "Expired - lapsed for non-payment"}
    )
    assert not is_public_domain({"filing_date": "2020-01-01", "legal_status": "Active"})
    assert not is_public_domain({"filing_date": None, "legal_status": None})
    assert not is_public_domain({"filing_date": "not-a-date", "legal_status": None})
