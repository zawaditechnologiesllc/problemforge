"""Tests for community demand signals (old.reddit + Quora HTML parsing)."""

import asyncio

import httpx

from app.config import settings
from app.services import demand

REDDIT_HTML = """
<html><body>
<div class="search-result search-result-link">
  <header><a class="search-title may-blank" href="https://old.reddit.com/r/smallbusiness/comments/abc/no_shows/">
    How do you deal with no-show appointments killing your revenue?</a></header>
  <div><span class="search-comments">47 comments</span>
  <a class="search-subreddit-link" href="/r/smallbusiness">r/smallbusiness</a></div>
</div>
<div class="search-result search-result-link">
  <header><a class="search-title may-blank" href="https://old.reddit.com/r/physicaltherapy/comments/def/soap_notes/">
    SOAP notes are eating 90 minutes of my day, any tools?</a></header>
  <div><span class="search-comments">12 comments</span></div>
</div>
<div class="search-result"><header></header></div>
</body></html>
"""

QUORA_HTML = """
<html><body>
<a href="/How-can-small-clinics-reduce-appointment-no-shows">x</a>
<a href="/profile/Some-Person">profile</a>
<a href="/topic/Healthcare">topic</a>
<a href="/What-software-do-physical-therapists-use-for-documentation">y</a>
<a href="/short-one">z</a>
</body></html>
"""


def test_parse_reddit_search_html():
    rows = demand.parse_reddit_search_html(REDDIT_HTML, limit=10)
    assert len(rows) == 2
    assert rows[0]["source"] == "reddit"
    assert "no-show" in rows[0]["title"]
    assert rows[0]["engagement"] == 47
    assert rows[0]["community"] == "r/smallbusiness"


def test_parse_quora_search_html_skips_non_questions():
    rows = demand.parse_quora_search_html(QUORA_HTML, limit=10)
    titles = [row["title"] for row in rows]
    assert "How can small clinics reduce appointment no shows" in titles
    assert all("profile" not in row["url"] for row in rows)
    assert all(row["source"] == "quora" for row in rows)


def test_quora_login_wall_yields_nothing():
    assert demand.parse_quora_search_html("<html>Please sign in</html>", 5) == []


def test_gather_signals_degrades_and_caches(monkeypatch):
    monkeypatch.setattr(settings, "demand_signals_enabled", True)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if "reddit" in request.url.host:
            return httpx.Response(200, text=REDDIT_HTML)
        return httpx.Response(403, text="blocked")  # Quora bot wall

    transport = httpx.MockTransport(handler)
    first = asyncio.run(
        demand.gather_demand_signals("dealing with appointment no shows", transport=transport)
    )
    assert len(first["questions"]) == 2
    assert first["score"] is not None and 0 < first["score"] <= 95

    # Second call must come from cache — no new HTTP requests
    before = calls["n"]
    second = asyncio.run(
        demand.gather_demand_signals("dealing with appointment no shows", transport=transport)
    )
    assert second == first
    assert calls["n"] == before


def test_disabled_flag_returns_empty(monkeypatch):
    monkeypatch.setattr(settings, "demand_signals_enabled", False)
    result = asyncio.run(demand.gather_demand_signals("anything at all here"))
    assert result == {"questions": [], "score": None}


def test_demand_score_heuristic():
    assert demand.demand_score([]) is None
    few = [{"engagement": 0}]
    assert demand.demand_score(few) == 6
    many = [{"engagement": 100}] * 10
    assert demand.demand_score(many) == 95  # capped
