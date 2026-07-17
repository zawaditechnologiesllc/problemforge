"""Public blueprint browsing/search + gated detail, copy, save, export."""

import csv
import io
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ..auth import current_user_optional, current_user_required
from ..db import get_db
from ..services.usage import check_and_increment, record_event
from ..tiers import tier_config

router = APIRouter(prefix="/api/v1/blueprints", tags=["blueprints"])

LIST_FIELDS = (
    "id, title, domain, patent_number, human_problem, expired_logic, "
    "buildability_score, demand_signal_score, public_domain_verified, created_at"
)

_SORTS = {
    "newest": ("created_at", True),
    "buildability": ("buildability_score", True),
    "demand": ("demand_signal_score", True),
}


def _sanitize_query(q: str) -> str:
    # Characters that would break PostgREST or= filter syntax.
    return re.sub(r"[,()\\%]", " ", q).strip()[:200]


@router.get("")
async def list_blueprints(
    q: str | None = None,
    domain: str | None = Query(None, pattern="^(software|mechanical|medical)$"),
    min_buildability: int | None = Query(None, ge=0, le=100),
    public_domain_only: bool = False,
    sort: str = Query("newest", pattern="^(newest|buildability|demand)$"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: dict | None = Depends(current_user_optional),
):
    db = get_db()

    if public_domain_only:
        # All data passes the ingestion gate; this filter narrows to rows whose
        # source status was re-verified. It's a paid-tier refinement.
        if user is None or not tier_config(user["profile"]["tier"])["prompts_unlocked"]:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "upgrade_required",
                    "message": "The verified Public Domain Only filter is available on paid plans.",
                },
            )

    query = db.table("blueprints").select(LIST_FIELDS, count="exact").eq(
        "is_public", True
    )
    if domain:
        query = query.eq("domain", domain)
    if min_buildability:
        query = query.gte("buildability_score", min_buildability)
    if public_domain_only:
        query = query.eq("public_domain_verified", True)
    if q:
        clean = _sanitize_query(q)
        if clean:
            query = query.or_(
                f"title.ilike.*{clean}*,"
                f"human_problem.ilike.*{clean}*,"
                f"expired_logic.ilike.*{clean}*"
            )

    column, desc = _SORTS[sort]
    query = query.order(column, desc=desc).range(offset, offset + limit - 1)
    result = query.execute()

    # Searches are metered for signed-in web sessions; API-key callers are
    # already metered per request as api_call, and anonymous browsing is fine
    # because everything valuable (prompts, build plans) is gated separately.
    if q and user and user.get("via") != "api_key":
        check_and_increment(user, "search")

    return {"items": result.data, "total": result.count or 0}


@router.get("/export")
async def export_blueprints(user: dict = Depends(current_user_required)):
    if not tier_config(user["profile"]["tier"])["export"]:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "upgrade_required",
                "message": "Bulk data export is available on the Enterprise plan.",
            },
        )
    rows = (
        get_db()
        .table("blueprints")
        .select(
            "patent_number, title, domain, human_problem, expired_logic, "
            "build_plan, master_prompt, buildability_score, demand_signal_score"
        )
        .eq("is_public", True)
        .execute()
        .data
    )
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()) if rows else [])
    writer.writeheader()
    writer.writerows(rows)
    record_event(user["user_id"], "export")
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=problemforge-blueprints.csv"},
    )


@router.get("/{blueprint_id}")
async def get_blueprint(
    blueprint_id: str, user: dict | None = Depends(current_user_optional)
):
    db = get_db()
    rows = (
        db.table("blueprints")
        .select("*")
        .eq("id", blueprint_id)
        .eq("is_public", True)
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    blueprint = rows[0]
    blueprint.pop("embedding", None)

    patent = None
    if blueprint.get("raw_patent_id"):
        praw = (
            db.table("raw_patents")
            .select("patent_number, filing_date, legal_status, source")
            .eq("id", blueprint["raw_patent_id"])
            .limit(1)
            .execute()
            .data
        )
        patent = praw[0] if praw else None

    unlocked = bool(
        user and tier_config(user["profile"]["tier"])["prompts_unlocked"]
    )
    if not unlocked:
        # Locked content never leaves the server for free/anonymous callers.
        blueprint["build_plan"] = None
        blueprint["master_prompt"] = None

    saved = False
    if user:
        saved = bool(
            db.table("saved_blueprints")
            .select("blueprint_id")
            .eq("user_id", user["user_id"])
            .eq("blueprint_id", blueprint_id)
            .limit(1)
            .execute()
            .data
        )

    return {**blueprint, "patent": patent, "locked": not unlocked, "saved": saved}


@router.get("/{blueprint_id}/related")
async def related_blueprints(blueprint_id: str):
    db = get_db()
    rows = (
        db.table("blueprints")
        .select("id, domain")
        .eq("id", blueprint_id)
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    related = (
        db.table("blueprints")
        .select(LIST_FIELDS)
        .eq("is_public", True)
        .eq("domain", rows[0]["domain"])
        .neq("id", blueprint_id)
        .order("buildability_score", desc=True)
        .limit(3)
        .execute()
        .data
    )
    return {"items": related}


@router.post("/{blueprint_id}/copy")
async def copy_master_prompt(
    blueprint_id: str, user: dict = Depends(current_user_required)
):
    if not tier_config(user["profile"]["tier"])["prompts_unlocked"]:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "upgrade_required",
                "message": "Master prompts are unlocked on the Builder and Pro plans.",
            },
        )
    rows = (
        get_db()
        .table("blueprints")
        .select("master_prompt")
        .eq("id", blueprint_id)
        .eq("is_public", True)
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    check_and_increment(user, "copy_prompt", blueprint_id)
    return {"master_prompt": rows[0]["master_prompt"]}


@router.post("/{blueprint_id}/save")
async def save_blueprint(
    blueprint_id: str, user: dict = Depends(current_user_required)
):
    get_db().table("saved_blueprints").upsert(
        {"user_id": user["user_id"], "blueprint_id": blueprint_id}
    ).execute()
    return {"saved": True}


@router.delete("/{blueprint_id}/save")
async def unsave_blueprint(
    blueprint_id: str, user: dict = Depends(current_user_required)
):
    get_db().table("saved_blueprints").delete().eq(
        "user_id", user["user_id"]
    ).eq("blueprint_id", blueprint_id).execute()
    return {"saved": False}
