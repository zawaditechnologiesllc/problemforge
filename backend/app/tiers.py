"""Tier definitions and limits. `None` means unlimited.

Enforcement is always server-side. Ladder calibrated against comparable
data/search API products (e.g. SerpApi: $25/1k, $75/5k, $150/15k searches);
ProblemForge is a discovery library, so limits are more generous per dollar.
"""

TIERS: dict[str, dict] = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "searches_per_month": 50,
        "validations_per_month": 5,
        "api_requests_per_month": 0,
        "prompts_unlocked": False,
        "api_access": False,
        "export": False,
        "priority_support": False,
    },
    "builder": {
        "name": "Builder",
        "price_monthly": 19,
        "searches_per_month": 500,
        "validations_per_month": 100,
        "api_requests_per_month": 0,
        "prompts_unlocked": True,
        "api_access": False,
        "export": False,
        "priority_support": False,
    },
    "pro": {
        "name": "Pro",
        "price_monthly": 49,
        "searches_per_month": 2500,
        "validations_per_month": 500,
        "api_requests_per_month": 5000,
        "prompts_unlocked": True,
        "api_access": True,
        "export": False,
        "priority_support": False,
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 150,
        "searches_per_month": None,      # unlimited
        "validations_per_month": None,   # unlimited
        "api_requests_per_month": None,  # unlimited API calls
        "prompts_unlocked": True,
        "api_access": True,
        "export": True,                  # bulk data export
        "priority_support": True,
    },
}


def tier_config(tier: str) -> dict:
    return TIERS.get(tier, TIERS["free"])
