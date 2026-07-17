"""Stripe subscriptions: Checkout, Customer Portal, and webhooks.

Two paid plans — Builder ($19/mo) and Pro ($49/mo) — mapped to Stripe Price IDs
via STRIPE_PRICE_BUILDER / STRIPE_PRICE_PRO. Webhooks are the single source of
truth for profiles.tier.
"""

import stripe
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel

from ..auth import current_user_required
from ..config import settings
from ..db import get_db
from ..services import fto
from ..services.usage import record_event

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan: str  # 'builder' | 'pro' | 'enterprise'


def _price_for_plan(plan: str) -> str:
    prices = {
        "builder": settings.stripe_price_builder,
        "pro": settings.stripe_price_pro,
        "enterprise": settings.stripe_price_enterprise,
    }
    price = prices.get(plan)
    if not price:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {plan}")
    return price


def _tier_for_price(price_id: str) -> str | None:
    if price_id == settings.stripe_price_builder:
        return "builder"
    if price_id == settings.stripe_price_pro:
        return "pro"
    if price_id == settings.stripe_price_enterprise:
        return "enterprise"
    return None


@router.post("/checkout")
async def create_checkout(
    body: CheckoutRequest, user: dict = Depends(current_user_required)
):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing is not configured yet")
    stripe.api_key = settings.stripe_secret_key
    profile = user["profile"]

    params: dict = {
        "mode": "subscription",
        "line_items": [{"price": _price_for_plan(body.plan), "quantity": 1}],
        "success_url": f"{settings.frontend_url}/account?checkout=success",
        "cancel_url": f"{settings.frontend_url}/pricing?checkout=cancelled",
        "client_reference_id": user["user_id"],
        "metadata": {"user_id": user["user_id"], "plan": body.plan},
        "subscription_data": {"metadata": {"user_id": user["user_id"]}},
        "allow_promotion_codes": True,
    }
    if profile.get("stripe_customer_id"):
        params["customer"] = profile["stripe_customer_id"]
    elif profile.get("email"):
        params["customer_email"] = profile["email"]

    session = stripe.checkout.Session.create(**params)
    return {"url": session.url}


@router.post("/portal")
async def create_portal(user: dict = Depends(current_user_required)):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Billing is not configured yet")
    stripe.api_key = settings.stripe_secret_key
    customer_id = user["profile"].get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=400, detail="No billing account yet")
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{settings.frontend_url}/account",
    )
    return {"url": session.url}


def _set_tier(user_id: str, tier: str, customer_id: str | None = None,
              subscription_id: str | None = None) -> None:
    update: dict = {"tier": tier}
    if customer_id:
        update["stripe_customer_id"] = customer_id
    if subscription_id is not None:
        update["stripe_subscription_id"] = subscription_id or None
    get_db().table("profiles").update(update).eq("id", user_id).execute()


def _user_id_for_customer(customer_id: str) -> str | None:
    rows = (
        get_db()
        .table("profiles")
        .select("id")
        .eq("stripe_customer_id", customer_id)
        .limit(1)
        .execute()
        .data
    )
    return rows[0]["id"] if rows else None


@router.post("/webhook")
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")
    stripe.api_key = settings.stripe_secret_key
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    obj = event["data"]["object"]

    if event["type"] == "checkout.session.completed":
        metadata = obj.get("metadata") or {}
        user_id = obj.get("client_reference_id") or metadata.get("user_id")

        # One-time Freedom-to-Operate report payment -> queue async generation.
        if metadata.get("kind") == "fto" and metadata.get("fto_report_id"):
            report_id = metadata["fto_report_id"]
            updated = (
                get_db()
                .table("fto_reports")
                .update({"status": "queued"})
                .eq("id", report_id)
                .eq("status", "pending_payment")  # idempotent on webhook retries
                .execute()
                .data
            )
            if updated:
                if user_id and obj.get("customer"):
                    get_db().table("profiles").update(
                        {"stripe_customer_id": obj["customer"]}
                    ).eq("id", user_id).is_("stripe_customer_id", "null").execute()
                record_event(user_id, "fto_report")
                background_tasks.add_task(fto.generate_report, report_id)
            return {"received": True}

        subscription_id = obj.get("subscription")
        if user_id and subscription_id:
            subscription = stripe.Subscription.retrieve(subscription_id)
            price_id = subscription["items"]["data"][0]["price"]["id"]
            tier = _tier_for_price(price_id)
            if tier:
                _set_tier(user_id, tier, obj.get("customer"), subscription_id)

    elif event["type"] == "customer.subscription.updated":
        user_id = (obj.get("metadata") or {}).get("user_id") or _user_id_for_customer(
            obj.get("customer", "")
        )
        if user_id:
            price_id = obj["items"]["data"][0]["price"]["id"]
            tier = _tier_for_price(price_id)
            if obj.get("status") in ("active", "trialing") and tier:
                _set_tier(user_id, tier, obj.get("customer"), obj.get("id"))
            elif obj.get("status") in ("canceled", "unpaid", "incomplete_expired"):
                _set_tier(user_id, "free", obj.get("customer"), "")

    elif event["type"] == "customer.subscription.deleted":
        user_id = (obj.get("metadata") or {}).get("user_id") or _user_id_for_customer(
            obj.get("customer", "")
        )
        if user_id:
            _set_tier(user_id, "free", obj.get("customer"), "")

    return {"received": True}
