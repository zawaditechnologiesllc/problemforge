"""The 5-Point Validation Framework.

Every Validator run pressure-tests the idea against five pillars:

1. Market Size    — are enough people searching for / discussing the problem?
                    Scored by demographics, with the best demographic named.
2. Competition    — do existing solutions have proven demand? Names the gaps
                    where the idea can differentiate (informed by real
                    community questions).
3. Feasibility    — can an MVP ship in 2-3 months with no-code tools or a
                    small team?
4. Monetization   — is there a concrete revenue model? Recommends the best.
5. Uniqueness     — what makes it compelling? Better UX or a focused niche
                    is enough; it need not be a new invention.

Analyses are LLM-generated (user-facing coder model), strict-JSON validated,
and cached 24h by idea hash so repeat runs cost nothing.
"""

import json
import re

from ..config import settings
from . import cache, llm

PILLARS = ("market_size", "competition", "feasibility", "monetization", "uniqueness")

_SYSTEM = (
    "You are a pragmatic, evidence-driven startup validator. You assess app "
    "ideas against a fixed 5-point framework. Be direct and specific — no "
    "hedging filler. Ground claims in the evidence provided (expired-patent "
    "matches and real community questions) when it exists, and say so when it "
    "does not. Scores are 0-100 integers where 50 means genuinely uncertain."
)

_USER_TEMPLATE = """Assess this app idea against the 5-Point Validation Framework.

IDEA:
{idea}

EVIDENCE — expired patents solving similar problems (proven, once-patented demand):
{matches}

EVIDENCE — real questions people are asking in communities right now:
{questions}

Respond with STRICTLY this JSON (no markdown, no commentary outside the JSON):
{{
  "market_size": {{"score": 0, "assessment": "Are enough people searching for or discussing this problem? Which demographics feel it hardest?", "best_demographic": "the single most promising demographic to target first and why"}},
  "competition": {{"score": 0, "assessment": "Do existing solutions have proven demand?", "gaps": ["specific gap where this idea can differentiate", "another gap"]}},
  "feasibility": {{"score": 0, "assessment": "Can an MVP be built in 2-3 months with no-code tools or a small team?", "mvp_scope": "the smallest shippable version in one sentence"}},
  "monetization": {{"score": 0, "assessment": "Is there a concrete revenue model with willingness to pay?", "recommended_model": "the single best revenue model (e.g. subscription for ongoing value, premium B2B pricing) and why"}},
  "uniqueness": {{"score": 0, "assessment": "What makes this compelling? Better UX or a focused niche is enough.", "angle": "the sharpest differentiation angle in one sentence"}},
  "overall_score": 0,
  "verdict": "2-3 sentence bottom line: build, reshape, or walk away — and the first thing to do next"
}}"""


def _format_matches(matches: list[dict]) -> str:
    if not matches:
        return "(none found)"
    lines = []
    for match in matches[:3]:
        lines.append(
            f"- {match.get('title')} (similarity {round((match.get('similarity') or 0) * 100)}%): "
            f"{(match.get('human_problem') or '')[:220]}"
        )
    return "\n".join(lines)


def _format_questions(questions: list[dict]) -> str:
    if not questions:
        return "(none found)"
    lines = []
    for question in questions[:8]:
        engagement = question.get("engagement")
        suffix = f" [{engagement} comments]" if engagement else ""
        lines.append(f"- ({question.get('source')}) {question.get('title')}{suffix}")
    return "\n".join(lines)


def parse_framework_json(raw: str) -> dict | None:
    """Validate the LLM output into the exact shape the UI renders."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    for pillar in PILLARS:
        block = data.get(pillar)
        if not isinstance(block, dict) or "assessment" not in block:
            return None
        try:
            block["score"] = max(0, min(100, int(block.get("score", 0))))
        except (TypeError, ValueError):
            block["score"] = 50
    if isinstance(data.get("competition", {}).get("gaps"), str):
        data["competition"]["gaps"] = [data["competition"]["gaps"]]
    if not isinstance(data.get("competition", {}).get("gaps"), list):
        data["competition"]["gaps"] = []
    try:
        data["overall_score"] = max(0, min(100, int(data.get("overall_score", 0))))
    except (TypeError, ValueError):
        data["overall_score"] = round(
            sum(data[p]["score"] for p in PILLARS) / len(PILLARS)
        )
    data.setdefault("verdict", "")
    return {key: data[key] for key in (*PILLARS, "overall_score", "verdict")}


async def analyze_idea(
    idea: str, matches: list[dict], questions: list[dict]
) -> dict | None:
    """Run the framework. Returns None when no LLM is configured or output fails validation."""
    if not settings.llm_api_key:
        return None

    key = cache.hash_key("framework", idea.strip().lower())
    cached = await cache.get_json(key)
    if cached is not None:
        return cached

    try:
        raw = await llm.chat(
            settings.coder_model,
            _SYSTEM,
            _USER_TEMPLATE.format(
                idea=idea.strip()[:1500],
                matches=_format_matches(matches),
                questions=_format_questions(questions),
            ),
            max_tokens=1400,
            temperature=0.3,
        )
    except Exception:
        return None

    parsed = parse_framework_json(raw)
    if parsed is not None:
        await cache.set_json(key, parsed, ttl_seconds=24 * 3600)
    return parsed
