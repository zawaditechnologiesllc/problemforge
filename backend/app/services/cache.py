"""Cost-saving cache layer.

Backends, chosen automatically:
- Redis when REDIS_URL is set (recommended: Upstash Redis serverless free
  tier, or Render Key Value — both give a rediss:// URL). Survives restarts
  and is shared across instances.
- In-process TTL cache otherwise, so caching always works in development and
  single-instance deployments with zero setup.

What gets cached (all misses are safe — callers treat cache as best-effort):
- Embeddings (7 days): identical text always embeds identically, so every
  repeat Validator run or re-ingested phrase is a free API call saved.
- Validation framework analyses (24h): repeat/near-duplicate idea checks
  skip the LLM entirely.
- Community demand signals (24h): keeps scraping polite and cheap.
"""

import hashlib
import json
import time
from typing import Any

from ..config import settings

_memory: dict[str, tuple[float, str]] = {}
_MEMORY_MAX_KEYS = 5000
_redis = None
_redis_failed = False


def hash_key(prefix: str, text: str) -> str:
    return f"pf:{prefix}:{hashlib.sha256(text.encode()).hexdigest()}"


async def _get_redis():
    global _redis, _redis_failed
    if not settings.redis_url or _redis_failed:
        return None
    if _redis is None:
        try:
            import redis.asyncio as aioredis

            _redis = aioredis.from_url(
                settings.redis_url, decode_responses=True, socket_timeout=3
            )
        except Exception:
            _redis_failed = True
            return None
    return _redis


async def get_json(key: str) -> Any | None:
    client = await _get_redis()
    if client is not None:
        try:
            raw = await client.get(key)
            return json.loads(raw) if raw else None
        except Exception:
            pass  # fall through to memory
    entry = _memory.get(key)
    if entry and entry[0] > time.monotonic():
        return json.loads(entry[1])
    if entry:
        _memory.pop(key, None)
    return None


async def set_json(key: str, value: Any, ttl_seconds: int) -> None:
    raw = json.dumps(value)
    client = await _get_redis()
    if client is not None:
        try:
            await client.set(key, raw, ex=ttl_seconds)
            return
        except Exception:
            pass  # fall through to memory
    if len(_memory) >= _MEMORY_MAX_KEYS:
        now = time.monotonic()
        expired = [k for k, (exp, _) in _memory.items() if exp <= now]
        for k in expired:
            _memory.pop(k, None)
        while len(_memory) >= _MEMORY_MAX_KEYS:
            _memory.pop(next(iter(_memory)))
    _memory[key] = (time.monotonic() + ttl_seconds, raw)
