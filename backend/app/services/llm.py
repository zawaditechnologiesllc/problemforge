"""Thin OpenAI-compatible LLM client.

The rest of the app never talks to a provider directly — switching models is a
one-line env change (TRANSLATOR_MODEL / CODER_MODEL / EMBEDDING_MODEL).
"""

import re

import httpx

from ..config import settings

TRANSLATION_SYSTEM = (
    "You are an expert product strategist and startup validator. Your job is "
    "to read complex, legally dense patent text and translate it into a highly "
    "scannable, actionable product blueprint for non-technical creators and AI "
    '"vibe coders."'
)

TRANSLATION_USER_TEMPLATE = """Analyze this expired patent and generate a clean, structured product blueprint.

DOMAIN: {domain}
TITLE: {title}
ABSTRACT: {abstract}

Respond STRICTLY in this Markdown format:

### THE HUMAN PROBLEM
[Real-world frustration this invention solves, in plain language, no legal jargon]

### THE EXPIRED CORE LOGIC
[The foundational logic/algorithm now free to copy]

### HOW A VIBE CODER BUILDS IT TODAY
[3-step technical execution plan using modern APIs — OpenAI, Whisper, Stripe,
Twilio, shadcn/ui, Supabase, etc. — that Cursor/Windsurf can execute]

### PROMPT FOR CURSOR / WINDSURF
[Ready-to-copy master prompt for building the MVP immediately]"""


async def chat(
    model: str, system: str, user: str, max_tokens: int = 3000, temperature: float = 0.4
) -> str:
    if not settings.llm_api_key:
        raise RuntimeError("LLM_API_KEY is not configured")
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{settings.llm_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def embed(text: str) -> list[float] | None:
    """Return a 1536-dim embedding, or None when no embeddings key is set."""
    if not settings.embeddings_api_key:
        return None
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.embeddings_base_url}/embeddings",
            headers={"Authorization": f"Bearer {settings.embeddings_api_key}"},
            json={"model": settings.embedding_model, "input": text[:8000]},
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]


def parse_blueprint_markdown(md: str) -> dict | None:
    """Split the four-section translation output into structured fields."""
    sections = {
        "human_problem": r"THE HUMAN PROBLEM",
        "expired_logic": r"THE EXPIRED CORE LOGIC",
        "build_plan": r"HOW A VIBE CODER BUILDS IT TODAY",
        "master_prompt": r"PROMPT FOR CURSOR\s*/\s*WINDSURF",
    }
    parts = re.split(r"^#{2,4}\s*", md, flags=re.MULTILINE)
    result: dict[str, str] = {}
    for part in parts:
        for field, header in sections.items():
            if re.match(header, part.strip(), flags=re.IGNORECASE):
                body = re.sub(header, "", part.strip(), count=1, flags=re.IGNORECASE)
                result[field] = body.strip().strip("[]").strip()
    if len(result) != 4 or not all(result.values()):
        return None
    return result


async def translate_patent(title: str, abstract: str, domain: str) -> dict | None:
    """Patent -> four-section blueprint via the bulk translator model."""
    md = await chat(
        settings.translator_model,
        TRANSLATION_SYSTEM,
        TRANSLATION_USER_TEMPLATE.format(
            domain=domain, title=title, abstract=abstract or "(no abstract available)"
        ),
    )
    return parse_blueprint_markdown(md)


async def classify_domain(title: str, abstract: str) -> str:
    """Classify a patent into one of the three product domains."""
    try:
        answer = await chat(
            settings.translator_model,
            "Classify patents. Reply with exactly one word: software, mechanical, or medical.",
            f"TITLE: {title}\nABSTRACT: {abstract or ''}",
            max_tokens=5,
            temperature=0,
        )
        word = answer.strip().lower()
        if word in ("software", "mechanical", "medical"):
            return word
    except Exception:
        pass
    return "software"
