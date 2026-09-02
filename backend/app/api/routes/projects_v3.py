"""
NDIP on Orion Platform Kernel
/api/v3/projects/ — Project Engine
Phase D5A-S5

Orion Kernel capability — domain-agnostic project infrastructure.
Visibility-aware access control per architect directive:
  private:           originator + explicitly authorised participants/admins
  participating_orgs: authorised members of participating organisations
  tenant:            appropriate tenant context
  public:            all authenticated users

platform_projects (v2) is UNTOUCHED — v2 routes unaffected.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import uuid, json

from app.db.database import SessionLocal
from app.api.routes.auth_v3 import get_current_v3_identity, get_db
from app.api.routes.activities_v3 import set_tenant_context, can_verify, can_admin

router = APIRouter(prefix="/api/v3/projects", tags=["v3-projects"])

VALID_TRANSITIONS = {
    "Draft":        ["Submitted", "Proposed"],
    "Proposed":     ["Under Review", "Draft"],
    "Submitted":    ["Under Review"],
    "Under Review": ["Approved", "Rejected", "Draft"],
    "Approved":     ["Active", "Under Review"],
    "Active":       ["Paused", "Completed", "Archived"],
    "Paused":       ["Active", "Cancelled", "Archived"],
    "Completed":    ["Archived"],
    "Cancelled":    ["Archived"],
    "Rejected":     ["Draft", "Archived"],
    "Archived":     [],
}

VERIFY_TRANSITIONS = {
    "Draft":        ["Submitted"],
    "Submitted":    ["Under Review"],
    "Under Review": ["Verified", "Rejected"],
    "Rejected":     ["Submitted", "Archived"],
    "Verified":     ["Archived"],
    "Archived":     [],
}


# ── Access control helpers ─────────────────────────────────────────────────────

def get_participant_org_ids(db: Session, identity_id: str) -> list:
    """Get all organisation IDs where this identity has active membership."""
    rows = db.execute(text("""
        SELECT DISTINCT organisation_id FROM memberships
        WHERE identity_id = :iid AND status = 'active'
    """), {"iid": identity_id}).fetchall()
    return [str(r.organisation_id) for r in rows if r.organisation_id]


def build_org_in_clause(org_ids: list) -> str:
    """Build a safe IN clause for org_ids — UUIDs only, no injection risk."""
    if not org_ids:
        return "('00000000-0000-0000-0000-000000000000')"
    # Validate UUID format before embedding
    import re
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    safe = [oid for oid in org_ids if uuid_pattern.match(oid.lower())]
    if not safe:
        return "('00000000-0000-0000-0000-000000000000')"
    return "(" + ",".join(f"'{oid}'" for oid in safe) + ")"


def can_access_project(db: Session, project: object, current: dict) -> bool:
    """
    Visibility-aware access check per architect directive.
    tenant_id IS NULL does NOT mean auto-visible to all.
    """
    identity_id = current["sub"]
    tenant_id = current.get("tenant_id")

    # Platform admin: full access
    if current.get("admin_level"):
        return True

    # Tenant-owned project: match tenant context
    if project.tenant_id is not None:
        return str(project.tenant_id) == tenant_id

    # Independent project (tenant_id IS NULL) — check visibility
    if project.visibility == "public":
        return True

    if project.visibility == "private":
        # Only originator or explicitly authorised participants
        if str(project.created_by) == identity_id:
            return True
        part = db.execute(text("""
            SELECT id FROM project_participants
            WHERE project_id = :pid AND identity_id = :iid AND status = 'active'
        """), {"pid": str(project.id), "iid": identity_id}).fetchone()
        return part is not None

    if project.visibility in ("participating_orgs", "tenant"):
        # Check if identity participates directly or via organisation
        my_org_ids = get_participant_org_ids(db, identity_id)
        org_in2 = build_org_in_clause(my_org_ids)
        part = db.execute(text(f"""
            SELECT id FROM project_participants
            WHERE project_id = :pid AND status = 'active'
            AND (
                identity_id = :iid
                OR organisation_id IN {org_in2}
            )
        """), {
            "pid": str(project.id),
            "iid": identity_id,
        }).fetchone()
        return part is not None

    return False


def require_active_membership(current: dict, db: Session, tenant_id: str):
    membership = db.execute(text("""
        SELECT id FROM memberships
        WHERE identity_id = :iid AND tenant_id = :tid AND status = 'active'
    """), {"iid": current["sub"], "tid": tenant_id}).fetchone()
    if not membership:
        raise HTTPException(status_code=403, detail="Active membership required")


# ── Schemas ────────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    project_type: str = "standard"
    visibility: str = "tenant"
    is_independent: bool = False        # True → tenant_id = NULL
    originating_org_id: Optional[str] = None
    geo_scope: str = "unspecified"
    location_state_id: Optional[int] = None
    location_lga_id: Optional[int] = None
    location_ward_id: Optional[int] = None
    start_date: Optional[date] = None
    target_end_date: Optional[date] = None
    sdg_alignment: Optional[list] = []
    outcomes: Optional[dict] = {}


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[str] = None
    geo_scope: Optional[str] = None
    location_state_id: Optional[int] = None
    location_lga_id: Optional[int] = None
    location_ward_id: Optional[int] = None
    start_date: Optional[date] = None
    target_end_date: Optional[date] = None
    end_date: Optional[date] = None
    sdg_alignment: Optional[list] = None
    outcomes: Optional[dict] = None


class StatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class VerificationAction(BaseModel):
    action: str
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class ParticipantAdd(BaseModel):
    organisation_id: Optional[str] = None
    identity_id: Optional[str] = None
    role_name: str = "partner"
    notes: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

PROJECT_SELECT = """
    SELECT
        p.id, p.tenant_id, p.originating_org_id, p.created_by,
        p.name, p.slug, p.description, p.project_type, p.status,
        p.visibility, p.geo_scope, p.sdg_alignment, p.outcomes,
        p.verification_status, p.verified_at, p.verification_notes,
        p.location_state_id, p.location_lga_id, p.location_ward_id,
        p.start_date, p.end_date, p.target_end_date,
        p.created_at, p.updated_at, p.submitted_at, p.is_archived,
        pi.full_name AS created_by_name,
        o.name AS originating_org_name,
        s.name AS state_name,
        l.name AS lga_name,
        w.name AS ward_name
    FROM projects p
    JOIN platform_identities pi ON pi.id = p.created_by
    LEFT JOIN organisations o ON o.id = p.originating_org_id
    LEFT JOIN ng_states s ON s.id = p.location_state_id
    LEFT JOIN ng_lgas l ON l.id = p.location_lga_id
    LEFT JOIN ng_wards w ON w.id = p.location_ward_id
"""


def format_project(row, participant_count: int = 0) -> dict:
    return {
        "id": str(row.id),
        "name": row.name,
        "slug": row.slug,
        "description": row.description,
        "project_type": row.project_type,
        "status": row.status,
        "visibility": row.visibility,
        "is_independent": row.tenant_id is None,
        "tenant_id": str(row.tenant_id) if row.tenant_id else None,
        "originating_org": row.originating_org_name,
        "created_by_name": row.created_by_name,
        "verification_status": row.verification_status,
        "verified_at": row.verified_at.isoformat() if row.verified_at else None,
        "geography": {
            "geo_scope": row.geo_scope,
            "state": row.state_name,
            "lga": row.lga_name,
            "ward": row.ward_name,
        },
        "sdg_alignment": row.sdg_alignment or [],
        "outcomes": row.outcomes or {},
        "start_date": row.start_date.isoformat() if row.start_date else None,
        "end_date": row.end_date.isoformat() if row.end_date else None,
        "target_end_date": row.target_end_date.isoformat() if row.target_end_date else None,
        "participant_count": participant_count,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
        "is_archived": row.is_archived,
    }


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/", status_code=201)
def create_project(
    payload: ProjectCreate,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """
    Create a project.
    is_independent=True → tenant_id=NULL (independent/cross-tenant project)
    is_independent=False → tenant_id set to current tenant
    """
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)
    require_active_membership(current, db, tenant_id)

    # Independent project: not tenant-owned
    project_tenant_id = None if payload.is_independent else tenant_id

    # Validate originating org belongs to tenant
    if payload.originating_org_id and not payload.is_independent:
        org = db.execute(text("""
            SELECT id FROM organisations WHERE id = :oid AND tenant_id = :tid
        """), {"oid": payload.originating_org_id, "tid": tenant_id}).fetchone()
        if not org:
            raise HTTPException(status_code=400, detail="Organisation not found in tenant")

    # Generate slug from name
    slug_base = payload.name.lower().replace(' ', '-')[:50]
    slug = f"{slug_base}-{str(uuid.uuid4())[:8]}"

    project_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO projects (
            id, tenant_id, originating_org_id, created_by,
            name, slug, description, project_type, status, visibility,
            geo_scope, location_state_id, location_lga_id, location_ward_id,
            sdg_alignment, outcomes, start_date, target_end_date,
            verification_status, created_at, updated_at
        ) VALUES (
            :id, :tenant_id, :org_id, :created_by,
            :name, :slug, :description, :project_type, 'Draft', :visibility,
            :geo_scope, :state_id, :lga_id, :ward_id,
            CAST(:sdg AS jsonb), CAST(:outcomes AS jsonb), :start_date, :target_end_date,
            'Draft', now(), now()
        )
    """), {
        "id": project_id,
        "tenant_id": project_tenant_id,
        "org_id": payload.originating_org_id,
        "created_by": current["sub"],
        "name": payload.name,
        "slug": slug,
        "description": payload.description,
        "project_type": payload.project_type,
        "visibility": payload.visibility,
        "geo_scope": payload.geo_scope,
        "state_id": payload.location_state_id,
        "lga_id": payload.location_lga_id,
        "ward_id": payload.location_ward_id,
        "sdg": json.dumps(payload.sdg_alignment or []),
        "outcomes": json.dumps(payload.outcomes or {}),
        "start_date": payload.start_date,
        "target_end_date": payload.target_end_date,
    })

    # Auto-add creator as originator participant
    role = db.execute(text("SELECT id FROM project_roles WHERE name = 'originator'")).fetchone()
    if role:
        db.execute(text("""
            INSERT INTO project_participants
                (id, project_id, identity_id, role_id, status, joined_at, added_by, created_at, updated_at)
            VALUES
                (:id, :pid, :iid, :rid, 'active', now(), :iid, now(), now())
        """), {
            "id": str(uuid.uuid4()),
            "pid": project_id,
            "iid": current["sub"],
            "rid": str(role.id),
        })

    db.commit()
    return {
        "id": project_id,
        "slug": slug,
        "status": "Draft",
        "is_independent": payload.is_independent,
        "message": "Project created"
    }


@router.get("/")
def list_projects(
    status: Optional[str] = Query(None),
    project_type: Optional[str] = Query(None),
    is_independent: Optional[bool] = Query(None),
    state_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """
    List projects accessible to the current user.
    Includes: tenant-owned projects + public independent projects
    + participating_orgs/private projects where user is a participant.
    """
    tenant_id = current["tenant_id"]
    identity_id = current["sub"]
    set_tenant_context(db, tenant_id)

    my_org_ids = get_participant_org_ids(db, identity_id)

    filters = ["p.is_archived = FALSE"]
    params = {
        "tid": tenant_id,
        "iid": identity_id,
    }

    # Visibility-aware filter — build dynamic org IN clause (no SQLAlchemy array issue)
    org_in = build_org_in_clause(my_org_ids)
    filters.append(f"""(
        p.tenant_id = :tid
        OR (p.tenant_id IS NULL AND p.visibility = 'public')
        OR (p.tenant_id IS NULL AND p.visibility IN ('participating_orgs','tenant') AND EXISTS (
            SELECT 1 FROM project_participants pp
            WHERE pp.project_id = p.id AND pp.status = 'active'
            AND (pp.identity_id = :iid OR pp.organisation_id IN {org_in})
        ))
        OR (p.tenant_id IS NULL AND p.visibility = 'private' AND (
            p.created_by = :iid OR EXISTS (
                SELECT 1 FROM project_participants pp
                WHERE pp.project_id = p.id AND pp.status = 'active'
                AND pp.identity_id = :iid
            )
        ))
    )""")

    if status:
        filters.append("p.status = :status")
        params["status"] = status
    if project_type:
        filters.append("p.project_type = :ptype")
        params["ptype"] = project_type
    if is_independent is True:
        filters.append("p.tenant_id IS NULL")
    elif is_independent is False:
        filters.append("p.tenant_id IS NOT NULL")
    if state_id:
        filters.append("p.location_state_id = :state_id")
        params["state_id"] = state_id

    where = " AND ".join(filters)
    offset = (page - 1) * page_size

    total = db.execute(
        text(f"SELECT COUNT(*) FROM projects p WHERE {where}"), params
    ).scalar()

    rows = db.execute(
        text(f"{PROJECT_SELECT} WHERE {where} ORDER BY p.created_at DESC LIMIT :limit OFFSET :offset"),
        {**params, "limit": page_size, "offset": offset}
    ).fetchall()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [format_project(r) for r in rows]
    }


@router.get("/roles/list")
def list_project_roles(
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """List all project roles."""
    rows = db.execute(text("SELECT id, name, description FROM project_roles ORDER BY name")).fetchall()
    return [{"id": str(r.id), "name": r.name, "description": r.description} for r in rows]


@router.get("/{project_id}")
def get_project(
    project_id: str,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """Get project detail — visibility-aware access check."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    row = db.execute(
        text(f"{PROJECT_SELECT} WHERE p.id = :id"), {"id": project_id}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

    if not can_access_project(db, row, current):
        raise HTTPException(status_code=403, detail="Access denied")

    part_count = db.execute(text("""
        SELECT COUNT(*) FROM project_participants
        WHERE project_id = :pid AND status = 'active'
    """), {"pid": project_id}).scalar()

    return format_project(row, part_count)


@router.patch("/{project_id}")
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """Update a project — creator or admin only, Draft/Proposed status."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    project = db.execute(
        text("SELECT id, created_by, status, tenant_id, visibility FROM projects WHERE id = :id"),
        {"id": project_id}
    ).fetchone()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not can_access_project(db, project, current):
        raise HTTPException(status_code=403, detail="Access denied")
    if project.status not in ("Draft", "Proposed", "Rejected"):
        raise HTTPException(status_code=409, detail=f"Cannot edit project in status: {project.status}")
    if str(project.created_by) != current["sub"] and not can_admin(current):
        raise HTTPException(status_code=403, detail="Only the creator or admin can edit this project")

    updates = {"id": project_id, "updated_at": datetime.utcnow()}
    set_parts = ["updated_at = :updated_at"]

    if payload.name is not None:
        updates["name"] = payload.name
        set_parts.append("name = :name")
    if payload.description is not None:
        updates["description"] = payload.description
        set_parts.append("description = :description")
    if payload.visibility is not None:
        updates["visibility"] = payload.visibility
        set_parts.append("visibility = :visibility")
    if payload.geo_scope is not None:
        updates["geo_scope"] = payload.geo_scope
        set_parts.append("geo_scope = :geo_scope")
    if payload.location_state_id is not None:
        updates["state_id"] = payload.location_state_id
        set_parts.append("location_state_id = :state_id")
    if payload.location_lga_id is not None:
        updates["lga_id"] = payload.location_lga_id
        set_parts.append("location_lga_id = :lga_id")
    if payload.location_ward_id is not None:
        updates["ward_id"] = payload.location_ward_id
        set_parts.append("location_ward_id = :ward_id")
    if payload.start_date is not None:
        updates["start_date"] = payload.start_date
        set_parts.append("start_date = :start_date")
    if payload.target_end_date is not None:
        updates["target_end_date"] = payload.target_end_date
        set_parts.append("target_end_date = :target_end_date")
    if payload.end_date is not None:
        updates["end_date"] = payload.end_date
        set_parts.append("end_date = :end_date")
    if payload.sdg_alignment is not None:
        updates["sdg"] = json.dumps(payload.sdg_alignment)
        set_parts.append("sdg_alignment = CAST(:sdg AS jsonb)")
    if payload.outcomes is not None:
        updates["outcomes"] = json.dumps(payload.outcomes)
        set_parts.append("outcomes = CAST(:outcomes AS jsonb)")

    db.execute(
        text(f"UPDATE projects SET {', '.join(set_parts)} WHERE id = :id"),
        updates
    )
    db.commit()
    return {"message": "Project updated"}


@router.post("/{project_id}/status")
def update_project_status(
    project_id: str,
    payload: StatusUpdate,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """Drive project lifecycle state machine."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    project = db.execute(
        text("SELECT id, created_by, status, tenant_id, visibility FROM projects WHERE id = :id"),
        {"id": project_id}
    ).fetchone()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not can_access_project(db, project, current):
        raise HTTPException(status_code=403, detail="Access denied")

    allowed = VALID_TRANSITIONS.get(project.status, [])
    if payload.status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot transition from '{project.status}' to '{payload.status}'. Allowed: {allowed}"
        )

    # Only creator or admin can advance status
    if str(project.created_by) != current["sub"] and not can_admin(current):
        raise HTTPException(status_code=403, detail="Only creator or admin can change project status")

    db.execute(text("""
        UPDATE projects SET status = :status, updated_at = now() WHERE id = :id
    """), {"status": payload.status, "id": project_id})
    db.commit()

    return {"message": f"Status: {project.status} → {payload.status}", "new_status": payload.status}


@router.post("/{project_id}/verify")
def verify_project(
    project_id: str,
    payload: VerificationAction,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """Drive verification lifecycle — separate from project status."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    project = db.execute(
        text("SELECT id, created_by, verification_status, tenant_id, visibility FROM projects WHERE id = :id"),
        {"id": project_id}
    ).fetchone()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not can_access_project(db, project, current):
        raise HTTPException(status_code=403, detail="Access denied")

    action_map = {
        "submit": "Submitted", "review": "Under Review",
        "verify": "Verified", "reject": "Rejected", "archive": "Archived"
    }
    target = action_map.get(payload.action.lower())
    if not target:
        raise HTTPException(status_code=400, detail=f"Unknown action: {payload.action}")

    allowed = VERIFY_TRANSITIONS.get(project.verification_status, [])
    if target not in allowed:
        raise HTTPException(status_code=409,
            detail=f"Cannot transition {project.verification_status} → {target}. Allowed: {allowed}")

    is_creator = str(project.created_by) == current["sub"]
    if payload.action == "submit" and not is_creator and not can_admin(current):
        raise HTTPException(status_code=403, detail="Only creator can submit")
    if payload.action in ("review", "verify", "reject") and not can_verify(current):
        raise HTTPException(status_code=403, detail="Verifier role required")
    if payload.action == "reject" and not payload.rejection_reason:
        raise HTTPException(status_code=400, detail="rejection_reason required")

    now = datetime.utcnow()
    if payload.action == "verify":
        db.execute(text("""
            UPDATE projects SET verification_status = :vs, verified_by = :vby,
            verified_at = :vat, verification_notes = :notes, updated_at = :now
            WHERE id = :id
        """), {"vs": target, "vby": current["sub"], "vat": now,
               "notes": payload.notes, "now": now, "id": project_id})
    else:
        db.execute(text("""
            UPDATE projects SET verification_status = :vs, verification_notes = :notes,
            rejection_reason = :rr, updated_at = :now WHERE id = :id
        """), {"vs": target, "notes": payload.notes,
               "rr": payload.rejection_reason, "now": now, "id": project_id})

    db.commit()
    return {
        "message": f"Verification: {project.verification_status} → {target}",
        "new_verification_status": target,
        "is_verified": target == "Verified",
    }


@router.post("/{project_id}/participants", status_code=201)
def add_participant(
    project_id: str,
    payload: ParticipantAdd,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """Add a participant (org or identity) to a project."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    project = db.execute(
        text("SELECT id, created_by, tenant_id, visibility FROM projects WHERE id = :id"),
        {"id": project_id}
    ).fetchone()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not can_access_project(db, project, current):
        raise HTTPException(status_code=403, detail="Access denied")
    if str(project.created_by) != current["sub"] and not can_admin(current):
        raise HTTPException(status_code=403, detail="Only creator or admin can add participants")
    if not payload.organisation_id and not payload.identity_id:
        raise HTTPException(status_code=400, detail="organisation_id or identity_id required")

    role = db.execute(text("SELECT id FROM project_roles WHERE name = :n"),
        {"n": payload.role_name}).fetchone()
    if not role:
        raise HTTPException(status_code=400, detail=f"Unknown role: {payload.role_name}")

    part_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO project_participants
            (id, project_id, organisation_id, identity_id, role_id,
             status, joined_at, notes, added_by, created_at, updated_at)
        VALUES
            (:id, :pid, :org_id, :iid, :rid,
             'active', now(), :notes, :added_by, now(), now())
        ON CONFLICT DO NOTHING
    """), {
        "id": part_id,
        "pid": project_id,
        "org_id": payload.organisation_id,
        "iid": payload.identity_id,
        "rid": str(role.id),
        "notes": payload.notes,
        "added_by": current["sub"],
    })
    db.commit()
    return {"id": part_id, "message": "Participant added"}


@router.get("/{project_id}/participants")
def list_participants(
    project_id: str,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """List project participants."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    project = db.execute(
        text("SELECT id, tenant_id, visibility FROM projects WHERE id = :id"),
        {"id": project_id}
    ).fetchone()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not can_access_project(db, project, current):
        raise HTTPException(status_code=403, detail="Access denied")

    rows = db.execute(text("""
        SELECT pp.id, pp.status, pp.joined_at, pp.notes,
               pr.name AS role_name,
               o.name AS org_name,
               pi.full_name AS identity_name
        FROM project_participants pp
        JOIN project_roles pr ON pr.id = pp.role_id
        LEFT JOIN organisations o ON o.id = pp.organisation_id
        LEFT JOIN platform_identities pi ON pi.id = pp.identity_id
        WHERE pp.project_id = :pid
        ORDER BY pp.joined_at
    """), {"pid": project_id}).fetchall()

    return [
        {
            "id": str(r.id),
            "role": r.role_name,
            "organisation": r.org_name,
            "identity": r.identity_name,
            "status": r.status,
            "joined_at": r.joined_at.isoformat() if r.joined_at else None,
            "notes": r.notes,
        }
        for r in rows
    ]


@router.get("/{project_id}/activities")
def list_project_activities(
    project_id: str,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """List activities linked to this project (tenant-scoped)."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    project = db.execute(
        text("SELECT id, tenant_id, visibility FROM projects WHERE id = :id"),
        {"id": project_id}
    ).fetchone()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not can_access_project(db, project, current):
        raise HTTPException(status_code=403, detail="Access denied")

    # Activities remain tenant-scoped even for shared projects
    rows = db.execute(text("""
        SELECT a.id, a.title, a.verification_status, a.activity_date,
               at.name AS activity_type,
               pi.full_name AS recorded_by_name
        FROM activities a
        JOIN activity_types at ON at.id = a.activity_type_id
        JOIN platform_identities pi ON pi.id = a.recorded_by
        WHERE a.project_id = :pid AND a.tenant_id = :tid AND a.is_archived = FALSE
        ORDER BY a.activity_date DESC
    """), {"pid": project_id, "tid": tenant_id}).fetchall()

    return [
        {
            "id": str(r.id),
            "title": r.title,
            "activity_type": r.activity_type,
            "activity_date": r.activity_date.isoformat() if r.activity_date else None,
            "verification_status": r.verification_status,
            "recorded_by": r.recorded_by_name,
        }
        for r in rows
    ]
