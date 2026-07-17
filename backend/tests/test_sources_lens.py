"""Tests for the Lens.org adapter."""

import asyncio
import json

import httpx
import pytest

from app.config import settings
from app.services.patent_sources import LensSource


def test_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "lens_api_key", "")
    with pytest.raises(RuntimeError, match="LENS_API_KEY"):
        asyncio.run(LensSource().fetch_expired_candidates())


def test_query_and_normalization(monkeypatch):
    monkeypatch.setattr(settings, "lens_api_key", "lens-token")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "total": 2,
                "data": [
                    {
                        "lens_id": "091-283-843",
                        "jurisdiction": "US",
                        "doc_number": "6934691",
                        "kind": "B1",
                        "earliest_claim_date": "2002-02-14",
                        "biblio": {
                            "invention_title": [
                                {"text": "Systeme de paiement", "lang": "fr"},
                                {"text": "Group payment system", "lang": "en"},
                            ]
                        },
                        "abstract": [{"text": "Splits shared bills.", "lang": "en"}],
                        "legal_status": {"patent_status": "EXPIRED"},
                    },
                    {"doc_number": None},
                ],
            },
        )

    rows = asyncio.run(
        LensSource().fetch_expired_candidates(
            days_window=7, limit=10, transport=httpx.MockTransport(handler)
        )
    )

    assert captured["auth"] == "Bearer lens-token"
    must = captured["body"]["query"]["bool"]["must"]
    assert {"term": {"jurisdiction": "US"}} in must
    range_clause = next(c for c in must if "range" in c)
    assert set(range_clause["range"]["earliest_claim_date"]) == {"gte", "lte"}
    assert rows == [
        {
            "source": "lens",
            "patent_number": "US6934691B1",
            "title": "Group payment system",
            "abstract": "Splits shared bills.",
            "filing_date": "2002-02-14",
            "legal_status": "Expired - expired (Lens.org legal status)",
        }
    ]
