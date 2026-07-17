"""Production middleware: per-IP rate limiting and security headers.

The rate limiter is an in-memory sliding window — appropriate for a
single-instance Render deployment. When scaling to multiple instances, move
to a shared store (Redis/Upstash); the tier-based monthly quotas in
services/usage.py are already database-backed and multi-instance safe.
"""

import time
from collections import deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_EXEMPT_PATHS = {"/healthz", "/", "/docs", "/openapi.json", "/redoc"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int = 120, window_seconds: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window_seconds
        self.hits: dict[str, deque] = {}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _EXEMPT_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = self.hits.setdefault(ip, deque())
        while bucket and now - bucket[0] > self.window:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": {
                        "code": "rate_limited",
                        "message": "Too many requests — slow down and retry shortly.",
                    }
                },
                headers={"Retry-After": str(self.window)},
            )
        bucket.append(now)

        # Bound memory: prune idle IPs occasionally.
        if len(self.hits) > 10000:
            self.hits = {
                key: value
                for key, value in self.hits.items()
                if value and now - value[-1] < self.window
            }
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
        )
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        return response
