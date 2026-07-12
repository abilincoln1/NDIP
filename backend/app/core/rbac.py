"""
NDIP V8 — Role-Based Access Control (EB-004)
Implements:
  - Permission checking via FastAPI dependency
  - Role-to-permission mappings (loaded from DB, cached)
  - require_permission() dependency for route decoration
  - User role resolution from JWT + database

Usage in routes:
    @router.get("/sensitive-data")
    def get_data(
        _: None = Depends(require_permission("intelligence:read")),
        current_user: dict = Depends(get_current_user),
    ):
        ...
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from functools import lru_cache
from typing import Optional
import time

from app.db.database import get_db
from app.core.security import get_current_user


# ── Permission constants ──────────────────────────────────────────────────
class Permission:
    INTELLIGENCE_READ    = "intelligence:read"
    INTELLIGENCE_EXPORT  = "intelligence:export"
    COPILOT_USE          = "copilot:use"
    ONBOARDING_READ      = "onboarding:read"
    ADMIN_USERS          = "admin:users"
    ADMIN_SOURCES        = "admin:sources"
    ADMIN_SYSTEM         = "admin:system"
    STRATEGIC_READ       = "strategic:read"
    ELECTION_READ        = "election:read"
    GNEI_READ            = "gnei:read"


# ── Role permission cache (refreshes every 5 minutes) ───────────────────
_role_permission_cache: dict = {}
_cache_timestamp: float = 0.0
_CACHE_TTL = 300  # 5 minutes


def _get_role_permissions(db: Session) -> dict:
    """Returns {role_name: set(permission_names)}. Cached for 5 minutes."""
    global _role_permission_cache, _cache_timestamp

    now = time.time()
    if _role_permission_cache and (now - _cache_timestamp) < _CACHE_TTL:
        return _role_permission_cache

    try:
        rows = db.execute(text("""
            SELECT r.name AS role_name, p.name AS permission_name
            FROM role_permissions rp
            JOIN roles r ON r.id = rp.role_id
            JOIN permissions p ON p.id = rp.permission_id
        """)).fetchall()

        cache: dict = {}
        for row in rows:
            if row.role_name not in cache:
                cache[row.role_name] = set()
            cache[row.role_name].add(row.permission_name)

        _role_permission_cache = cache
        _cache_timestamp = now
        return cache
    except Exception:
        # Graceful degradation: if RBAC tables don't exist yet, allow all
        return {}


def get_user_role(user_email: str, db: Session) -> str:
    """Resolve the authenticated user's role from the database."""
    try:
        result = db.execute(text("""
            SELECT r.name FROM user_roles ur
            JOIN roles r ON r.id = ur.role_id
            JOIN admin_users u ON u.id = ur.user_id
            WHERE u.email = :email
            ORDER BY r.id ASC
            LIMIT 1
        """), {"email": user_email}).fetchone()
        return result[0] if result else "executive"
    except Exception:
        return "executive"


def user_has_permission(user_email: str, permission: str, db: Session) -> bool:
    """Check whether a user has a specific permission via their role."""
    role = get_user_role(user_email, db)

    # Admins always have all permissions
    if role == "admin":
        return True

    role_permissions = _get_role_permissions(db)

    # If RBAC tables don't exist yet, grant all permissions (migration not run)
    if not role_permissions:
        return True

    user_permissions = role_permissions.get(role, set())
    return permission in user_permissions


def require_permission(permission: str):
    """
    FastAPI dependency factory.
    Usage: Depends(require_permission("intelligence:read"))
    """
    def _check(
        db: Session = Depends(get_db),
        current_user: dict = Depends(get_current_user),
    ):
        user_email = current_user.get("email", "unknown")
        if not user_has_permission(user_email, permission, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {permission}. Contact your administrator to request access.",
            )
        return current_user

    return _check


def get_user_role_dep(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> str:
    """FastAPI dependency: returns the current user's role string."""
    user_email = current_user.get("email", "unknown")
    return get_user_role(user_email, db)
