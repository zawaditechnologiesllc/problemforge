"""Tests for the startup-community corpus (old.reddit listing parsing)."""

import asyncio

import httpx

from app.services import community

LISTING_HTML = """
<html><body>
<div class="thing" data-promoted="true" data-permalink="/r/startups/comments/ad1/sponsored/">
  <a class="title">Sponsored: buy our thing</a>
</div>
<div class="thing" data-permalink="/r/SomebodyMakeThis/comments/xyz/an_app_that_reminds_me/">
  <p class="title"><a class="title">Somebody make an app that reminds me to follow up with leads</a></p>
  <div class="score unvoted" title="482">482</div>
  <a class="comments" href="#">57 comments</a>
</div>
<div class="thing" data-permalink="/r/SomebodyMakeThis/comments/abc/tool_for_splitting/">
  <p class="title"><a class="title">A tool for splitting utility bills between roommates automatically</a></p>
  <div class="score unvoted" title="1,204">1.2k</div>
  <a class="comments" href="#">203 comments</a>
</div>
<div class="thing"><p class="title"></p></div>
</body></html>
"""


def test_parse_listing_skips_promoted_and_broken():
    posts = community.parse_subreddit_listing_html(LISTING_HTML, "SomebodyMakeThis", 10)
    assert len(posts) == 2
    assert posts[0]["title"].startswith("Somebody make an app")
    assert posts[0]["score"] == 482
    assert posts[0]["num_comments"] == 57
    assert posts[0]["community"] == "r/SomebodyMakeThis"
    assert posts[0]["url"].startswith("https://old.reddit.com/r/SomebodyMakeThis/")
    # Comma-grouped score parsed correctly
    assert posts[1]["score"] == 1204


def test_fetch_community_top_uses_listing_url():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["ua"] = request.headers.get("user-agent", "")
        return httpx.Response(200, text=LISTING_HTML)

    posts = asyncio.run(
        community.fetch_community_top(
            "SomebodyMakeThis", transport=httpx.MockTransport(handler)
        )
    )
    assert "old.reddit.com/r/SomebodyMakeThis/top/?t=month" in captured["url"]
    assert "ProblemForge" in captured["ua"]  # honest bot UA
    assert len(posts) == 2


def test_communities_list_is_sane():
    assert len(community.COMMUNITIES) >= 6
    assert "SomebodyMakeThis" in community.COMMUNITIES
