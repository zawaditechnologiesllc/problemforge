"""Account: profile + usage, saved blueprints, and Pro API key management."""

import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import current_user_required
from ..db import get_db
from ..tiers import tier_config

router = APIRouter(prefix="/api/v1/account", tags=["account"])


@router.get("/me")
async def me(user: dict = Depends(current_user_required)):
    profile = user["profile"]
    limits = tier_config(profile["tier"])
    return {
        "id": profile["id"],
        "email": profile.get("email"),
        "tier": profile["tier"],
        "tier_name": limits["name"],
        "is_admin": bool(profile.get("is_admin")),
        "has_billing": bool(profile.get("stripe_customer_id")),
        "usage": {
            "searches_used": profile.get("monthly_search_count") or 0,
            "searches_limit": limits["searches_per_month"],
            "validations_used": profile.get("monthly_validate_count") or 0,
            "validations_limit": limits["validations_per_month"],
            "api_requests_used": profile.get("monthly_api_count") or 0,
            "api_requests_limit": limits["api_requests_per_month"],
            "reset_at": profile.get("usage_reset_at"),
        },
        "features": {
            "prompts_unlocked": limits["prompts_unlocked"],
            "api_access": limits["api_access"],
            "export": limits["export"],
            "priority_support": limits["priority_support"],
        },
    }


@router.get("/saved")
async def saved_blueprints(user: dict = Depends(current_user_required)):
    db = get_db()
    saved = (
        db.table("saved_blueprints")
        .select("blueprint_id, created_at")
        .eq("user_id", user["user_id"])
        .order("created_at", desc=True)
        .execute()
        .data
    )
    if not saved:
        return {"items": []}
    ids = [row["blueprint_id"] for row in saved]
    blueprints = (
        db.table("blueprints")
        .select(
            "id, title, domain, patent_number, human_problem, expired_logic, "
            "buildability_score, demand_signal_score, created_at"
        )
        .in_("id", ids)
        .execute()
        .data
    )
    order = {bp_id: index for index, bp_id in enumerate(ids)}
    blueprints.sort(key=lambda b: order.get(b["id"], 99))
    return {"items": blueprints}


class CreateKeyRequest(BaseModel):
    name: str = Field(default="default", max_length=60)


@router.get("/api-keys")
async def list_api_keys(user: dict = Depends(current_user_required)):
    rows = (
        get_db()
        .table("api_keys")
        .select("id, name, key_prefix, created_at, last_used_at, revoked_at")
        .eq("user_id", user["user_id"])
        .order("created_at", desc=True)
        .execute()
        .data
    )
    return {"items": rows}


@router.post("/api-keys")
async def create_api_key(
    body: CreateKeyRequest, user: dict = Depends(current_user_required)
):
    if not tier_config(user["profile"]["tier"])["api_access"]:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "upgrade_required",
                "message": "API keys are available on the Pro and Enterprise plans.",
            },
        )
    secret = f"pf_live_{secrets.token_urlsafe(24)}"
    get_db().table("api_keys").insert(
        {
            "user_id": user["user_id"],
            "name": body.name or "default",
            "key_prefix": secret[:12],
            "key_hash": hashlib.sha256(secret.encode()).hexdigest(),
        }
    ).execute()
    # The plaintext key is returned exactly once and never stored.
    return {"key": secret}


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str, user: dict = Depends(current_user_required)):
    get_db().table("api_keys").update(
        {"revoked_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", key_id).eq("user_id", user["user_id"]).execute()
    return {"revoked": True}
