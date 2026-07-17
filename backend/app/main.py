"""ProblemForge API — FastAPI service deployed on Render.

Serves the user-facing REST API (/api/v1/*), Stripe webhooks, and shares its
codebase with the ingestion cron worker (worker/ingest.py).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import account, billing, blueprints, validate

app = FastAPI(
    title="ProblemForge API",
    version="1.0.0",
    description="Validated startup problems mined from expired patents.",
)

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
