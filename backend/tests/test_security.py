"""Security smoke tests — run against the real ASGI app on every CI pass.

Covers the properties that must never regress: authentication gating, admin
authorization, security headers, CORS allow-listing, webhook signature
verification, input validation, and the per-IP rate limiter.
"""

import asyncio

import httpx
import pytest

from app.auth import current_user_required
from app.config import settings
from app.main import app
from app.routers.blueprints import _sanitize_query


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    )


def _get(path: str, **kwargs) -> httpx.Response:
    async def run():
        async with _client() as client:
            return await client.get(path, **kwargs)

    return asyncio.run(run())


def _post(path: str, **kwargs) -> httpx.Response:
    async def run():
        async with _client() as client:
            return await client.post(path, **kwargs)

    return asyncio.run(run())


# ---------------------------------------------------------------------------
# Authentication gating: protected endpoints must reject anonymous callers
# ---------------------------------------------------------------------------
PROTECTED_GETS = [
    "/api/v1/account/me",
    "/api/v1/account/saved",
    "/api/v1/account/api-keys",
    "/api/v1/blueprints/export",
    "/api/v1/fto/reports",
    "/api/v1/support/thread",
    "/api/v1/admin/overview",
    "/api/v1/admin/users",
    "/api/v1/admin/support/threads",
]


@pytest.mark.parametrize("path", PROTECTED_GETS)
def test_protected_endpoints_reject_anonymous(path):
    response = _get(path)
    assert response.status_code == 401, f"{path} must require auth"


def test_protected_writes_reject_anonymous():
    assert _post("/api/v1/billing/checkout", json={"plan": "builder"}).status_code == 401
    assert _post("/api/v1/fto/checkout", json={"patent_number": "US1234567A"}).status_code == 401
    assert _post("/api/v1/support/messages", json={"body": "hello"}).status_code == 401

    async def run_delete():
        async with _client() as client:
            return await client.delete("/api/v1/account")

    assert asyncio.run(run_delete()).status_code == 401


def test_admin_endpoints_reject_non_admin_users():
    # Simulate a signed-in but non-admin user via dependency override.
    app.dependency_overrides[current_user_required] = lambda: {
        "user_id": "user-1",
        "profile": {"id": "user-1", "tier": "pro", "is_admin": False},
        "via": "session",
    }
    try:
        assert _get("/api/v1/admin/overview").status_code == 403
        assert _get("/api/v1/admin/users").status_code == 403
        assert _post("/api/v1/admin/tasks/ingest").status_code == 403
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Transport security: headers and CORS
# ---------------------------------------------------------------------------
def test_security_headers_on_every_response():
    response = _get("/healthz")
    assert response.status_code == 200
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert "strict-transport-security" in response.headers
    assert "referrer-policy" in response.headers
    assert "permissions-policy" in response.headers


def test_cors_rejects_unknown_origins_and_allows_frontend():
    evil = _get("/healthz", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in evil.headers
    allowed = _get("/healthz", headers={"Origin": "http://localhost:3000"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:3000"


# ---------------------------------------------------------------------------
# Payments: webhook signature verification
# ---------------------------------------------------------------------------
def test_webhook_unconfigured_returns_503():
    response = _post("/api/v1/billing/webhook", content=b"{}")
    assert response.status_code == 503  # refuses to process without a secret


def test_webhook_rejects_bad_signature(monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_testsecret")
    response = _post(
        "/api/v1/billing/webhook",
        content=b'{"type": "checkout.session.completed"}',
        headers={"stripe-signature": "t=1,v1=forged"},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
def test_validator_rejects_bad_input():
    assert _post("/api/v1/validate", json={"idea": "short"}).status_code == 422
    assert _post("/api/v1/validate", json={"idea": "x" * 3000}).status_code == 422
    assert _post("/api/v1/validate", json={}).status_code == 422


def test_search_query_sanitizer_strips_filter_injection():
    # Characters that could break out of PostgREST or= filter syntax.
    assert "," not in _sanitize_query("a,b")
    assert "(" not in _sanitize_query("a(b")
    assert ")" not in _sanitize_query("a)b")
    assert "%" not in _sanitize_query("a%b")
    assert "\\" not in _sanitize_query("a\\b")
    assert len(_sanitize_query("x" * 500)) <= 200
    assert _sanitize_query("medical billing delays") == "medical billing delays"


def test_unknown_admin_task_is_rejected():
    app.dependency_overrides[current_user_required] = lambda: {
        "user_id": "admin-1",
        "profile": {"id": "admin-1", "tier": "pro", "is_admin": True},
        "via": "session",
    }
    try:
        response = _post("/api/v1/admin/tasks/os.system")
        assert response.status_code == 404  # only the fixed allow-list runs
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Rate limiting (kept last: it intentionally exhausts the per-IP budget)
# ---------------------------------------------------------------------------
def test_rate_limiter_kicks_in_under_burst():
    async def run():
        async with _client() as client:
            for attempt in range(130):
                response = await client.get("/api/v1/nonexistent")
                if response.status_code == 429:
                    assert response.headers.get("retry-after")
                    return attempt
        return None

    tripped_at = asyncio.run(run())
    assert tripped_at is not None, "burst of 130 requests must trip the limiter"


def test_healthz_exempt_from_rate_limit():
    # Even after the budget above is spent, health checks keep working.
    assert _get("/healthz").status_code == 200
