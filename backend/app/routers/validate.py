"""The Validator ("Collision Checker"): embed an idea, find expired prior art."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..auth import current_user_optional
from ..db import get_db
from ..services import llm
from ..services.usage import check_and_increment

router = APIRouter(prefix="/api/v1", tags=["validator"])

# Best-effort per-IP daily cap for anonymous validator use. Resets on restart,
# which is acceptable — signed-in usage is metered properly in Postgres.
_ANON_LIMIT_PER_DAY = 10
_anon_counts: dict[str, tuple[str, int]] = {}


class ValidateRequest(BaseModel):
    idea: str = Field(min_length=10, max_length=2000)


def _check_anon_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    today = date.today().isoformat()
    day, count = _anon_counts.get(ip, (today, 0))
    if day != today:
        day, count = today, 0
    if count >= _ANON_LIMIT_PER_DAY:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "limit_reached",
                "message": "Daily validator limit reached. Create a free account for more runs.",
            },
        )
    _anon_counts[ip] = (day, count + 1)


@router.post("/validate")
async def validate_idea(
    body: ValidateRequest,
    request: Request,
    user: dict | None = Depends(current_user_optional),
):
    if user:
        # API-key callers are metered per request as api_call at auth time.
        if user.get("via") != "api_key":
            check_and_increment(user, "validator_run")
    else:
        _check_anon_limit(request)

    db = get_db()
    method = "vector"
    matches: list[dict] = []

    embedding = None
    try:
        embedding = await llm.embed(body.idea)
    except Exception:
        embedding = None

    if embedding is not None:
        result = db.rpc(
            "match_blueprints",
            {"query_embedding": embedding, "match_count": 5},
        ).execute()
        matches = result.data or []

    if not matches:
        method = "text"
        result = db.rpc(
            "match_blueprints_text",
            {"query_text": body.idea[:500], "match_count": 5},
        ).execute()
        matches = result.data or []

    for match in matches:
        raw = match.get("similarity") or 0
        match["similarity"] = round(max(0.0, min(1.0, float(raw))), 4)

    matches = [m for m in matches if m["similarity"] > 0.01]
    return {"method": method, "matches": matches}
