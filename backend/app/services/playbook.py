"""Blueprint enrichment: the Modern AI Playbook + a stored 5-point validation.

For each blueprint (an old, expired-patent problem) we generate once and
store forever:

- **Playbook** — does the problem still exist today (with evidence from the
  startup-community corpus), how to solve it NOW using AI, a concrete
  end-to-end stack covering design → coding → configuration → integration →
  testing, and marketing/distribution channels with the audience each one
  reaches and how.
- **Validation** — the same 5-Point Validation Framework used by the
  Validator, run against the blueprint itself. The result is shown to ALL
  users on the blueprint page so they can judge how valid the idea is.

Generation is lazy (first signed-in view kicks a background job) or bulk
(worker/backfill_enrichment.py). A short cache lock prevents stampedes.
"""

import json
import re

from ..config import settings
from ..db import get_db
from . import cache, community, demand, framework, llm

STAGES = ("design", "coding", "configuration", "integration", "testing")

_SYSTEM = (
    "You are a hands-on startup strategist who has shipped AI products. You "
    "turn old, expired-patent problems into concrete modern build-and-launch "
    "playbooks. Be specific: name real tools, real services, and real "
    "channels. Assume the builder is a solo 'vibe coder' using AI coding "
    "assistants."
)

_USER_TEMPLATE = """An expired patent solved this problem. Produce the modern playbook.

TITLE: {title}
THE HUMAN PROBLEM: {human_problem}
THE EXPIRED CORE LOGIC: {expired_logic}

EVIDENCE — what startup communities are asking for right now (may be empty):
{evidence}

Respond with STRICTLY this JSON (no markdown outside it):
{{
  "problem_today": {{
    "still_exists": true,
    "assessment": "Does this problem still exist today? Who feels it and how has it changed?",
    "evidence": "one sentence citing the strongest signal (community demand, market behavior) or stating that evidence is thin"
  }},
  "ai_solution": "How to solve it NOW using AI — the 2-4 sentence modern approach (LLMs, vision, speech, agents) that the original inventor could not use",
  "stack": {{
    "design": "design phase: tools + approach (e.g. Google Stitch or Figma for screens, a design system choice)",
    "coding": "coding phase: framework + AI coding tools (e.g. Next.js 14 + TypeScript built with Cursor/Windsurf; note mobile choice if relevant)",
    "configuration": "hosting + configuration (e.g. Vercel frontend, Render/FastAPI backend, Supabase Postgres+Auth, env/secrets setup)",
    "integration": "the third-party APIs that do the heavy lifting (e.g. OpenAI/Whisper, Stripe, Twilio) and what each is for",
    "testing": "testing approach: what to test and with what (e.g. Playwright e2e on the money path, pytest for the API, a 10-user beta)"
  }},
  "marketing": {{
    "channels": [
      {{"channel": "channel name (e.g. Reddit communities, SEO, TikTok/short-form, Product Hunt, cold outreach, marketplaces/integrations)", "audience": "who this reaches", "how": "the specific tactic — different ways to reach that audience"}},
      {{"channel": "...", "audience": "...", "how": "..."}}
    ]
  }}
}}

Give 3 to 5 marketing channels, ordered by expected impact for THIS product."""


def parse_playbook_json(raw: str) -> dict | None:
    """Validate LLM output into the exact shape the UI renders."""
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

    problem_today = data.get("problem_today")
    if not isinstance(problem_today, dict) or not problem_today.get("assessment"):
        return None
    problem_today["still_exists"] = bool(problem_today.get("still_exists", True))
    problem_today.setdefault("evidence", "")

    if not data.get("ai_solution"):
        return None

    stack = data.get("stack")
    if not isinstance(stack, dict):
        return None
    for stage in STAGES:
        if not stack.get(stage):
            return None

    channels_raw = (data.get("marketing") or {}).get("channels")
    if not isinstance(channels_raw, list) or not channels_raw:
        return None
    channels = []
    for channel in channels_raw[:5]:
        if isinstance(channel, dict) and channel.get("channel"):
            channels.append(
                {
                    "channel": str(channel["channel"]),
                    "audience": str(channel.get("audience") or ""),
                    "how": str(channel.get("how") or ""),
                }
            )
    if not channels:
        return None

    return {
        "problem_today": problem_today,
        "ai_solution": str(data["ai_solution"]),
        "stack": {stage: str(stack[stage]) for stage in STAGES},
        "marketing": {"channels": channels},
    }


def _format_evidence(matches: list[dict], questions: list[dict]) -> str:
    lines = []
    for match in matches[:3]:
        lines.append(
            f"- ({match.get('community')}, {match.get('upvotes')} upvotes) {match.get('title')}"
        )
    for question in questions[:4]:
        lines.append(f"- ({question.get('source')}) {question.get('title')}")
    return "\n".join(lines) or "(none found)"


async def generate_enrichment(blueprint_id: str) -> bool:
    """Generate + store playbook and 5-point validation for one blueprint.

    Returns True when the blueprint ends up enriched. Safe to call
    concurrently — a short cache lock deduplicates work.
    """
    if not settings.llm_api_key:
        return False

    lock_key = cache.hash_key("enrich-lock", blueprint_id)
    if await cache.get_json(lock_key):
        return False
    await cache.set_json(lock_key, True, ttl_seconds=180)

    db = get_db()
    rows = (
        db.table("blueprints")
        .select("id, title, human_problem, expired_logic, playbook, validation, embedding")
        .eq("id", blueprint_id)
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        return False
    blueprint = rows[0]
    if blueprint.get("playbook") and blueprint.get("validation"):
        return True

    # Evidence: corpus matches (vector) + live community questions.
    matches: list[dict] = []
    embedding = blueprint.get("embedding")
    if isinstance(embedding, str):  # supabase returns vectors as strings
        embedding = None
    if embedding is None:
        embedding = await llm.embed(blueprint["human_problem"])
    if embedding is not None:
        matches = community.match_posts(db, embedding)
    try:
        signals = await demand.gather_demand_signals(blueprint["title"])
    except Exception:
        signals = {"questions": [], "score": None}

    update: dict = {}

    if not blueprint.get("playbook"):
        try:
            raw = await llm.chat(
                settings.coder_model,
                _SYSTEM,
                _USER_TEMPLATE.format(
                    title=blueprint["title"],
                    human_problem=blueprint["human_problem"][:900],
                    expired_logic=blueprint["expired_logic"][:600],
                    evidence=_format_evidence(matches, signals["questions"]),
                ),
                max_tokens=1600,
                temperature=0.4,
            )
            playbook = parse_playbook_json(raw)
            if playbook:
                update["playbook"] = playbook
        except Exception:
            pass

    if not blueprint.get("validation"):
        idea = f"{blueprint['title']}. {blueprint['human_problem'][:600]}"
        validation = await framework.analyze_idea(idea, [], signals["questions"])
        if validation:
            update["validation"] = validation
            update["validation_score"] = validation["overall_score"]

    if update:
        db.table("blueprints").update(update).eq("id", blueprint_id).execute()
    return bool(update) or bool(blueprint.get("playbook"))
