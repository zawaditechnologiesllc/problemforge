"""Tests for the cache layer and the timeless backfill windows."""

import asyncio
import time
from datetime import date

from app.services import cache
from worker.backfill_history import _windows


def test_memory_cache_roundtrip_and_expiry(monkeypatch):
    key = cache.hash_key("test", f"roundtrip-{time.time()}")
    assert asyncio.run(cache.get_json(key)) is None
    asyncio.run(cache.set_json(key, {"a": [1, 2]}, ttl_seconds=60))
    assert asyncio.run(cache.get_json(key)) == {"a": [1, 2]}

    expired_key = cache.hash_key("test", f"expiry-{time.time()}")
    asyncio.run(cache.set_json(expired_key, "x", ttl_seconds=60))
    # Force expiry by rewinding the stored deadline
    deadline, raw = cache._memory[expired_key]
    cache._memory[expired_key] = (time.monotonic() - 1, raw)
    assert asyncio.run(cache.get_json(expired_key)) is None


def test_hash_key_is_stable_and_distinct():
    assert cache.hash_key("emb", "hello") == cache.hash_key("emb", "hello")
    assert cache.hash_key("emb", "hello") != cache.hash_key("emb", "world")
    assert cache.hash_key("emb", "hello") != cache.hash_key("framework", "hello")


def test_backfill_windows_are_timeless():
    windows = list(_windows(date(1960, 1, 1), date(1990, 12, 31)))
    # Pre-1980: year-sized; 1980+: month-sized
    early = [w for w in windows if w[0].year < 1980]
    late = [w for w in windows if w[0].year >= 1980]
    assert len(early) == 20  # 1960..1979 inclusive, one window per year
    assert len(late) == 11 * 12  # 1980..1990 inclusive, monthly
    # Continuous coverage, no gaps or overlaps
    for (lo_a, hi_a), (lo_b, _) in zip(windows, windows[1:]):
        assert (lo_b - hi_a).days == 1
    assert windows[0][0] == date(1960, 1, 1)
    assert windows[-1][1] == date(1990, 12, 31)


def test_backfill_windows_clamp_to_end():
    windows = list(_windows(date(2005, 1, 1), date(2005, 2, 15)))
    assert windows[-1][1] == date(2005, 2, 15)
