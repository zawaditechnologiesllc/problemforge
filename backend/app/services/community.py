"""Startup-community corpus: ideas people publicly ask for on old.reddit.

Weekly, we pull the top posts of the month from startup-idea communities —
public pages, plain HTTP, no API keys — embed them, and store them. The data
improves results users see in two places, with full attribution and links
back to the original posts:

- Validator: "startup communities are asking for this" matches.
- Blueprint enrichment: evidence for whether the old problem still exists.

Same politeness rules as services/demand.py: one request per community per
run, honest User-Agent, best-effort degradation, and a weekly cadence.
"""

import re

import httpx
from bs4 import BeautifulSoup

from ..db import get_db
from . import llm
from .demand import USER_AGENT

# Communities where people describe problems they want built/solved.
COMMUNITIES = (
    "SomebodyMakeThis",
    "AppIdeas",
    "Startup_Ideas",
    "startups",
    "SaaS",
    "Entrepreneur",
    "smallbusiness",
    "sidehustle",
)


def parse_subreddit_listing_html(html: str, community: str, limit: int) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    posts = []
    for thing in soup.select("div.thing"):
        if thing.get("data-promoted") == "true":
            continue
        permalink = thing.get("data-permalink")
        title_el = thing.select_one("a.title")
        if not permalink or not title_el:
            continue
        score = 0
        score_el = thing.select_one("div.score.unvoted")
        if score_el:
            raw = score_el.get("title") or score_el.get_text(strip=True)
            match = re.search(r"(\d+)", str(raw).replace(",", ""))
            if match:
                score = int(match.group(1))
        num_comments = 0
        comments_el = thing.select_one("a.comments")
        if comments_el:
            match = re.search(r"(\d+)", comments_el.get_text())
            if match:
                num_comments = int(match.group(1))
        posts.append(
            {
                "source": "reddit",
                "community": f"r/{community}",
                "title": title_el.get_text(strip=True),
                "url": f"https://old.reddit.com{permalink}",
                "score": score,
                "num_comments": num_comments,
            }
        )
        if len(posts) >= limit:
            break
    return posts


async def fetch_community_top(
    community: str,
    period: str = "month",
    limit: int = 25,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[dict]:
    url = f"https://old.reddit.com/r/{community}/top/?t={period}"
    async with httpx.AsyncClient(
        timeout=12, transport=transport, follow_redirects=True
    ) as client:
        resp = await client.get(url, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        return parse_subreddit_listing_html(resp.text, community, limit)


async def run_community_ingestion(limit_per_community: int = 25) -> dict:
    """Refresh the corpus. Idempotent by post URL; embeddings are cached."""
    db = get_db()
    stats = {"fetched": 0, "inserted": 0, "failed": 0}
    for community in COMMUNITIES:
        try:
            posts = await fetch_community_top(community, limit=limit_per_community)
        except Exception:
            stats["failed"] += 1
            continue
        stats["fetched"] += len(posts)
        for post in posts:
            try:
                exists = (
                    db.table("community_posts")
                    .select("id")
                    .eq("url", post["url"])
                    .limit(1)
                    .execute()
                    .data
                )
                if exists:
                    continue
                embedding = await llm.embed(post["title"])
                db.table("community_posts").insert(
                    {**post, "embedding": embedding}
                ).execute()
                stats["inserted"] += 1
            except Exception:
                stats["failed"] += 1
    return stats


def match_posts(db, embedding: list[float], count: int = 3) -> list[dict]:
    """Corpus posts similar to an embedding — user-facing, with links."""
    try:
        result = db.rpc(
            "match_community_posts",
            {"query_embedding": embedding, "match_count": count},
        ).execute()
    except Exception:
        return []
    matches = []
    for row in result.data or []:
        similarity = max(0.0, min(1.0, float(row.get("similarity") or 0)))
        if similarity < 0.3:
            continue
        matches.append(
            {
                "title": row.get("title"),
                "url": row.get("url"),
                "community": row.get("community"),
                "upvotes": row.get("score") or 0,
                "num_comments": row.get("num_comments") or 0,
                "similarity": round(similarity, 4),
            }
        )
    return matches
