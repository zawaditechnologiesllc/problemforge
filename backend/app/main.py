"""ProblemForge API — FastAPI service deployed on Render.

Serves the user-facing REST API (/api/v1/*), Stripe webhooks (subscriptions +
one-time FTO reports), and shares its codebase with the ingestion cron worker
(worker/ingest.py).
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from .routers import account, admin, billing, blueprints, fto, validate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="ProblemForge API",
    version="1.1.0",
    description="Validated startup problems mined from expired patents.",
)

# Middleware runs in reverse registration order: CORS first, then rate
# limiting, then security headers on the way out.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, limit=120, window_seconds=60)

allowed_origins = {settings.frontend_url.rstrip("/"), "http://localhost:3000"}
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(allowed_origins),
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(blueprints.router)
app.include_router(validate.router)
app.include_router(billing.router)
app.include_router(account.router)
app.include_router(fto.router)
app.include_router(admin.router)
app.include_router(admin.public_router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {
        "service": "problemforge-api",
        "docs": "/docs",
        "health": "/healthz",
    }
