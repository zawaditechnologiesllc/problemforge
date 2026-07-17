"""Freedom-to-Operate report endpoints ($99 one-time via Stripe Checkout)."""

import stripe
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from ..auth import current_user_required
from ..config import settings
from ..db import get_db
from ..services import fto
from ..services.usage import record_event

router = APIRouter(prefix="/api/v1/fto", tags=["fto"])


class FtoCheckoutRequest(BaseModel):
    patent_number: str | None = None
    blueprint_id: str | None = None


@router.post("/checkout")
async def create_fto_checkout(
    body: FtoCheckoutRequest, user: dict = Depends(current_user_required)
):
    if not settings.stripe_secret_key or not settings.stripe_price_fto:
        raise HTTPException(
            status_code=503, detail="FTO reports are not configured yet"
        )

    db = get_db()
    patent_number = body.patent_number
    blueprint_id = body.blueprint_id
    if blueprint_id and not patent_number:
        rows = (
            db.table("blueprints")
            .select("patent_number")
            .eq("id", blueprint_id)
            .limit(1)
            .execute()
            .data
        )
        if not rows or not rows[0].get("patent_number"):
            raise HTTPException(status_code=404, detail="Blueprint not found")
        patent_number = rows[0]["patent_number"]
    if not patent_number:
        raise HTTPException(status_code=400, detail="patent_number or blueprint_id required")

    normalized = fto.valid_patent_number(patent_number)
    if not normalized:
        raise HTTPException(
            status_code=400,
            detail="Invalid patent number — expected e.g. US7156808B2",
        )

    report = (
        db.table("fto_reports")
        .insert(
            {
                "user_id": user["user_id"],
                "patent_number": normalized,
                "blueprint_id": blueprint_id,
            }
        )
        .execute()
        .data[0]
    )

    stripe.api_key = settings.stripe_secret_key
    profile = user["profile"]
    params: dict = {
        "mode": "payment",
        "line_items": [{"price": settings.stripe_price_fto, "quantity": 1}],
        "success_url": f"{settings.frontend_url}/account?fto=success",
        "cancel_url": f"{settings.frontend_url}/account?fto=cancelled",
        "client_reference_id": user["user_id"],
        "metadata": {
            "kind": "fto",
            "fto_report_id": report["id"],
            "user_id": user["user_id"],
            "patent_number": normalized,
        },
    }
    if profile.get("stripe_customer_id"):
        params["customer"] = profile["stripe_customer_id"]
    elif profile.get("email"):
        params["customer_email"] = profile["email"]

    session = stripe.checkout.Session.create(**params)
    db.table("fto_reports").update({"stripe_session_id": session.id}).eq(
        "id", report["id"]
    ).execute()
    return {"url": session.url, "report_id": report["id"]}


@router.get("/reports")
async def list_reports(user: dict = Depends(current_user_required)):
    rows = (
        get_db()
        .table("fto_reports")
        .select("id, patent_number, blueprint_id, status, error, created_at, completed_at")
        .eq("user_id", user["user_id"])
        .order("created_at", desc=True)
        .limit(50)
        .execute()
        .data
    )
    return {"items": rows}


@router.get("/reports/{report_id}/download")
async def download_report(report_id: str, user: dict = Depends(current_user_required)):
    rows = (
        get_db()
        .table("fto_reports")
        .select("*")
        .eq("id", report_id)
        .eq("user_id", user["user_id"])
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Report not found")
    report = rows[0]
    if report["status"] != "ready" or not report.get("report_path"):
        raise HTTPException(status_code=409, detail=f"Report is {report['status']}")
    return {"url": fto.signed_download_url(report)}


@router.post("/reports/{report_id}/retry")
async def retry_report(
    report_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(current_user_required),
):
    rows = (
        get_db()
        .table("fto_reports")
        .select("id, status")
        .eq("id", report_id)
        .eq("user_id", user["user_id"])
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Report not found")
    if rows[0]["status"] != "failed":
        raise HTTPException(status_code=409, detail="Only failed reports can be retried")
    record_event(user["user_id"], "fto_report", None)
    background_tasks.add_task(fto.generate_report, report_id)
    return {"queued": True}
