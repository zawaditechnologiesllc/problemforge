"""Support chat: site widget (signed-in users) -> admin panel Messages.

One open thread per user; messages append to it. Admin replies trigger a
best-effort email to the user; new user messages notify the site contact
email (set in Admin -> Site Footer). All email is optional — chat works
fully without Resend configured.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import current_user_required
from ..config import settings
from ..db import get_db
from ..services import email as email_service
from .admin import FOOTER_DEFAULTS, require_admin

router = APIRouter(prefix="/api/v1/support", tags=["support"])
admin_router = APIRouter(prefix="/api/v1/admin/support", tags=["admin"])

MAX_MESSAGES_PER_DAY = 50


class MessageBody(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


def _open_thread_for(db, user_id: str) -> dict | None:
    rows = (
        db.table("support_threads")
        .select("*")
        .eq("user_id", user_id)
        .eq("status", "open")
        .order("last_message_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


def _thread_messages(db, thread_id: str) -> list[dict]:
    return (
        db.table("support_messages")
        .select("id, sender, body, created_at, read_at")
        .eq("thread_id", thread_id)
        .order("created_at")
        .limit(200)
        .execute()
        .data
    )


def _contact_email(db) -> str:
    rows = (
        db.table("site_settings").select("value").eq("key", "footer").limit(1).execute().data
    )
    footer = {**FOOTER_DEFAULTS, **((rows[0]["value"] or {}) if rows else {})}
    return footer.get("contact_email") or ""


# ---------------------------------------------------------------------------
# User side (the site widget)
# ---------------------------------------------------------------------------
@router.get("/thread")
async def get_thread(
    mark_read: bool = Query(False),
    user: dict = Depends(current_user_required),
):
    db = get_db()
    thread = _open_thread_for(db, user["user_id"])
    if not thread:
        return {"thread": None, "messages": [], "unread": 0}
    messages = _thread_messages(db, thread["id"])
    unread = sum(1 for m in messages if m["sender"] == "admin" and not m["read_at"])
    if mark_read and unread:
        db.table("support_messages").update(
            {"read_at": datetime.now(timezone.utc).isoformat()}
        ).eq("thread_id", thread["id"]).eq("sender", "admin").is_(
            "read_at", "null"
        ).execute()
        unread = 0
    return {
        "thread": {"id": thread["id"], "status": thread["status"]},
        "messages": messages,
        "unread": unread,
    }


@router.post("/messages")
async def send_message(body: MessageBody, user: dict = Depends(current_user_required)):
    db = get_db()
    day_ago = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    thread = _open_thread_for(db, user["user_id"])
    if thread:
        recent = (
            db.table("support_messages")
            .select("id", count="exact")
            .eq("thread_id", thread["id"])
            .eq("sender", "user")
            .gte("created_at", day_ago)
            .limit(1)
            .execute()
            .count
            or 0
        )
        if recent >= MAX_MESSAGES_PER_DAY:
            raise HTTPException(
                status_code=429,
                detail={"code": "limit_reached", "message": "Daily message limit reached — we'll reply to your existing messages soon."},
            )
    else:
        thread = (
            db.table("support_threads")
            .insert(
                {
                    "user_id": user["user_id"],
                    "subject": body.body[:80],
                }
            )
            .execute()
            .data[0]
        )

    message = (
        db.table("support_messages")
        .insert({"thread_id": thread["id"], "sender": "user", "body": body.body})
        .execute()
        .data[0]
    )
    db.table("support_threads").update(
        {"last_message_at": datetime.now(timezone.utc).isoformat(), "status": "open"}
    ).eq("id", thread["id"]).execute()

    # Notify the operator inbox (best-effort, only if configured).
    contact = _contact_email(db)
    if contact:
        await email_service.send_email(
            contact,
            "New support message on ProblemForge",
            "New support message",
            [
                f"From: {user['profile'].get('email') or user['user_id']}",
                f"Message: {body.body[:500]}",
            ],
            cta=("Open the admin panel", f"{settings.frontend_url}/admin"),
        )
    return {"message": message, "thread_id": thread["id"]}


# ---------------------------------------------------------------------------
# Admin side (Messages tab)
# ---------------------------------------------------------------------------
@admin_router.get("/threads")
async def admin_threads(
    status: str = Query("open", pattern="^(open|closed|all)$"),
    admin: dict = Depends(require_admin),
):
    db = get_db()
    query = (
        db.table("support_threads")
        .select("id, user_id, subject, status, created_at, last_message_at")
        .order("last_message_at", desc=True)
        .limit(100)
    )
    if status != "all":
        query = query.eq("status", status)
    threads = query.execute().data

    # Attach requester email + unread count per thread.
    for thread in threads:
        profile = (
            db.table("profiles")
            .select("email, tier")
            .eq("id", thread["user_id"])
            .limit(1)
            .execute()
            .data
        )
        thread["email"] = profile[0]["email"] if profile else None
        thread["tier"] = profile[0]["tier"] if profile else "free"
        thread["unread"] = (
            db.table("support_messages")
            .select("id", count="exact")
            .eq("thread_id", thread["id"])
            .eq("sender", "user")
            .is_("read_at", "null")
            .limit(1)
            .execute()
            .count
            or 0
        )
    return {"items": threads}


@admin_router.get("/threads/{thread_id}")
async def admin_thread(thread_id: str, admin: dict = Depends(require_admin)):
    db = get_db()
    rows = (
        db.table("support_threads").select("*").eq("id", thread_id).limit(1).execute().data
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Thread not found")
    messages = _thread_messages(db, thread_id)
    # Opening a thread marks the user's messages as read.
    db.table("support_messages").update(
        {"read_at": datetime.now(timezone.utc).isoformat()}
    ).eq("thread_id", thread_id).eq("sender", "user").is_("read_at", "null").execute()
    return {"thread": rows[0], "messages": messages}


@admin_router.post("/threads/{thread_id}/reply")
async def admin_reply(
    thread_id: str, body: MessageBody, admin: dict = Depends(require_admin)
):
    db = get_db()
    rows = (
        db.table("support_threads").select("*").eq("id", thread_id).limit(1).execute().data
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Thread not found")
    thread = rows[0]
    message = (
        db.table("support_messages")
        .insert({"thread_id": thread_id, "sender": "admin", "body": body.body})
        .execute()
        .data[0]
    )
    db.table("support_threads").update(
        {"last_message_at": datetime.now(timezone.utc).isoformat(), "status": "open"}
    ).eq("id", thread_id).execute()

    # Best-effort email so the user knows a reply is waiting.
    profile = (
        db.table("profiles").select("email").eq("id", thread["user_id"]).limit(1).execute().data
    )
    if profile and profile[0].get("email"):
        await email_service.send_email(
            profile[0]["email"],
            "Support replied — ProblemForge",
            "You have a reply from support",
            [
                "Our team replied to your support message:",
                body.body[:500],
            ],
            cta=("Open the chat", settings.frontend_url),
        )
    return {"message": message}


class ThreadStatus(BaseModel):
    status: str = Field(pattern="^(open|closed)$")


@admin_router.patch("/threads/{thread_id}")
async def admin_set_status(
    thread_id: str, body: ThreadStatus, admin: dict = Depends(require_admin)
):
    rows = (
        get_db()
        .table("support_threads")
        .update({"status": body.status})
        .eq("id", thread_id)
        .execute()
        .data
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Thread not found")
    return rows[0]
