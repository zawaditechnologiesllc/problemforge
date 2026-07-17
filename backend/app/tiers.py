"""Tier definitions and limits. Enforcement is always server-side."""

TIERS: dict[str, dict] = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "searches_per_month": 50,
        "validations_per_month": 5,
        "prompts_unlocked": False,
        "api_access": False,
        "export": False,
    },
    "builder": {
        "name": "Builder",
        "price_monthly": 19,
        "searches_per_month": 500,
        "validations_per_month": 100,
        "prompts_unlocked": True,
        "api_access": False,
        "export": False,
    },
    "pro": {
        "name": "Pro",
        "price_monthly": 49,
        "searches_per_month": 2000,
        "validations_per_month": 1000,
        "prompts_unlocked": True,
        "api_access": True,
        "export": True,
    },
}


def tier_config(tier: str) -> dict:
    return TIERS.get(tier, TIERS["free"])
