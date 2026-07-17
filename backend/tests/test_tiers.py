"""Sanity checks on the pricing ladder."""

from app.tiers import TIERS, tier_config


def test_all_tiers_present():
    assert set(TIERS) == {"free", "builder", "pro", "enterprise"}


def test_prices():
    assert TIERS["free"]["price_monthly"] == 0
    assert TIERS["builder"]["price_monthly"] == 19
    assert TIERS["pro"]["price_monthly"] == 49
    assert TIERS["enterprise"]["price_monthly"] == 150


def test_limits_scale_up_the_ladder():
    assert TIERS["free"]["searches_per_month"] < TIERS["builder"]["searches_per_month"]
    assert TIERS["builder"]["searches_per_month"] < TIERS["pro"]["searches_per_month"]
    assert TIERS["enterprise"]["searches_per_month"] is None  # unlimited
    assert TIERS["enterprise"]["api_requests_per_month"] is None  # unlimited API calls


def test_feature_gates():
    assert not TIERS["free"]["prompts_unlocked"]
    assert TIERS["builder"]["prompts_unlocked"]
    assert not TIERS["builder"]["api_access"]
    assert TIERS["pro"]["api_access"]
    assert not TIERS["pro"]["export"]
    assert TIERS["enterprise"]["export"]  # bulk data export is Enterprise
    assert TIERS["enterprise"]["priority_support"]


def test_unknown_tier_falls_back_to_free():
    assert tier_config("nonsense") == TIERS["free"]
