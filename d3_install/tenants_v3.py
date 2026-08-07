"""
NDIP on Orion Platform Kernel
/api/v3/tenants/ — Tenant Management (platform admin only)
Phase D5A-S2
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.db.database import SessionLocal
from app.api.routes.auth_v3 import get_current_v3_identity, get_db

router = APIRouter(prefix="/api/v3/tenants", tags=["v3-tenants"])


# ── Guards ─────────────────────────────────────────────────────────────────────

def require_platform_admin(current: dict = Depends(get_current_v3_identity)):
    if not current.get("admin_level"):
        raise HTTPException(status_code=403, detail="Platform admin access required")
    return current


# ── Schemas ────────────────────────────────────────────────────────────────────

class TenantCreate(BaseModel):
    name: str
    slug: str
    tenant_type: str
    primary_country_iso: Optional[str] = "GB"


class TenantConfigUpdate(BaseModel):
    platform_name_override: Optional[str] = None
    powered_by_label: Optional[str] = None
    primary_colour: Optional[str] = None
    secondary_colour: Optional[str] = None
    accent_colour: Optional[str] = None
    enabled_modules: Optional[list[str]] = None
    custom_terminology: Optional[dict] = None


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/")
def list_tenants(
    db: Session = Depends(get_db),
    current: dict = Depends(require_platform_admin)
):
    """List all tenants. Platform admin only."""
    rows = db.execute(text("""
        SELECT t.id, t.name, t.slug, t.tenant_type, t.status, t.created_at,
               tc.platform_name_override, tc.enabled_modules
        FROM tenants t
        LEFT JOIN tenant_config tc ON tc.tenant_id = t.id
        ORDER BY t.created_at
    """)).fetchall()

    return [
        {
            "id": str(r.id),
            "name": r.name,
            "slug": r.slug,
            "tenant_type": r.tenant_type,
            "status": r.status,
            "platform_name_override": r.platform_name_override,
            "enabled_modules": r.enabled_modules,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/{slug}")
def get_tenant(
    slug: str,
    db: Session = Depends(get_db),
    current: dict = Depends(require_platform_admin)
):
    """Get a single tenant by slug. Platform admin only."""
    row = db.execute(
        text("""
            SELECT t.id, t.name, t.slug, t.tenant_type, t.status, t.created_at,
                   tc.logo_url, tc.primary_colour, tc.secondary_colour, tc.accent_colour,
                   tc.platform_name_override, tc.powered_by_label,
                   tc.enabled_modules, tc.custom_terminology, tc.dashboard_layout
            FROM tenants t
            LEFT JOIN tenant_config tc ON tc.tenant_id = t.id
            WHERE t.slug = :slug
        """),
        {"slug": slug}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Member count
    member_count = db.execute(
        text("SELECT COUNT(*) FROM memberships WHERE tenant_id = :tid AND status = 'active'"),
        {"tid": str(row.id)}
    ).scalar()

    return {
        "id": str(row.id),
        "name": row.name,
        "slug": row.slug,
        "tenant_type": row.tenant_type,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "config": {
            "logo_url": row.logo_url,
            "primary_colour": row.primary_colour,
            "secondary_colour": row.secondary_colour,
            "accent_colour": row.accent_colour,
            "platform_name_override": row.platform_name_override,
            "powered_by_label": row.powered_by_label,
            "enabled_modules": row.enabled_modules,
            "custom_terminology": row.custom_terminology,
            "dashboard_layout": row.dashboard_layout,
        },
        "stats": {
            "active_members": member_count,
        }
    }


@router.post("/", status_code=201)
def create_tenant(
    payload: TenantCreate,
    db: Session = Depends(get_db),
    current: dict = Depends(require_platform_admin)
):
    """Create a new tenant. Platform admin only."""
    existing = db.execute(
        text("SELECT id FROM tenants WHERE slug = :slug"),
        {"slug": payload.slug}
    ).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail=f"Slug '{payload.slug}' already taken")

    country = db.execute(
        text("SELECT id FROM countries WHERE iso_code = :iso"),
        {"iso": payload.primary_country_iso.upper()}
    ).fetchone()

    tenant = db.execute(
        text("""
            INSERT INTO tenants (name, slug, tenant_type, status, primary_country_id)
            VALUES (:name, :slug, :type, 'onboarding', :cid)
            RETURNING id, name, slug, tenant_type, status, created_at
        """),
        {
            "name": payload.name,
            "slug": payload.slug,
            "type": payload.tenant_type,
            "cid": str(country.id) if country else None,
        }
    ).fetchone()

    # Create default config
    db.execute(
        text("""
            INSERT INTO tenant_config (tenant_id)
            VALUES (:tid)
            ON CONFLICT (tenant_id) DO NOTHING
        """),
        {"tid": str(tenant.id)}
    )

    db.commit()

    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "slug": tenant.slug,
        "tenant_type": tenant.tenant_type,
        "status": tenant.status,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
        "message": "Tenant created. Status: onboarding. Activate when ready."
    }


@router.patch("/{slug}/config")
def update_tenant_config(
    slug: str,
    payload: TenantConfigUpdate,
    db: Session = Depends(get_db),
    current: dict = Depends(require_platform_admin)
):
    """Update tenant branding and config. Platform admin only."""
    tenant = db.execute(
        text("SELECT id FROM tenants WHERE slug = :slug"),
        {"slug": slug}
    ).fetchone()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    updates = {}
    if payload.platform_name_override is not None:
        updates["platform_name_override"] = payload.platform_name_override
    if payload.powered_by_label is not None:
        updates["powered_by_label"] = payload.powered_by_label
    if payload.primary_colour is not None:
        updates["primary_colour"] = payload.primary_colour
    if payload.secondary_colour is not None:
        updates["secondary_colour"] = payload.secondary_colour
    if payload.accent_colour is not None:
        updates["accent_colour"] = payload.accent_colour
    if payload.enabled_modules is not None:
        updates["enabled_modules"] = payload.enabled_modules
    if payload.custom_terminology is not None:
        updates["custom_terminology"] = payload.custom_terminology

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clauses = ", ".join([f"{k} = :{k}" for k in updates])
    updates["tid"] = str(tenant.id)
    updates["updated_at"] = datetime.utcnow()

    db.execute(
        text(f"UPDATE tenant_config SET {set_clauses}, updated_at = :updated_at WHERE tenant_id = :tid"),
        updates
    )
    db.commit()

    return {"message": f"Tenant config updated for {slug}"}


@router.patch("/{slug}/status")
def update_tenant_status(
    slug: str,
    status: str,
    db: Session = Depends(get_db),
    current: dict = Depends(require_platform_admin)
):
    """Activate, suspend or offboard a tenant. Platform admin only."""
    valid = ["onboarding", "active", "suspended", "offboarded"]
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid}")

    result = db.execute(
        text("UPDATE tenants SET status = :status WHERE slug = :slug RETURNING id"),
        {"status": status, "slug": slug}
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Tenant not found")
    db.commit()
    return {"message": f"Tenant '{slug}' status set to '{status}'"}
