"""Admin panel API + public site settings.

Admin access is a database flag (profiles.is_admin) — no hardcoded emails or
secret URLs. Grant it in SQL after the operator signs up:
  update public.profiles set is_admin = true where email = '...';
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import current_user_required
from ..db import get_db
from ..services.active import run_active_ingestion
from ..services.community import run_community_ingestion
from ..services.ingestion import backfill_embeddings, run_ingestion
from ..services.playbook import generate_enrichment

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
public_router = APIRouter(prefix="/api/v1", tags=["site"])

FOOTER_DEFAULTS = {
    "company_name": "Zawadi Technologies LLC",
    "product_name": "ProblemForge",
    "tagline": "Validated startup problems mined from expired, public-domain patents across 20 regions.",
    "address": "",
    "contact_email": "",
    "links": [],
}


async def require_admin(user: dict = Depends(current_user_required)) -> dict:
    if not user["profile"].get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ---------------------------------------------------------------------------
# Public: site settings (footer content etc. — public site chrome, not secrets)
# ---------------------------------------------------------------------------
@public_router.get("/site-settings")
async def get_site_settings():
    rows = (
        get_db()
        .table("site_settings")
        .select("key, value")
        .eq("key", "footer")
        .limit(1)
        .execute()
        .data
    )
    footer = {**FOOTER_DEFAULTS, **((rows[0]["value"] or {}) if rows else {})}
    return {"footer": footer}


class FooterSettings(BaseModel):
    company_name: str = Field(min_length=1, max_length=120)
    product_name: str = Field(min_length=1, max_length=80)
    tagline: str = Field(default="", max_length=300)
    address: str = Field(default="", max_length=300)
    # empty string allowed; otherwise must look like an email address
    contact_email: str = Field(
        default="", max_length=200, pattern=r"^$|^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )
    links: list[dict] = Field(default_factory=list, max_length=10)


@router.put("/settings/footer")
async def save_footer(body: FooterSettings, admin: dict = Depends(require_admin)):
    links = [
        {"label": str(link.get("label", ""))[:60], "url": str(link.get("url", ""))[:300]}
        for link in body.links
        if link.get("label") and link.get("url")
    ]
    value = {
        "company_name": body.company_name,
        "product_name": body.product_name,
        "tagline": body.tagline,
        "address": body.address,
        "contact_email": body.contact_email,
        "links": links,
    }
    get_db().table("site_settings").upsert(
        {
            "key": "footer",
            "value": value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()
    return {"footer": value}


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
def _count(table: str, **filters) -> int:
    query = get_db().table(table).select("id", count="exact").limit(1)
    for column, value in filters.items():
        query = query.eq(column, value)
    return query.execute().count or 0


@router.get("/overview")
async def overview(admin: dict = Depends(require_admin)):
    db = get_db()
    tiers = {}
    for tier in ("free", "builder", "pro", "enterprise"):
        tiers[tier] = _count("profiles", tier=tier)
    month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    events = (
        db.table("usage_events")
        .select("event_type")
        .gte("created_at", month_ago)
        .limit(10000)
        .execute()
        .data
    )
    events_by_type: dict[str, int] = {}
    for event in events:
        events_by_type[event["event_type"]] = events_by_type.get(event["event_type"], 0) + 1
    fto = {}
    for status in ("pending_payment", "queued", "processing", "ready", "failed"):
        fto[status] = _count("fto_reports", status=status)
    return {
        "users": {"total": sum(tiers.values()), "by_tier": tiers},
        "blueprints": {
            "public": _count("blueprints", is_public=True),
            "hidden": _count("blueprints", is_public=False),
            "enriched": db.table("blueprints").select("id", count="exact")
            .not_.is_("playbook", "null").limit(1).execute().count or 0,
        },
        "raw_patents": _count("raw_patents"),
        "community_posts": _count("community_posts"),
        "active_patents": _count("active_patents"),
        "fto_reports": fto,
        "usage_last_30d": events_by_type,
    }


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
@router.get("/users")
async def list_users(
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
    admin: dict = Depends(require_admin),
):
    query = (
        get_db()
        .table("profiles")
        .select(
            "id, email, tier, is_admin, monthly_search_count, monthly_validate_count, "
            "monthly_api_count, stripe_customer_id, created_at",
            count="exact",
        )
        .order("created_at", desc=True)
        .range(offset, offset + min(limit, 100) - 1)
    )
    if q:
        query = query.ilike("email", f"*{q.replace('%', '').replace(',', '')}*")
    result = query.execute()
    return {"items": result.data, "total": result.count or 0}


class UserUpdate(BaseModel):
    tier: str | None = Field(default=None, pattern="^(free|builder|pro|enterprise)$")
    is_admin: bool | None = None


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str, body: UserUpdate, admin: dict = Depends(require_admin)
):
    update: dict = {}
    if body.tier is not None:
        update["tier"] = body.tier
    if body.is_admin is not None:
        if user_id == admin["user_id"] and body.is_admin is False:
            raise HTTPException(status_code=400, detail="You cannot remove your own admin access")
        update["is_admin"] = body.is_admin
    if not update:
        raise HTTPException(status_code=400, detail="Nothing to update")
    rows = get_db().table("profiles").update(update).eq("id", user_id).execute().data
    if not rows:
        raise HTTPException(status_code=404, detail="User not found")
    return rows[0]


# ---------------------------------------------------------------------------
# Blueprints (including hidden)
# ---------------------------------------------------------------------------
@router.get("/blueprints")
async def admin_blueprints(
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
    admin: dict = Depends(require_admin),
):
    query = (
        get_db()
        .table("blueprints")
        .select(
            "id, title, domain, patent_number, buildability_score, demand_signal_score, "
            "validation_score, is_public, created_at",
            count="exact",
        )
        .order("created_at", desc=True)
        .range(offset, offset + min(limit, 100) - 1)
    )
    if q:
        query = query.ilike("title", f"*{q.replace('%', '').replace(',', '')}*")
    result = query.execute()
    return {"items": result.data, "total": result.count or 0}


class BlueprintUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    domain: str | None = Field(default=None, pattern="^(software|mechanical|medical)$")
    human_problem: str | None = Field(default=None, min_length=10)
    expired_logic: str | None = Field(default=None, min_length=10)
    buildability_score: int | None = Field(default=None, ge=0, le=100)
    demand_signal_score: int | None = Field(default=None, ge=0, le=100)
    is_public: bool | None = None


@router.patch("/blueprints/{blueprint_id}")
async def update_blueprint(
    blueprint_id: str, body: BlueprintUpdate, admin: dict = Depends(require_admin)
):
    update = {k: v for k, v in body.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(status_code=400, detail="Nothing to update")
    rows = (
        get_db().table("blueprints").update(update).eq("id", blueprint_id).execute().data
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Blueprint not found")
    rows[0].pop("embedding", None)
    return rows[0]


@router.delete("/blueprints/{blueprint_id}")
async def delete_blueprint(blueprint_id: str, admin: dict = Depends(require_admin)):
    get_db().table("blueprints").delete().eq("id", blueprint_id).execute()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# FTO reports + ingestion runs (read-only monitoring)
# ---------------------------------------------------------------------------
@router.get("/fto-reports")
async def admin_fto_reports(limit: int = 50, admin: dict = Depends(require_admin)):
    rows = (
        get_db()
        .table("fto_reports")
        .select("id, user_id, patent_number, status, error, created_at, completed_at")
        .order("created_at", desc=True)
        .limit(min(limit, 100))
        .execute()
        .data
    )
    return {"items": rows}


@router.get("/ingestion-runs")
async def admin_ingestion_runs(limit: int = 50, admin: dict = Depends(require_admin)):
    rows = (
        get_db()
        .table("ingestion_runs")
        .select("*")
        .order("started_at", desc=True)
        .limit(min(limit, 100))
        .execute()
        .data
    )
    return {"items": rows}


# ---------------------------------------------------------------------------
# Operational tasks (run the workers on demand from the panel)
# ---------------------------------------------------------------------------
async def _enrich_batch(limit: int = 20) -> None:
    db = get_db()
    rows = (
        db.table("blueprints")
        .select("id")
        .is_("playbook", "null")
        .eq("is_public", True)
        .limit(limit)
        .execute()
        .data
    )
    for row in rows:
        await generate_enrichment(row["id"])


TASKS = {
    "ingest": run_ingestion,
    "ingest_active": run_active_ingestion,
    "ingest_community": run_community_ingestion,
    "backfill_embeddings": backfill_embeddings,
    "enrich_blueprints": _enrich_batch,
}


@router.post("/tasks/{task_name}")
async def run_task(
    task_name: str,
    background_tasks: BackgroundTasks,
    admin: dict = Depends(require_admin),
):
    task = TASKS.get(task_name)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown task. Available: {', '.join(sorted(TASKS))}",
        )
    background_tasks.add_task(task)
    return {"started": task_name}
