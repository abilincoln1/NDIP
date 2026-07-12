"""
Redis Cache Service
Caches intelligence results to avoid recomputing on every request.
Cache TTLs match data freshness requirements:
- Leadership Pack: 60 min
- National Pulse: 60 min  
- Situation Room: 30 min
- Intelligence Brief: 60 min
- Historical: 2 hours
Cache is automatically invalidated after daily ingest.
"""
import json
import hashlib
from typing import Any, Optional
from functools import wraps

try:
    import redis
    _redis_available = True
except ImportError:
    _redis_available = False

from app.core.config import get_settings

settings = get_settings()

_client: Optional[Any] = None


def get_redis():
    global _client
    if _client is None and _redis_available:
        try:
            _client = redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=2)
            _client.ping()
        except Exception:
            _client = None
    return _client


def cache_key(*parts) -> str:
    """Generate a consistent cache key from parts."""
    key = ":".join(str(p) for p in parts)
    return f"agora:{key}"


def get_cached(key: str) -> Optional[dict]:
    """Get a cached value. Returns None if not found or Redis unavailable."""
    r = get_redis()
    if not r:
        return None
    try:
        val = r.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


def set_cached(key: str, value: dict, ttl_seconds: int = 1800) -> bool:
    """Cache a value with TTL. Returns True if successful."""
    r = get_redis()
    if not r:
        return False
    try:
        r.setex(key, ttl_seconds, json.dumps(value, default=str))
        return True
    except Exception:
        return False


def invalidate_pattern(pattern: str) -> int:
    """Delete all keys matching pattern. Returns count deleted."""
    r = get_redis()
    if not r:
        return 0
    try:
        keys = r.keys(f"agora:{pattern}*")
        if keys:
            return r.delete(*keys)
        return 0
    except Exception:
        return 0


def invalidate_all() -> int:
    """Clear all Agora cache entries. Call after daily ingest."""
    return invalidate_pattern("")


# ─── TTL constants ────────────────────────────────────────────────────────────
TTL_LEADERSHIP_PACK = 3600    # 60 min
TTL_NATIONAL_PULSE  = 3600    # 60 min
TTL_SITUATION_ROOM  = 1800    # 30 min
TTL_BRIEF           = 3600    # 60 min
TTL_HISTORICAL      = 7200    # 2 hours
TTL_NARRATIVES      = 1800    # 30 min


def cached_endpoint(prefix: str, ttl: int):
    """
    Decorator for FastAPI route functions.
    Caches based on prefix + function arguments.
    Usage:
        @cached_endpoint("leadership-pack", TTL_LEADERSHIP_PACK)
        def my_route(days: int, db, _):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from kwargs (days, period etc)
            key_parts = [prefix] + [f"{k}={v}" for k, v in sorted(kwargs.items())
                                     if k not in ("db", "_")]
            key = cache_key(*key_parts)

            cached = get_cached(key)
            if cached is not None:
                cached["_cached"] = True
                return cached

            result = func(*args, **kwargs)

            if isinstance(result, dict):
                set_cached(key, result, ttl)

            return result
        return wrapper
    return decorator
