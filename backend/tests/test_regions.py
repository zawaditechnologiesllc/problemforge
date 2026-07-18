"""Tests for the 20 regional sources and their provider routing."""

import asyncio
import json

import httpx

from app.config import settings
from app.services.patent_sources import REGIONS, all_sources, enabled_sources


def _clear_all_creds(monkeypatch):
    monkeypatch.setattr(settings, "uspto_api_key", "")
    monkeypatch.setattr(settings, "google_service_account_json", "")
    monkeypatch.setattr(settings, "lens_api_key", "")
    monkeypatch.setattr(settings, "epo_ops_key", "")
    monkeypatch.setattr(settings, "epo_ops_secret", "")


def test_twenty_regions_all_unique():
    sources = all_sources()
    assert len(sources) == 20
    codes = [source.region.code for source in sources]
    assert len(set(codes)) == 20
    # The markets the product targets are all present
    for code in ("US", "EP", "JP", "KR", "CN", "IN", "BR", "MX", "ZA", "SG", "IL"):
        assert code in codes


def test_no_credentials_means_no_enabled_sources(monkeypatch):
    _clear_all_creds(monkeypatch)
    assert enabled_sources() == []


def test_one_global_provider_lights_up_every_region(monkeypatch):
    _clear_all_creds(monkeypatch)
    monkeypatch.setattr(settings, "lens_api_key", "lens-token")
    enabled = enabled_sources()
    assert len(enabled) == 20
    assert all(source.provider().name == "lens" for source in enabled)


def test_us_prefers_uspto_and_falls_back(monkeypatch):
    _clear_all_creds(monkeypatch)
    monkeypatch.setattr(settings, "uspto_api_key", "pv-key")
    monkeypatch.setattr(settings, "lens_api_key", "lens-token")
    us = next(source for source in all_sources() if source.region.code == "US")
    assert us.provider().name == "uspto"

    monkeypatch.setattr(settings, "uspto_api_key", "")
    us = next(source for source in all_sources() if source.region.code == "US")
    assert us.provider().name == "lens"


def test_ep_prefers_epo(monkeypatch):
    _clear_all_creds(monkeypatch)
    monkeypatch.setattr(settings, "epo_ops_key", "k")
    monkeypatch.setattr(settings, "epo_ops_secret", "s")
    monkeypatch.setattr(settings, "lens_api_key", "lens-token")
    ep = next(source for source in all_sources() if source.region.code == "EP")
    assert ep.provider().name == "epo"


def test_regional_fetch_scopes_jurisdiction_and_stamps_it(monkeypatch):
    _clear_all_creds(monkeypatch)
    monkeypatch.setattr(settings, "lens_api_key", "lens-token")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "jurisdiction": "JP",
                        "doc_number": "3999999",
                        "kind": "B2",
                        "earliest_claim_date": "2004-03-01",
                        "biblio": {
                            "invention_title": [{"text": "A device", "lang": "en"}]
                        },
                        "abstract": [{"text": "Does things.", "lang": "en"}],
                        "legal_status": {"patent_status": "EXPIRED"},
                    }
                ]
            },
        )

    jp = next(source for source in all_sources() if source.region.code == "JP")
    rows = asyncio.run(
        jp.fetch_expired_candidates(
            days_window=7, limit=5, transport=httpx.MockTransport(handler)
        )
    )
    must = captured["body"]["query"]["bool"]["must"]
    assert {"term": {"jurisdiction": "JP"}} in must
    assert rows[0]["jurisdiction"] == "JP"
    assert rows[0]["patent_number"] == "JP3999999B2"


def test_region_list_matches_registry():
    assert len(REGIONS) == 20
    assert all(region.providers for region in REGIONS)
