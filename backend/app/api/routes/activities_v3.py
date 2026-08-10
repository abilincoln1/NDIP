"""
NDIP on Orion Platform Kernel
/api/v3/activities/ — Activity Engine
Phase D5A-S4

Orion Kernel capability — domain-agnostic activity infrastructure.
Supports all tenant types: political, civic, academic, NGO, business, government, independent.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import uuid
import json

from app.db.database import SessionLocal
from app.api.routes.auth_v3 import get_current_v3_identity, get_db

router = APIRouter(prefix="/api/v3/activities", tags=["v3-activities"])

# Valid verification state transitions (from workflow_definitions)
VALID_TRANSITIONS = {
    "Draft":        ["Submitted"],
    "Submitted":    ["Under Review"],
    "Under Review": ["Verified", "Rejected"],
    "Rejected":     ["Submitted", "Archived"],
    "Verified":     ["Archived"],
    "Archived":     [],
}


# ── Guards ─────────────────────────────────────────────────────────────────────

def require_active_membership(current: dict, db: Session, tenant_id: str):
    """Verify identity has active membership in tenant."""
    try:
        membership = db.execute(
            text("""
                SELECT m.id, m.status FROM memberships m
                WHERE m.identity_id = :iid AND m.tenant_id = :tid AND m.status = 'active'
                LIMIT 1
            """),
            {"iid": current["sub"], "tid": tenant_id}
        ).fetchone()
        if not membership:
            raise HTTPException(status_code=403, detail="Active membership required")
        return membership
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=403, detail="Membership verification failed")


def can_verify(current: dict) -> bool:
    roles = current.get("roles", [])
    return any(r in roles for r in ["verifier", "chapter_admin", "national_director", "super_admin"])


def can_admin(current: dict) -> bool:
    roles = current.get("roles", [])
    return any(r in roles for r in ["chapter_admin", "national_director", "super_admin"]) or \
           current.get("admin_level") is not None


# ── Schemas ────────────────────────────────────────────────────────────────────

class ActivityCreate(BaseModel):
    activity_type: str          # name of activity type (e.g. 'ward_visit')
    title: str
    description: Optional[str] = None
    activity_date: date
    activity_details: Optional[dict] = {}
    organisation_id: Optional[str] = None
    # Geographic — all optional
    location_country_iso: Optional[str] = None
    location_state_id: Optional[int] = None
    location_lga_id: Optional[int] = None
    location_ward_id: Optional[int] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    location_text: Optional[str] = None


class ActivityUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    activity_date: Optional[date] = None
    activity_details: Optional[dict] = None
    location_state_id: Optional[int] = None
    location_lga_id: Optional[int] = None
    location_ward_id: Optional[int] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    location_text: Optional[str] = None


class VerificationAction(BaseModel):
    action: str          # "submit", "review", "verify", "reject", "archive"
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def set_tenant_context(db: Session, tenant_id: str):
    db.execute(text("SET LOCAL app.current_tenant_id = :tid"), {"tid": tenant_id})


def get_activity_type(db: Session, type_name: str):
    at = db.execute(
        text("SELECT id, name, requires_evidence, requires_location, detail_schema FROM activity_types WHERE name = :n"),
        {"n": type_name}
    ).fetchone()
    if not at:
        raise HTTPException(status_code=400, detail=f"Unknown activity type: {type_name}")
    return at


def format_activity(row) -> dict:
    return {
        "id": str(row.id),
        "title": row.title,
        "description": row.description,
        "activity_type": row.type_name,
        "activity_date": row.activity_date.isoformat() if row.activity_date else None,
        "activity_details": row.activity_details or {},
        "organisation": row.org_name,
        "recorded_by_name": row.recorded_by_name,
        "verification_status": row.verification_status,
        "is_verified": row.verification_status == "Verified",
        "verified_by_name": row.verified_by_name,
        "verified_at": row.verified_at.isoformat() if row.verified_at else None,
        "verification_notes": row.verification_notes,
        "rejection_reason": row.rejection_reason,
        "geography": {
            "state": row.state_name,
            "lga": row.lga_name,
            "ward": row.ward_name,
            "gps_lat": row.gps_lat,
            "gps_lng": row.gps_lng,
            "location_text": row.location_text,
        },
        "tenant_id": str(row.tenant_id),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
        "is_archived": row.is_archived,
    }


ACTIVITY_SELECT = """
    SELECT
        a.id, a.title, a.description, a.activity_date, a.activity_details,
        a.verification_status, a.verified_at, a.verification_notes,
        a.rejection_reason, a.submitted_at, a.created_at, a.is_archived,
        a.gps_lat, a.gps_lng, a.location_text, a.tenant_id,
        at.name AS type_name,
        o.name AS org_name,
        pi.full_name AS recorded_by_name,
        piv.full_name AS verified_by_name,
        s.name AS state_name,
        l.name AS lga_name,
        w.name AS ward_name
    FROM activities a
    JOIN activity_types at ON at.id = a.activity_type_id
    LEFT JOIN organisations o ON o.id = a.organisation_id
    JOIN platform_identities pi ON pi.id = a.recorded_by
    LEFT JOIN platform_identities piv ON piv.id = a.verified_by
    LEFT JOIN ng_states s ON s.id = a.location_state_id
    LEFT JOIN ng_lgas l ON l.id = a.location_lga_id
    LEFT JOIN ng_wards w ON w.id = a.location_ward_id
"""


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/", status_code=201)
def create_activity(
    payload: ActivityCreate,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """
    Create a new activity record.
    Orion Kernel capability — works for any tenant type.
    """
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)
    require_active_membership(current, db, tenant_id)

    # Resolve activity type
    at = get_activity_type(db, payload.activity_type)

    # Resolve country
    country_id = None
    if payload.location_country_iso:
        country = db.execute(
            text("SELECT id FROM countries WHERE iso_code = :iso"),
            {"iso": payload.location_country_iso.upper()}
        ).fetchone()
        if country:
            country_id = str(country.id)

    # Validate organisation belongs to tenant
    if payload.organisation_id:
        org = db.execute(
            text("SELECT id FROM organisations WHERE id = :oid AND tenant_id = :tid"),
            {"oid": payload.organisation_id, "tid": tenant_id}
        ).fetchone()
        if not org:
            raise HTTPException(status_code=400, detail="Organisation not found in tenant")

    activity_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO activities (
            id, tenant_id, recorded_by, organisation_id, activity_type_id,
            title, description, activity_date, activity_details,
            location_country_id, location_state_id, location_lga_id, location_ward_id,
            gps_lat, gps_lng, location_text,
            verification_status, created_at, updated_at
        ) VALUES (
            :id, :tenant_id, :recorded_by, :org_id, :type_id,
            :title, :description, :activity_date, CAST(:details AS jsonb),
            :country_id, :state_id, :lga_id, :ward_id,
            :gps_lat, :gps_lng, :location_text,
            'Draft', now(), now()
        )
    """), {
        "id": activity_id,
        "tenant_id": tenant_id,
        "recorded_by": current["sub"],
        "org_id": payload.organisation_id,
        "type_id": str(at.id),
        "title": payload.title,
        "description": payload.description,
        "activity_date": payload.activity_date,
        "details": json.dumps(payload.activity_details or {}),
        "country_id": country_id,
        "state_id": payload.location_state_id,
        "lga_id": payload.location_lga_id,
        "ward_id": payload.location_ward_id,
        "gps_lat": payload.gps_lat,
        "gps_lng": payload.gps_lng,
        "location_text": payload.location_text,
    })
    db.commit()

    return {"id": activity_id, "verification_status": "Draft", "message": "Activity created"}


@router.get("/")
def list_activities(
    status: Optional[str] = Query(None),
    activity_type: Optional[str] = Query(None),
    state_id: Optional[int] = Query(None),
    lga_id: Optional[int] = Query(None),
    ward_id: Optional[int] = Query(None),
    organisation_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """List activities for current tenant with filtering."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    filters = ["a.tenant_id = :tid", "a.is_archived = FALSE"]
    params = {"tid": tenant_id}

    if status:
        filters.append("a.verification_status = :status")
        params["status"] = status
    if activity_type:
        filters.append("at.name = :atype")
        params["atype"] = activity_type
    if state_id:
        filters.append("a.location_state_id = :state_id")
        params["state_id"] = state_id
    if lga_id:
        filters.append("a.location_lga_id = :lga_id")
        params["lga_id"] = lga_id
    if ward_id:
        filters.append("a.location_ward_id = :ward_id")
        params["ward_id"] = ward_id
    if organisation_id:
        filters.append("a.organisation_id = :org_id")
        params["org_id"] = organisation_id

    where = " AND ".join(filters)
    offset = (page - 1) * page_size

    total = db.execute(
        text(f"SELECT COUNT(*) FROM activities a JOIN activity_types at ON at.id = a.activity_type_id WHERE {where}"),
        params
    ).scalar()

    rows = db.execute(
        text(f"{ACTIVITY_SELECT} WHERE {where} ORDER BY a.activity_date DESC, a.created_at DESC LIMIT :limit OFFSET :offset"),
        {**params, "limit": page_size, "offset": offset}
    ).fetchall()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [format_activity(r) for r in rows]
    }


@router.get("/{activity_id}")
def get_activity(
    activity_id: str,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """Get a single activity by ID."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    row = db.execute(
        text(f"{ACTIVITY_SELECT} WHERE a.id = :id AND a.tenant_id = :tid"),
        {"id": activity_id, "tid": tenant_id}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Activity not found")

    return format_activity(row)


@router.patch("/{activity_id}")
def update_activity(
    activity_id: str,
    payload: ActivityUpdate,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """Update a Draft activity. Only recorder or admin can update."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    activity = db.execute(
        text("SELECT id, recorded_by, verification_status FROM activities WHERE id = :id AND tenant_id = :tid"),
        {"id": activity_id, "tid": tenant_id}
    ).fetchone()

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    if activity.verification_status not in ("Draft", "Rejected"):
        raise HTTPException(status_code=409, detail=f"Cannot edit activity in status: {activity.verification_status}")
    if str(activity.recorded_by) != current["sub"] and not can_admin(current):
        raise HTTPException(status_code=403, detail="Only the recorder or an admin can edit this activity")

    updates = {"updated_at": datetime.utcnow(), "id": activity_id, "tid": tenant_id}
    set_parts = ["updated_at = :updated_at"]

    if payload.title is not None:
        updates["title"] = payload.title
        set_parts.append("title = :title")
    if payload.description is not None:
        updates["description"] = payload.description
        set_parts.append("description = :description")
    if payload.activity_date is not None:
        updates["activity_date"] = payload.activity_date
        set_parts.append("activity_date = :activity_date")
    if payload.activity_details is not None:
        updates["details"] = str(payload.activity_details)
        set_parts.append("activity_details = CAST(:details AS jsonb)")
    if payload.location_state_id is not None:
        updates["state_id"] = payload.location_state_id
        set_parts.append("location_state_id = :state_id")
    if payload.location_lga_id is not None:
        updates["lga_id"] = payload.location_lga_id
        set_parts.append("location_lga_id = :lga_id")
    if payload.location_ward_id is not None:
        updates["ward_id"] = payload.location_ward_id
        set_parts.append("location_ward_id = :ward_id")
    if payload.gps_lat is not None:
        updates["gps_lat"] = payload.gps_lat
        set_parts.append("gps_lat = :gps_lat")
    if payload.gps_lng is not None:
        updates["gps_lng"] = payload.gps_lng
        set_parts.append("gps_lng = :gps_lng")
    if payload.location_text is not None:
        updates["location_text"] = payload.location_text
        set_parts.append("location_text = :location_text")

    db.execute(
        text(f"UPDATE activities SET {', '.join(set_parts)} WHERE id = :id AND tenant_id = :tid"),
        updates
    )
    db.commit()
    return {"message": "Activity updated"}


@router.post("/{activity_id}/verify")
def verify_activity(
    activity_id: str,
    payload: VerificationAction,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """
    Drive the verification state machine.
    Actions: submit, review, verify, reject, archive
    Enforces valid transitions from workflow_definitions.
    Clearly distinguishes self-reported from verified records.
    """
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    activity = db.execute(
        text("SELECT id, recorded_by, verification_status FROM activities WHERE id = :id AND tenant_id = :tid"),
        {"id": activity_id, "tid": tenant_id}
    ).fetchone()

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    current_status = activity.verification_status
    action = payload.action.lower()

    # Map action to target status
    action_map = {
        "submit": "Submitted",
        "review": "Under Review",
        "verify": "Verified",
        "reject": "Rejected",
        "archive": "Archived",
    }
    target_status = action_map.get(action)
    if not target_status:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}. Valid: {list(action_map.keys())}")

    # Validate transition
    allowed = VALID_TRANSITIONS.get(current_status, [])
    if target_status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot transition from '{current_status}' to '{target_status}'. Allowed: {allowed}"
        )

    # Permission checks
    is_recorder = str(activity.recorded_by) == current["sub"]

    if action == "submit" and not is_recorder and not can_admin(current):
        raise HTTPException(status_code=403, detail="Only the recorder can submit")
    if action in ("review", "verify", "reject") and not can_verify(current):
        raise HTTPException(status_code=403, detail="Verifier role required")
    if action == "archive" and not can_admin(current):
        raise HTTPException(status_code=403, detail="Admin role required to archive")

    # Rejection requires reason
    if action == "reject" and not payload.rejection_reason:
        raise HTTPException(status_code=400, detail="rejection_reason required when rejecting")

    now = datetime.utcnow()
    updates = {
        "id": activity_id,
        "tid": tenant_id,
        "status": target_status,
        "updated_at": now,
        "notes": payload.notes,
        "rejection_reason": payload.rejection_reason,
    }

    if action == "submit":
        db.execute(text("""
            UPDATE activities SET
                verification_status = :status,
                submitted_at = :updated_at,
                updated_at = :updated_at
            WHERE id = :id AND tenant_id = :tid
        """), updates)
    elif action == "verify":
        updates["verified_by"] = current["sub"]
        updates["verified_at"] = now
        db.execute(text("""
            UPDATE activities SET
                verification_status = :status,
                verified_by = :verified_by,
                verified_at = :verified_at,
                verification_notes = :notes,
                updated_at = :updated_at
            WHERE id = :id AND tenant_id = :tid
        """), updates)
    elif action == "reject":
        db.execute(text("""
            UPDATE activities SET
                verification_status = :status,
                verification_notes = :notes,
                rejection_reason = :rejection_reason,
                updated_at = :updated_at
            WHERE id = :id AND tenant_id = :tid
        """), updates)
    else:
        db.execute(text("""
            UPDATE activities SET
                verification_status = :status,
                verification_notes = :notes,
                updated_at = :updated_at
            WHERE id = :id AND tenant_id = :tid
        """), updates)

    db.commit()

    return {
        "message": f"Activity status updated: {current_status} → {target_status}",
        "previous_status": current_status,
        "new_status": target_status,
        "is_verified": target_status == "Verified",
    }


@router.get("/types/list")
def list_activity_types(
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """List all available activity types with their schemas."""
    rows = db.execute(text("""
        SELECT id, name, description, requires_evidence, requires_location, detail_schema
        FROM activity_types ORDER BY name
    """)).fetchall()

    return [
        {
            "id": str(r.id),
            "name": r.name,
            "description": r.description,
            "requires_evidence": r.requires_evidence,
            "requires_location": r.requires_location,
            "detail_schema": r.detail_schema,
        }
        for r in rows
    ]
