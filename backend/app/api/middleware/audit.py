"""
NDIP V8 — Audit Log Middleware (EB-005)
Intercepts every API request and writes an immutable record to audit_log.
Captures: user, endpoint, method, IP, response code, duration.
Must be registered in main.py as:
    app.add_middleware(AuditLogMiddleware)
"""
import time
import hashlib
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy import text
from app.db.database import SessionLocal

# Endpoints that do not need audit logging (health checks, static assets)
SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico"}


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip non-auditable paths
        if request.url.path in SKIP_PATHS or request.url.path.startswith("/static"):
            return await call_next(request)

        start_time = time.time()
        response: Response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)

        # Extract user identity from request state (set by auth middleware)
        user_email = None
        user_id = None
        try:
            user_email = getattr(request.state, "user_email", None)
            user_id = getattr(request.state, "user_id", None)
        except Exception:
            pass

        # Extract IP address
        ip = request.client.host if request.client else None
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()

        # Hash any query params for audit (never log values, only structure)
        payload_hash = None
        try:
            query_keys = sorted(request.query_params.keys())
            payload_hash = hashlib.sha256(
                json.dumps(query_keys).encode()
            ).hexdigest()[:16] if query_keys else None
        except Exception:
            pass

        # Write audit record — fire and forget, non-blocking
        try:
            db = SessionLocal()
            db.execute(text("""
                INSERT INTO audit_log
                    (user_email, user_id, action, endpoint, method,
                     ip_address, user_agent, payload_hash, response_code, duration_ms)
                VALUES
                    (:user_email, :user_id, :action, :endpoint, :method,
                     :ip_address::inet, :user_agent, :payload_hash, :response_code, :duration_ms)
            """), {
                "user_email": user_email,
                "user_id": user_id,
                "action": f"{request.method}:{request.url.path}",
                "endpoint": str(request.url.path)[:500],
                "method": request.method,
                "ip_address": ip,
                "user_agent": request.headers.get("user-agent", "")[:500],
                "payload_hash": payload_hash,
                "response_code": response.status_code,
                "duration_ms": duration_ms,
            })
            db.commit()
            db.close()
        except Exception:
            # Audit log failure must never break the API response
            pass

        return response
