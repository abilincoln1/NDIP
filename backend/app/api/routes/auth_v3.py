"""
NDIP on Orion Platform Kernel
/api/v3/auth/ — Platform Identity Authentication
Phase D5A-S2

Separate from /api/v2/members/login — operates on platform_identities table.
v2 routes are untouched.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, EmailStr
from typing import Optional
import bcrypt
from jose import jwt, JWTError
import uuid
from datetime import datetime, timezone, timedelta

from app.db.database import SessionLocal
from app.core.config import get_settings

router = APIRouter(prefix="/api/v3/auth", tags=["v3-auth"])


# ── DB dependency ──────────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Schemas ────────────────────────────────────────────────────────────────────

class V3LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: Optional[str] = "rtifn"


class V3LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    identity_id: str
    tenant_id: str
    full_name: str
    roles: list[str]
    admin_level: Optional[str] = None


class V3RefreshRequest(BaseModel):
    refresh_token: str


class V3TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── JWT helpers ────────────────────────────────────────────────────────────────

def _create_v3_access_token(payload: dict) -> str:
    s = get_settings()
    data = payload.copy()
    data["exp"] = datetime.now(timezone.utc) + timedelta(minutes=30)
    data["iat"] = datetime.now(timezone.utc)
    data["v"] = "3"
    return jwt.encode(data, s.secret_key, algorithm="HS256")


def _create_v3_refresh_token(identity_id: str, tenant_id: str) -> str:
    s = get_settings()
    data = {
        "sub": identity_id,
        "tenant_id": tenant_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "iat": datetime.now(timezone.utc),
        "v": "3",
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(data, s.secret_key, algorithm="HS256")


def _decode_v3_token(token: str) -> dict:
    s = get_settings()
    try:
        return jwt.decode(token, s.secret_key, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ── Current identity dependency ────────────────────────────────────────────────

def get_current_v3_identity(request: Request, db: Session = Depends(get_db)) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth[7:]
    payload = _decode_v3_token(token)
    if payload.get("v") != "3":
        raise HTTPException(status_code=401, detail="Use v3 token for v3 routes")
    identity_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    if not identity_id or not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    # Set RLS session variable
    db.execute(text("SET LOCAL app.current_tenant_id = :tid"), {"tid": tenant_id})
    return payload


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=V3LoginResponse)
def v3_login(payload: V3LoginRequest, db: Session = Depends(get_db)):
    """
    Platform identity login. Returns v3 JWT.
    Works independently of the v2 members table.
    """
    # 1. Resolve tenant
    tenant = db.execute(
        text("SELECT id, status FROM tenants WHERE slug = :slug"),
        {"slug": payload.tenant_slug}
    ).fetchone()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if tenant.status != "active":
        raise HTTPException(status_code=403, detail="Tenant is not active")
    tenant_id = str(tenant.id)

    # 2. Find identity
    identity = db.execute(
        text("""
            SELECT pi.id, pi.full_name, pi.identity_status,
                   pia.password_hash, pia.failed_attempts, pia.locked_until
            FROM platform_identities pi
            JOIN platform_identity_auth pia ON pia.identity_id = pi.id
            WHERE pi.email = :email
        """),
        {"email": payload.email.lower()}
    ).fetchone()

    if not identity:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if identity.identity_status != "active":
        raise HTTPException(status_code=403, detail="Identity is not active")

    if identity.locked_until and identity.locked_until > datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="Account temporarily locked")

    # 3. Verify password
    if not bcrypt.checkpw(payload.password.encode(), identity.password_hash.encode()):
        # Increment failed attempts
        db.execute(
            text("UPDATE platform_identity_auth SET failed_attempts = failed_attempts + 1 WHERE identity_id = :id"),
            {"id": str(identity.id)}
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 4. Reset failed attempts, update last_login
    db.execute(
        text("""
            UPDATE platform_identity_auth
            SET failed_attempts = 0, last_login_at = now()
            WHERE identity_id = :id
        """),
        {"id": str(identity.id)}
    )
    db.execute(
        text("UPDATE platform_identities SET last_seen_at = now() WHERE id = :id"),
        {"id": str(identity.id)}
    )

    # 5. Resolve membership and roles for this tenant
    # memberships table created in D5A-S3 — safe fallback if not yet present
    roles = []
    try:
        membership = db.execute(
            text("""
                SELECT m.id, m.status
                FROM memberships m
                WHERE m.identity_id = :iid AND m.tenant_id = :tid AND m.status = 'active'
                LIMIT 1
            """),
            {"iid": str(identity.id), "tid": tenant_id}
        ).fetchone()
        if membership:
            role_rows = db.execute(
                text("""
                    SELECT kr.name
                    FROM membership_roles mr
                    JOIN kernel_roles kr ON kr.id = mr.role_id
                    WHERE mr.membership_id = :mid
                """),
                {"mid": str(membership.id)}
            ).fetchall()
            roles = [r.name for r in role_rows]
    except Exception:
        db.rollback()
        roles = []

    # 6. Check platform admin level
    admin = db.execute(
        text("SELECT admin_level FROM platform_admins WHERE identity_id = :id"),
        {"id": str(identity.id)}
    ).fetchone()
    admin_level = admin.admin_level if admin else None

    db.commit()

    # 7. Build JWT
    token_payload = {
        "sub": str(identity.id),
        "tenant_id": tenant_id,
        "tenant_slug": payload.tenant_slug,
        "roles": roles,
        "admin_level": admin_level,
        "full_name": identity.full_name,
    }
    access_token = _create_v3_access_token(token_payload)
    refresh_token = _create_v3_refresh_token(str(identity.id), tenant_id)

    return V3LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        identity_id=str(identity.id),
        tenant_id=tenant_id,
        full_name=identity.full_name,
        roles=roles,
        admin_level=admin_level,
    )


@router.post("/refresh", response_model=V3TokenResponse)
def v3_refresh(payload: V3RefreshRequest, db: Session = Depends(get_db)):
    """Refresh a v3 access token using a v3 refresh token."""
    data = _decode_v3_token(payload.refresh_token)
    if data.get("type") != "refresh" or data.get("v") != "3":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    identity_id = data["sub"]
    tenant_id = data["tenant_id"]

    # Verify identity still active
    identity = db.execute(
        text("SELECT id, full_name, identity_status FROM platform_identities WHERE id = :id"),
        {"id": identity_id}
    ).fetchone()
    if not identity or identity.identity_status != "active":
        raise HTTPException(status_code=401, detail="Identity not active")

    # Rebuild roles — safe fallback before D5A-S3
    roles = []
    try:
        membership = db.execute(
            text("""
                SELECT m.id FROM memberships m
                WHERE m.identity_id = :iid AND m.tenant_id = :tid AND m.status = 'active'
                LIMIT 1
            """),
            {"iid": identity_id, "tid": tenant_id}
        ).fetchone()
        if membership:
            role_rows = db.execute(
                text("""
                    SELECT kr.name FROM membership_roles mr
                    JOIN kernel_roles kr ON kr.id = mr.role_id
                    WHERE mr.membership_id = :mid
                """),
                {"mid": str(membership.id)}
            ).fetchall()
            roles = [r.name for r in role_rows]
    except Exception:
        db.rollback()
        roles = []

    admin = db.execute(
        text("SELECT admin_level FROM platform_admins WHERE identity_id = :id"),
        {"id": identity_id}
    ).fetchone()

    token_payload = {
        "sub": identity_id,
        "tenant_id": tenant_id,
        "roles": roles,
        "admin_level": admin.admin_level if admin else None,
        "full_name": identity.full_name,
    }
    access_token = _create_v3_access_token(token_payload)
    return V3TokenResponse(access_token=access_token)


@router.get("/me")
def v3_me(
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """Return current platform identity profile."""
    identity = db.execute(
        text("""
            SELECT pi.id, pi.email, pi.full_name, pi.phone,
                   pi.identity_status, pi.created_at, pi.last_seen_at,
                   c.name AS residence_country
            FROM platform_identities pi
            LEFT JOIN countries c ON c.id = pi.residence_country_id
            WHERE pi.id = :id
        """),
        {"id": current["sub"]}
    ).fetchone()

    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found")

    # Memberships across all tenants — safe fallback before D5A-S3
    memberships = []
    try:
        memberships = db.execute(
            text("""
                SELECT m.id, m.tenant_id, t.name AS tenant_name, t.slug,
                       o.name AS org_name, m.membership_number,
                       m.membership_type, m.status, m.joined_date
                FROM memberships m
                JOIN tenants t ON t.id = m.tenant_id
                LEFT JOIN organisations o ON o.id = m.organisation_id
                WHERE m.identity_id = :id AND m.status = 'active'
            """),
            {"id": current["sub"]}
        ).fetchall()
    except Exception:
        db.rollback()
        memberships = []

    return {
        "identity_id": str(identity.id),
        "email": identity.email,
        "full_name": identity.full_name,
        "phone": identity.phone,
        "identity_status": identity.identity_status,
        "residence_country": identity.residence_country,
        "created_at": identity.created_at.isoformat() if identity.created_at else None,
        "last_seen_at": identity.last_seen_at.isoformat() if identity.last_seen_at else None,
        "current_tenant_id": current["tenant_id"],
        "roles": current.get("roles", []),
        "admin_level": current.get("admin_level"),
        "memberships": [
            {
                "membership_id": str(m.id),
                "tenant_id": str(m.tenant_id),
                "tenant_name": m.tenant_name,
                "tenant_slug": m.slug,
                "organisation": m.org_name,
                "membership_number": m.membership_number,
                "membership_type": m.membership_type,
                "status": m.status,
                "joined_date": m.joined_date.isoformat() if m.joined_date else None,
            }
            for m in memberships
        ],
    }
