"""Authentication: Supabase JWT (web sessions) and API keys (Pro tier)."""

import hashlib
from datetime import datetime, timedelta, timezone

import httpx
import jwt
from fastapi import Depends, HTTPException, Request

from .config import settings
from .db import get_db
from .tiers import tier_config


def _verify_jwt_local(token: str) -> str | None:
    """Verify with the legacy HS256 project secret, if configured."""
    if not settings.supabase_jwt_secret:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


def _verify_jwt_remote(token: str) -> str | None:
    """Fallback: ask Supabase Auth who this token belongs to.

    Works regardless of the project's signing-key setup (HS256 or asymmetric).
    """
    if not settings.supabase_url or not settings.supabase_anon_key:
        return None
    try:
        resp = httpx.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={
                "apikey": settings.supabase_anon_key,
                "Authorization": f"Bearer {token}",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("id")
    except httpx.HTTPError:
        pass
    return None


def _user_id_from_token(token: str) -> str | None:
    return _verify_jwt_local(token) or _verify_jwt_remote(token)


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _user_id_from_api_key(key: str) -> str | None:
    db = get_db()
    rows = (
        db.table("api_keys")
        .select("id, user_id, revoked_at")
        .eq("key_hash", _hash_key(key))
        .limit(1)
        .execute()
        .data
    )
    if not rows or rows[0].get("revoked_at"):
        return None
    db.table("api_keys").update(
        {"last_used_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", rows[0]["id"]).execute()
    return rows[0]["user_id"]


def _load_profile(user_id: str) -> dict:
    db = get_db()
    rows = db.table("profiles").select("*").eq("id", user_id).limit(1).execute().data
    if rows:
        profile = rows[0]
    else:
        # Users created before the profile trigger existed.
        profile = (
            db.table("profiles").upsert({"id": user_id}).execute().data[0]
        )
    return _maybe_reset_usage(profile)


def _maybe_reset_usage(profile: dict) -> dict:
    """Roll the monthly counters if the 30-day window has elapsed."""
    reset_at_raw = profile.get("usage_reset_at")
    try:
        reset_at = datetime.fromisoformat(str(reset_at_raw).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        reset_at = datetime.now(timezone.utc)
    if datetime.now(timezone.utc) - reset_at >= timedelta(days=30):
        updated = (
            get_db()
            .table("profiles")
            .update(
                {
                    "monthly_search_count": 0,
                    "monthly_validate_count": 0,
                    "usage_reset_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", profile["id"])
            .execute()
            .data
        )
        if updated:
            return updated[0]
    return profile


async def current_user_optional(request: Request) -> dict | None:
    """Resolve the caller from a Bearer token or X-API-Key. None if anonymous."""
    api_key = request.headers.get("x-api-key")
    if api_key:
        user_id = _user_id_from_api_key(api_key)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid API key")
        profile = _load_profile(user_id)
        if not tier_config(profile["tier"])["api_access"]:
            raise HTTPException(
                status_code=403, detail="API access requires the Pro plan"
            )
        return {"user_id": user_id, "profile": profile, "via": "api_key"}

    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        user_id = _user_id_from_token(token)
        if user_id:
            return {
                "user_id": user_id,
                "profile": _load_profile(user_id),
                "via": "session",
            }
    return None


async def current_user_required(
    user: dict | None = Depends(current_user_optional),
) -> dict:
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user
