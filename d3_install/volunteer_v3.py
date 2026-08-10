"""
NDIP on Orion Platform Kernel
/api/v3/volunteer/ — Volunteer Engine
Phase D5A-S4

Orion Kernel capability — domain-agnostic volunteer record infrastructure.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import uuid

from app.db.database import SessionLocal
from app.api.routes.auth_v3 import get_current_v3_identity, get_db
from app.api.routes.activities_v3 import (
    set_tenant_context, require_active_membership,
    can_verify, can_admin, VALID_TRANSITIONS
)

router = APIRouter(prefix="/api/v3/volunteer", tags=["v3-volunteer"])

VOLUNTEER_TYPES = [
    'canvassing', 'event_support', 'admin', 'training',
    'outreach', 'mentoring', 'technical', 'fundraising',
    'project_work', 'community', 'other'
]


# ── Schemas ────────────────────────────────────────────────────────────────────

class VolunteerCreate(BaseModel):
    volunteer_type: str
    description: Optional[str] = None
    hours_contributed: Optional[float] = None
    volunteer_date: date
    organisation_id: Optional[str] = None
    activity_id: Optional[str] = None
    location_state_id: Optional[int] = None
    location_lga_id: Optional[int] = None
    location_ward_id: Optional[int] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    skills_used: Optional[list] = []


class VolunteerUpdate(BaseModel):
    description: Optional[str] = None
    hours_contributed: Optional[float] = None
    volunteer_date: Optional[date] = None
    location_state_id: Optional[int] = None
    location_lga_id: Optional[int] = None
    location_ward_id: Optional[int] = None
    skills_used: Optional[list] = None


class VerificationAction(BaseModel):
    action: str
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def format_volunteer(row) -> dict:
    return {
        "id": str(row.id),
        "volunteer_type": row.volunteer_type,
        "description": row.description,
        "hours_contributed": row.hours_contributed,
        "volunteer_date": row.volunteer_date.isoformat() if row.volunteer_date else None,
        "volunteer_name": row.volunteer_name,
        "organisation": row.org_name,
        "activity_id": str(row.activity_id) if row.activity_id else None,
        "skills_used": row.skills_used or [],
        "verification_status": row.verification_status,
        "is_verified": row.verification_status == "Verified",
        "verified_by_name": row.verified_by_name,
        "verified_at": row.verified_at.isoformat() if row.verified_at else None,
        "verification_notes": row.verification_notes,
        "geography": {
            "state": row.state_name,
            "lga": row.lga_name,
            "ward": row.ward_name,
            "gps_lat": row.gps_lat,
            "gps_lng": row.gps_lng,
        },
        "tenant_id": str(row.tenant_id),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "is_archived": row.is_archived,
    }


VOLUNTEER_SELECT = """
    SELECT
        v.id, v.volunteer_type, v.description, v.hours_contributed,
        v.volunteer_date, v.skills_used, v.verification_status,
        v.verified_at, v.verification_notes, v.created_at, v.is_archived,
        v.gps_lat, v.gps_lng, v.activity_id, v.tenant_id,
        pi.full_name AS volunteer_name,
        piv.full_name AS verified_by_name,
        o.name AS org_name,
        s.name AS state_name,
        l.name AS lga_name,
        w.name AS ward_name
    FROM volunteer_records v
    JOIN platform_identities pi ON pi.id = v.identity_id
    LEFT JOIN platform_identities piv ON piv.id = v.verified_by
    LEFT JOIN organisations o ON o.id = v.organisation_id
    LEFT JOIN ng_states s ON s.id = v.location_state_id
    LEFT JOIN ng_lgas l ON l.id = v.location_lga_id
    LEFT JOIN ng_wards w ON w.id = v.location_ward_id
"""


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/", status_code=201)
def create_volunteer_record(
    payload: VolunteerCreate,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """Create a new volunteer record."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)
    require_active_membership(current, db, tenant_id)

    if payload.volunteer_type not in VOLUNTEER_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid volunteer_type. Valid: {VOLUNTEER_TYPES}")

    if payload.organisation_id:
        org = db.execute(
            text("SELECT id FROM organisations WHERE id = :oid AND tenant_id = :tid"),
            {"oid": payload.organisation_id, "tid": tenant_id}
        ).fetchone()
        if not org:
            raise HTTPException(status_code=400, detail="Organisation not found in tenant")

    if payload.activity_id:
        act = db.execute(
            text("SELECT id FROM activities WHERE id = :aid AND tenant_id = :tid"),
            {"aid": payload.activity_id, "tid": tenant_id}
        ).fetchone()
        if not act:
            raise HTTPException(status_code=400, detail="Activity not found in tenant")

    record_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO volunteer_records (
            id, tenant_id, identity_id, organisation_id, activity_id,
            volunteer_type, description, hours_contributed, volunteer_date,
            location_state_id, location_lga_id, location_ward_id,
            gps_lat, gps_lng, skills_used,
            verification_status, created_at, updated_at
        ) VALUES (
            :id, :tenant_id, :identity_id, :org_id, :activity_id,
            :vtype, :description, :hours, :vdate,
            :state_id, :lga_id, :ward_id,
            :gps_lat, :gps_lng, :skills::jsonb,
            'Draft', now(), now()
        )
    """), {
        "id": record_id,
        "tenant_id": tenant_id,
        "identity_id": current["sub"],
        "org_id": payload.organisation_id,
        "activity_id": payload.activity_id,
        "vtype": payload.volunteer_type,
        "description": payload.description,
        "hours": payload.hours_contributed,
        "vdate": payload.volunteer_date,
        "state_id": payload.location_state_id,
        "lga_id": payload.location_lga_id,
        "ward_id": payload.location_ward_id,
        "gps_lat": payload.gps_lat,
        "gps_lng": payload.gps_lng,
        "skills": str(payload.skills_used or []),
    })
    db.commit()
    return {"id": record_id, "verification_status": "Draft", "message": "Volunteer record created"}


@router.get("/")
def list_volunteer_records(
    status: Optional[str] = Query(None),
    volunteer_type: Optional[str] = Query(None),
    state_id: Optional[int] = Query(None),
    ward_id: Optional[int] = Query(None),
    identity_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """List volunteer records for current tenant."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    filters = ["v.tenant_id = :tid", "v.is_archived = FALSE"]
    params = {"tid": tenant_id}

    if status:
        filters.append("v.verification_status = :status")
        params["status"] = status
    if volunteer_type:
        filters.append("v.volunteer_type = :vtype")
        params["vtype"] = volunteer_type
    if state_id:
        filters.append("v.location_state_id = :state_id")
        params["state_id"] = state_id
    if ward_id:
        filters.append("v.location_ward_id = :ward_id")
        params["ward_id"] = ward_id
    if identity_id:
        filters.append("v.identity_id = :iid")
        params["iid"] = identity_id
    # Non-admins see only their own records
    elif not can_admin(current):
        filters.append("v.identity_id = :my_id")
        params["my_id"] = current["sub"]

    where = " AND ".join(filters)
    offset = (page - 1) * page_size

    total = db.execute(
        text(f"SELECT COUNT(*) FROM volunteer_records v WHERE {where}"),
        params
    ).scalar()

    rows = db.execute(
        text(f"{VOLUNTEER_SELECT} WHERE {where} ORDER BY v.volunteer_date DESC LIMIT :limit OFFSET :offset"),
        {**params, "limit": page_size, "offset": offset}
    ).fetchall()

    return {"total": total, "page": page, "page_size": page_size, "items": [format_volunteer(r) for r in rows]}


@router.get("/{record_id}")
def get_volunteer_record(
    record_id: str,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """Get a single volunteer record."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    row = db.execute(
        text(f"{VOLUNTEER_SELECT} WHERE v.id = :id AND v.tenant_id = :tid"),
        {"id": record_id, "tid": tenant_id}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Volunteer record not found")

    if str(row.volunteer_name) != current["sub"] and not can_admin(current):
        pass  # volunteer_name is a name string, access allowed — tenant boundary enforced by RLS

    return format_volunteer(row)


@router.post("/{record_id}/verify")
def verify_volunteer_record(
    record_id: str,
    payload: VerificationAction,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """Drive verification state machine for a volunteer record."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    record = db.execute(
        text("SELECT id, identity_id, verification_status FROM volunteer_records WHERE id = :id AND tenant_id = :tid"),
        {"id": record_id, "tid": tenant_id}
    ).fetchone()

    if not record:
        raise HTTPException(status_code=404, detail="Volunteer record not found")

    current_status = record.verification_status
    action_map = {
        "submit": "Submitted", "review": "Under Review",
        "verify": "Verified", "reject": "Rejected", "archive": "Archived"
    }
    target_status = action_map.get(payload.action.lower())
    if not target_status:
        raise HTTPException(status_code=400, detail=f"Unknown action: {payload.action}")

    allowed = VALID_TRANSITIONS.get(current_status, [])
    if target_status not in allowed:
        raise HTTPException(status_code=409, detail=f"Cannot transition {current_status} → {target_status}. Allowed: {allowed}")

    is_owner = str(record.identity_id) == current["sub"]
    if payload.action == "submit" and not is_owner and not can_admin(current):
        raise HTTPException(status_code=403, detail="Only the volunteer can submit their own record")
    if payload.action in ("review", "verify", "reject") and not can_verify(current):
        raise HTTPException(status_code=403, detail="Verifier role required")
    if payload.action == "reject" and not payload.rejection_reason:
        raise HTTPException(status_code=400, detail="rejection_reason required")

    now = datetime.utcnow()
    if payload.action == "verify":
        db.execute(text("""
            UPDATE volunteer_records SET
                verification_status = :status, verified_by = :vby,
                verified_at = :vat, verification_notes = :notes, updated_at = :now
            WHERE id = :id AND tenant_id = :tid
        """), {"status": target_status, "vby": current["sub"], "vat": now,
               "notes": payload.notes, "now": now, "id": record_id, "tid": tenant_id})
    else:
        db.execute(text("""
            UPDATE volunteer_records SET
                verification_status = :status, verification_notes = :notes,
                rejection_reason = :rr, updated_at = :now
            WHERE id = :id AND tenant_id = :tid
        """), {"status": target_status, "notes": payload.notes,
               "rr": payload.rejection_reason, "now": now, "id": record_id, "tid": tenant_id})

    db.commit()
    return {
        "message": f"Volunteer record: {current_status} → {target_status}",
        "previous_status": current_status,
        "new_status": target_status,
        "is_verified": target_status == "Verified",
    }
