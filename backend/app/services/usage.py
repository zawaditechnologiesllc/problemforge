"""Server-side usage metering and tier limit enforcement."""

from fastapi import HTTPException

from ..db import get_db
from ..tiers import tier_config

_COUNTER_FIELD = {
    "search": "monthly_search_count",
    "validator_run": "monthly_validate_count",
}
_LIMIT_FIELD = {
    "search": "searches_per_month",
    "validator_run": "validations_per_month",
}


def check_and_increment(
    user: dict, event_type: str, blueprint_id: str | None = None
) -> None:
    """Raise 429 if the caller is at their monthly limit; otherwise count the event."""
    profile = user["profile"]
    limits = tier_config(profile["tier"])

    counter_field = _COUNTER_FIELD.get(event_type)
    if counter_field:
        limit = limits[_LIMIT_FIELD[event_type]]
        used = profile.get(counter_field) or 0
        if used >= limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "limit_reached",
                    "message": f"Monthly limit reached ({used}/{limit}). Upgrade for a higher limit.",
                    "limit": limit,
                },
            )
        db = get_db()
        db.table("profiles").update({counter_field: used + 1}).eq(
            "id", profile["id"]
        ).execute()
        profile[counter_field] = used + 1

    record_event(user["user_id"], event_type, blueprint_id)


def record_event(
    user_id: str | None, event_type: str, blueprint_id: str | None = None
) -> None:
    try:
        get_db().table("usage_events").insert(
            {
                "user_id": user_id,
                "event_type": event_type,
                "blueprint_id": blueprint_id,
            }
        ).execute()
    except Exception:
        # Metering must never take down the request path.
        pass
