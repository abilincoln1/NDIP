"""
NDIP Phase D.3 — Health Endpoints (D3.8) + Rate Limiting (D3.9)
File: app/api/routes/health_v2.py

Health endpoints:
  GET /health           — liveness (already exists in main.py, enhanced here)
  GET /readiness        — readiness: checks DB + Redis connectivity
  GET /api/v2/metrics   — platform metrics for monitoring

Rate limiting middleware (D3.9):
  RateLimitMiddleware — per-IP sliding window using Redis.
  Falls back to in-memory if Redis is unavailable (degraded mode).
  Limits: 60 req/min for authenticated, 20 req/min for unauthenticated.
  Auth endpoints (/api/v2/auth/password-reset, /api/v2/auth/verify-email):
  stricter limit of 10 req/min per IP.
"""
import time
import logging
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from sqlalchemy import text

logger = logging.getLogger("ndip.health")

health_router = APIRouter(tags=["health_v2"])


# ─── Health endpoints ───────────────────────────────────────────────────────

@health_router.get("/readiness", summary="Readiness check — DB + Redis")
def readiness():
    """Returns 200 if the platform can serve traffic (DB and Redis reachable).
    Returns 503 with details if any dependency is down."""
    from app.db.database import SessionLocal
    import os, redis as redis_lib

    checks = {}
    healthy = True

    # Database check
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        healthy = False

    # Redis check
    try:
        r = redis_lib.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
        r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        healthy = False

    status_code = 200 if healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if healthy else "degraded", "checks": checks},
    )


@health_router.get("/api/v2/metrics", summary="Platform metrics")
def metrics():
    """Live platform metrics for monitoring dashboards."""
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        row = db.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM members WHERE is_active AND deleted_at IS NULL) AS active_members,
                (SELECT COUNT(*) FROM member_sessions WHERE revoked_at IS NULL AND expires_at > now()) AS active_sessions,
                (SELECT COUNT(*) FROM audit_log WHERE created_at > now() - INTERVAL '1 hour') AS requests_last_hour,
                (SELECT COUNT(*) FROM notifications WHERE status = 'failed') AS failed_notifications,
                (SELECT COUNT(*) FROM verification_submissions WHERE status = 'pending' AND deleted_at IS NULL) AS pending_verifications,
                (SELECT AVG(duration_ms) FROM audit_log WHERE created_at > now() - INTERVAL '5 minutes') AS avg_response_ms_5min,
                (SELECT COUNT(*) FROM audit_log WHERE response_code >= 500 AND created_at > now() - INTERVAL '1 hour') AS server_errors_last_hour,
                (SELECT COUNT(*) FROM scheduler_job_log WHERE status = 'failed' AND started_at > now() - INTERVAL '24 hours') AS scheduler_failures_24h
        """)).fetchone()
        return dict(row._mapping) if row else {}
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()


# ─── Rate Limiting Middleware ───────────────────────────────────────────────

# Stricter limits for sensitive auth endpoints
STRICT_PATHS = {
    "/api/v2/auth/password-reset/request",
    "/api/v2/auth/verify-email/request",
    "/api/v2/members/login",
    "/api/v2/members/register",
}

SKIP_PATHS = {"/health", "/readiness", "/docs", "/openapi.json", "/redoc"}

RATE_LIMITS = {
    "strict": (10, 60),      # 10 requests per 60 seconds
    "unauthenticated": (20, 60),
    "authenticated": (60, 60),
}


class InMemoryRateLimiter:
    """Fallback in-memory rate limiter (not suitable for multi-process)."""
    def __init__(self):
        self._windows: dict = defaultdict(list)

    def is_allowed(self, key: str, limit: int, window_sec: int) -> bool:
        now = time.time()
        window = self._windows[key]
        self._windows[key] = [t for t in window if now - t < window_sec]
        if len(self._windows[key]) >= limit:
            return False
        self._windows[key].append(now)
        return True


class RedisRateLimiter:
    """Redis-backed sliding window rate limiter."""
    def __init__(self, redis_client):
        self._r = redis_client

    def is_allowed(self, key: str, limit: int, window_sec: int) -> bool:
        pipe = self._r.pipeline()
        now = time.time()
        window_start = now - window_sec
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window_sec + 1)
        results = pipe.execute()
        current_count = results[1]
        return current_count < limit


def _build_rate_limiter():
    try:
        import redis as redis_lib, os
        r = redis_lib.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
        r.ping()
        return RedisRateLimiter(r)
    except Exception:
        logger.warning("Redis unavailable for rate limiting — using in-memory fallback")
        return InMemoryRateLimiter()


_LIMITER = _build_rate_limiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter. Keyed by IP address.
    Returns 429 Too Many Requests when limit is exceeded.
    Applied before auth so even unauthenticated brute force is throttled.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if path in SKIP_PATHS or path.startswith("/static"):
            return await call_next(request)

        ip = _get_ip(request)
        key_prefix = f"ratelimit:{ip}:{path}" if path in STRICT_PATHS else f"ratelimit:{ip}"

        # Determine limit tier
        if path in STRICT_PATHS:
            limit, window = RATE_LIMITS["strict"]
        elif getattr(request.state, "user_id", None):
            limit, window = RATE_LIMITS["authenticated"]
        else:
            limit, window = RATE_LIMITS["unauthenticated"]

        if not _LIMITER.is_allowed(key_prefix, limit, window):
            return JSONResponse(
                status_code=429,
                content={
                    "ok": False,
                    "error": "Too many requests. Please slow down.",
                    "code": "RATE_LIMIT_EXCEEDED",
                },
                headers={"Retry-After": str(window)},
            )

        return await call_next(request)


def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
