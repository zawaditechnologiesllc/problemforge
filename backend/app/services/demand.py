"""Community demand signals: real questions people ask, scraped from public
old.reddit.com and Quora search pages — plain HTTP, no API keys.

Design constraints (deliberate):
- Low volume and polite: one request per source per query, honest bot
  User-Agent, short timeouts, results cached for 24 hours.
- Best-effort: both sites change markup and rate-limit datacenter IPs; every
  failure degrades to an empty list, never an error. Quora in particular
  often serves a login wall to bots — when it does, we simply get nothing.
- Review each site's terms of service before scaling this up; the safe
  posture is exactly this: tiny, cached, public-page reads.
"""

import re
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from ..config import settings
from . import cache

USER_AGENT = (
    "Mozilla/5.0 (compatible; ProblemForgeSignals/1.0; "
    "research of public community questions)"
)
_QUORA_SKIP_PREFIXES = (
    "/profile/", "/topic/", "/search", "/about", "/careers", "/contact",
    "/press", "/login", "/signup", "/answer/", "/q/",
)


def _query_terms(text: str, max_words: int = 12) -> str:
    """Long validator ideas make bad search queries — keep the first N words."""
    return " ".join(re.sub(r"[^\w\s'-]", " ", text).split()[:max_words])


def parse_reddit_search_html(html: str, limit: int) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for result in soup.select("div.search-result"):
        title_link = result.select_one("a.search-title")
        if not title_link or not title_link.get_text(strip=True):
            continue
        comments = 0
        comments_el = result.select_one("a.search-comments, span.search-comments")
        if comments_el:
            match = re.search(r"(\d+)", comments_el.get_text())
            if match:
                comments = int(match.group(1))
        subreddit_el = result.select_one("a.search-subreddit-link")
        results.append(
            {
                "source": "reddit",
                "title": title_link.get_text(strip=True),
                "url": title_link.get("href") or "",
                "community": subreddit_el.get_text(strip=True) if subreddit_el else None,
                "engagement": comments,
            }
        )
        if len(results) >= limit:
            break
    return results


def parse_quora_search_html(html: str, limit: int) -> list[dict]:
    """Pull question links out of whatever HTML Quora serves.

    Question URLs are slugs like /How-do-I-track-medication-refills. A login
    wall or JS-only page simply yields no matches.
    """
    seen: set[str] = set()
    results = []
    for match in re.finditer(r'href="(/[A-Za-z0-9][A-Za-z0-9%\-]{24,})"', html):
        path = match.group(1)
        if path.lower().startswith(_QUORA_SKIP_PREFIXES) or path in seen:
            continue
        if path.count("-") < 3:  # question slugs are multi-word
            continue
        seen.add(path)
        results.append(
            {
                "source": "quora",
                "title": path.strip("/").replace("-", " "),
                "url": f"https://www.quora.com{path}",
                "community": None,
                "engagement": None,
            }
        )
        if len(results) >= limit:
            break
    return results


async def fetch_reddit_questions(
    query: str, limit: int = 8, transport: httpx.AsyncBaseTransport | None = None
) -> list[dict]:
    url = f"https://old.reddit.com/search?q={quote_plus(query)}&sort=top&t=all"
    async with httpx.AsyncClient(
        timeout=12, transport=transport, follow_redirects=True
    ) as client:
        resp = await client.get(url, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        return parse_reddit_search_html(resp.text, limit)


async def fetch_quora_questions(
    query: str, limit: int = 5, transport: httpx.AsyncBaseTransport | None = None
) -> list[dict]:
    url = f"https://www.quora.com/search?q={quote_plus(query)}"
    async with httpx.AsyncClient(
        timeout=12, transport=transport, follow_redirects=True
    ) as client:
        resp = await client.get(url, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        return parse_quora_search_html(resp.text, limit)


async def gather_demand_signals(
    text: str, transport: httpx.AsyncBaseTransport | None = None
) -> dict:
    """Real community questions related to `text`, cached for 24 hours."""
    empty = {"questions": [], "score": None}
    if not settings.demand_signals_enabled:
        return empty
    query = _query_terms(text)
    if not query:
        return empty

    key = cache.hash_key("demand", query.lower())
    cached = await cache.get_json(key)
    if cached is not None:
        return cached

    questions: list[dict] = []
    for fetcher in (fetch_reddit_questions, fetch_quora_questions):
        try:
            questions.extend(await fetcher(query, transport=transport))
        except Exception:
            continue  # best-effort by design

    signals = {"questions": questions[:10], "score": demand_score(questions)}
    await cache.set_json(key, signals, ttl_seconds=24 * 3600)
    return signals


def demand_score(questions: list[dict]) -> int | None:
    """0-100 heuristic from volume + engagement of real community questions."""
    if not questions:
        return None
    volume = min(len(questions), 10) * 6  # up to 60
    engagement = sum(q.get("engagement") or 0 for q in questions)
    return min(95, volume + min(35, engagement // 5))
