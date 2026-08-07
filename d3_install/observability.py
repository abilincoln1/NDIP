"""
NDIP Phase D.3 — Observability (D3.8)
File: app/api/middleware/observability.py

Implements:
  - Request correlation IDs (X-Request-ID header — generated if absent)
  - Structured JSON logging with request context
  - Slow query detection via response-time header
  - Request state enrichment so AuditLogMiddleware picks up user identity
  - Health and readiness endpoint helpers

Register in main.py BEFORE AuditLogMiddleware so request IDs are
available when audit records are written:

    app.add_middleware(ObservabilityMiddleware)
    app.add_middleware(AuditLogMiddleware)
"""
import json
import logging
import time
import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.security import decode_token

SLOW_REQUEST_THRESHOLD_MS = 1000  # Log a warning for requests over 1 second

logger = logging.getLogger("ndip.api")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Per-request middleware that:
    1. Assigns or propagates X-Request-ID
    2. Decodes the bearer token (if present) and attaches user identity
       to request.state so AuditLogMiddleware can log it without re-decoding
    3. Logs structured JSON for every request at INFO level
    4. Logs a WARNING for slow requests
    5. Propagates X-Request-ID in the response headers
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.time()

        # Decode token and attach identity to request state
        # (best-effort — auth failures are handled by route dependencies)
        _attach_identity(request)

        # Process request
        response: Response = await call_next(request)

        duration_ms = int((time.time() - start) * 1000)

        # Attach request ID and timing to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)

        # Structured log record
        log_record = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "user_id": getattr(request.state, "user_id", None),
            "user_email": getattr(request.state, "user_email", None),
            "ip": _get_ip(request),
            "user_agent": request.headers.get("user-agent", "")[:200],
        }

        if response.status_code >= 500:
            logger.error(json.dumps(log_record))
        elif duration_ms >= SLOW_REQUEST_THRESHOLD_MS:
            log_record["slow_request"] = True
            logger.warning(json.dumps(log_record))
        elif response.status_code >= 400:
            logger.warning(json.dumps(log_record))
        else:
            logger.info(json.dumps(log_record))

        return response


def _attach_identity(request: Request) -> None:
    """Extract JWT claims and attach to request.state."""
    request.state.user_id = None
    request.state.user_email = None
    try:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            claims = decode_token(token)
            request.state.user_id = claims.get("sub") or claims.get("member_id")
            request.state.user_email = claims.get("email")
    except Exception:
        pass  # Not authenticated — leave state as None


def _get_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None
