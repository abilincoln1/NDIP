"""
NDIP Phase D.3 — Platform Routes (D3.2)
File: app/api/routes/platform_routes.py

Consolidated router module for the remaining /api/v2/ endpoints:
  /api/v2/projects
  /api/v2/sponsorships
  /api/v2/ward-executives
  /api/v2/verification
  /api/v2/impact
  /api/v2/admin

Each section follows the same pattern:
  - Pydantic schemas (In/Out)
  - RBAC enforcement via require_member_role()
  - Pagination + filtering on list endpoints
  - Consistent {"ok": True, "data": ..., "meta": ...} envelope
  - Audit trail via audit_log (handled by middleware)
"""
import json
from typing import Optional
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.database import get_db
from app.core.member_rbac import get_current_member, require_member_role
from app.models.member import Member

# ─── Shared helpers ────────────────────────────────────────────────────────

def _ok(data, meta=None):
    return {"ok": True, "data": data, "meta": meta or {}}

def _row(row) -> dict:
    if row is None:
        return {}
    d = dict(row._mapping)
    for k, v in list(d.items()):
        if type(v).__name__ in ("UUID",):
            d[k] = str(v)
    return d

def _rows(rows) -> list:
    return [_row(r) for r in rows]

def _paginate(db, base_q, count_q, params, page, page_size):
    total = db.execute(text(count_q), params).scalar() or 0
    offset = (page - 1) * page_size
    data = db.execute(text(base_q + " LIMIT :limit OFFSET :offset"),
                      {**params, "limit": page_size, "offset": offset}).fetchall()
    return _rows(data), {
        "total": total, "page": page,
        "page_size": page_size,
        "total_pages": -(-total // page_size),
    }


# ═══════════════════════════════════════════════════════════════════════════
# PROJECTS  /api/v2/projects
# ═══════════════════════════════════════════════════════════════════════════

projects_router = APIRouter(prefix="/api/v2/projects", tags=["projects"])

PROJECT_TYPES = ["development","advocacy","cultural","educational","fundraising","health","other"]
PROJECT_STATUSES = ["draft","active","on_hold","completed","cancelled"]

class ProjectCreateIn(BaseModel):
    title: str = Field(..., min_length=3, max_length=500)
    description: str = Field(..., min_length=10)
    project_type: str
    sector: Optional[str] = None
    state_id: Optional[int] = None
    lga_id: Optional[int] = None
    ward_id: Optional[int] = None
    budget_naira: Optional[float] = Field(None, ge=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    tags: list[str] = []

class ProjectUpdateIn(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=500)
    description: Optional[str] = None
    project_type: Optional[str] = None
    sector: Optional[str] = None
    budget_naira: Optional[float] = Field(None, ge=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    tags: Optional[list[str]] = None

class StakeholderAddIn(BaseModel):
    member_id: UUID
    role: str  # owner, sponsor, funder, implementer, advisor, observer, verifier


@projects_router.post("/", status_code=201)
def create_project(p: ProjectCreateIn, member: Member = Depends(get_current_member), db: Session = Depends(get_db)):
    if p.project_type not in PROJECT_TYPES:
        raise HTTPException(400, f"Invalid project_type. Must be one of: {PROJECT_TYPES}")
    row = db.execute(text("""
        INSERT INTO platform_projects
            (created_by, chapter_id, title, description, project_type, sector,
             state_id, lga_id, ward_id, budget_naira, start_date, end_date,
             tags, status)
        VALUES
            (CAST(:mid AS UUID), CAST(:cid AS UUID), :title, :desc, :ptype, :sector,
             :state_id, :lga_id, :ward_id, :budget, :start_date, :end_date,
             CAST(:tags AS jsonb), 'draft')
        RETURNING *
    """), {
        "mid": str(member.id), "cid": str(member.chapter_id) if member.chapter_id else None,
        "title": p.title, "desc": p.description, "ptype": p.project_type,
        "sector": p.sector, "state_id": p.state_id, "lga_id": p.lga_id,
        "ward_id": p.ward_id, "budget": p.budget_naira,
        "start_date": p.start_date, "end_date": p.end_date,
        "tags": json.dumps(p.tags),
    }).fetchone()
    # Auto-add creator as owner stakeholder
    db.execute(text("""
        INSERT INTO project_stakeholders (project_id, member_id, role)
        VALUES (CAST(:pid AS UUID), CAST(:mid AS UUID), 'owner')
        ON CONFLICT DO NOTHING
    """), {"pid": str(row.id), "mid": str(member.id)})
    db.commit()
    return _ok(_row(row))


@projects_router.get("/")
def list_projects(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    project_status: Optional[str] = Query(None), project_type: Optional[str] = Query(None),
    _: Member = Depends(get_current_member), db: Session = Depends(get_db),
):
    conds = ["deleted_at IS NULL"]
    params = {}
    if project_status in PROJECT_STATUSES:
        conds.append("status = :status"); params["status"] = project_status
    if project_type in PROJECT_TYPES:
        conds.append("project_type = :ptype"); params["ptype"] = project_type
    where = "WHERE " + " AND ".join(conds)
    rows, meta = _paginate(db,
        f"SELECT * FROM platform_projects {where} ORDER BY created_at DESC",
        f"SELECT COUNT(*) FROM platform_projects {where}",
        params, page, page_size)
    return _ok(rows, meta)


@projects_router.get("/{project_id}")
def get_project(project_id: UUID, _: Member = Depends(get_current_member), db: Session = Depends(get_db)):
    row = db.execute(text("SELECT * FROM platform_projects WHERE id = CAST(:id AS UUID) AND deleted_at IS NULL"),
                     {"id": str(project_id)}).fetchone()
    if not row:
        raise HTTPException(404, "Project not found")
    stakeholders = db.execute(text("""
        SELECT ps.member_id, ps.role, m.full_name, m.membership_number
        FROM project_stakeholders ps JOIN members m ON ps.member_id = m.id
        WHERE ps.project_id = CAST(:pid AS UUID)
    """), {"pid": str(project_id)}).fetchall()
    result = _row(row)
    result["stakeholders"] = _rows(stakeholders)
    return _ok(result)


@projects_router.put("/{project_id}")
def update_project(
    project_id: UUID, payload: ProjectUpdateIn,
    member: Member = Depends(get_current_member), db: Session = Depends(get_db),
):
    row = db.execute(text("SELECT * FROM platform_projects WHERE id = CAST(:id AS UUID) AND deleted_at IS NULL"),
                     {"id": str(project_id)}).fetchone()
    if not row:
        raise HTTPException(404, "Project not found")
    if str(row.created_by) != str(member.id) and member.role not in ("chapter_admin","national_director","super_admin"):
        raise HTTPException(403, "Access denied")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _ok(_row(row))
    set_clauses = []
    params = {"id": str(project_id)}
    for k, v in updates.items():
        if k == "tags":
            set_clauses.append("tags = CAST(:tags AS jsonb)")
            params["tags"] = json.dumps(v)
        else:
            set_clauses.append(f"{k} = :{k}")
            params[k] = v
    set_clauses.append("updated_at = now()")
    db.execute(text(f"UPDATE platform_projects SET {', '.join(set_clauses)} WHERE id = CAST(:id AS UUID)"), params)
    db.commit()
    return _ok(_row(db.execute(text("SELECT * FROM platform_projects WHERE id = CAST(:id AS UUID)"),
                               {"id": str(project_id)}).fetchone()))


@projects_router.post("/{project_id}/stakeholders", status_code=201)
def add_stakeholder(
    project_id: UUID, payload: StakeholderAddIn,
    member: Member = Depends(get_current_member), db: Session = Depends(get_db),
):
    row = db.execute(text("SELECT created_by FROM platform_projects WHERE id = CAST(:id AS UUID) AND deleted_at IS NULL"),
                     {"id": str(project_id)}).fetchone()
    if not row:
        raise HTTPException(404, "Project not found")
    if str(row.created_by) != str(member.id) and member.role not in ("chapter_admin","national_director","super_admin"):
        raise HTTPException(403, "Only project owner or admin can add stakeholders")
    valid_roles = ("owner","sponsor","funder","implementer","advisor","observer","verifier")
    if payload.role not in valid_roles:
        raise HTTPException(400, f"Invalid role. Must be one of: {valid_roles}")
    db.execute(text("""
        INSERT INTO project_stakeholders (project_id, member_id, role)
        VALUES (CAST(:pid AS UUID), CAST(:mid AS UUID), :role)
        ON CONFLICT (project_id, member_id) DO UPDATE SET role = EXCLUDED.role
    """), {"pid": str(project_id), "mid": str(payload.member_id), "role": payload.role})
    db.commit()
    return _ok({"project_id": str(project_id), "member_id": str(payload.member_id), "role": payload.role})


# ═══════════════════════════════════════════════════════════════════════════
# SPONSORSHIPS  /api/v2/sponsorships
# ═══════════════════════════════════════════════════════════════════════════

sponsorships_router = APIRouter(prefix="/api/v2/sponsorships", tags=["sponsorships"])

SPONSORSHIP_TYPES = ["infrastructure","education","health","agriculture","youth","women","other"]
SPONSORSHIP_STATUSES = ["proposed","active","completed","cancelled","suspended"]

class SponsorshipCreateIn(BaseModel):
    ward_id: int
    sponsorship_type: str
    title: str = Field(..., min_length=3, max_length=500)
    description: Optional[str] = None
    budget_naira: Optional[float] = Field(None, ge=0)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    beneficiaries_count: int = Field(0, ge=0)


@sponsorships_router.post("/", status_code=201)
def create_sponsorship(
    p: SponsorshipCreateIn,
    member: Member = Depends(get_current_member), db: Session = Depends(get_db),
):
    if p.sponsorship_type not in SPONSORSHIP_TYPES:
        raise HTTPException(400, f"Invalid sponsorship_type. Must be one of: {SPONSORSHIP_TYPES}")
    row = db.execute(text("""
        INSERT INTO ward_sponsorships
            (sponsor_member_id, ward_id, sponsorship_type, title, description,
             budget_naira, start_date, end_date, beneficiaries_count, status)
        VALUES
            (CAST(:mid AS UUID), :ward_id, :stype, :title, :desc,
             :budget, :start_date, :end_date, :bcount, 'proposed')
        RETURNING *
    """), {
        "mid": str(member.id), "ward_id": p.ward_id,
        "stype": p.sponsorship_type, "title": p.title, "desc": p.description,
        "budget": p.budget_naira, "start_date": p.start_date, "end_date": p.end_date,
        "bcount": p.beneficiaries_count,
    }).fetchone()
    db.commit()
    return _ok(_row(row))


@sponsorships_router.get("/")
def list_sponsorships(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    ward_id: Optional[int] = None, stype: Optional[str] = Query(None, alias="type"),
    _: Member = Depends(get_current_member), db: Session = Depends(get_db),
):
    conds = []
    params = {}
    if ward_id:
        conds.append("ward_id = :ward_id"); params["ward_id"] = ward_id
    if stype in SPONSORSHIP_TYPES:
        conds.append("sponsorship_type = :stype"); params["stype"] = stype
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    rows, meta = _paginate(db,
        f"SELECT * FROM ward_sponsorships {where} ORDER BY created_at DESC",
        f"SELECT COUNT(*) FROM ward_sponsorships {where}",
        params, page, page_size)
    return _ok(rows, meta)


@sponsorships_router.get("/{sponsorship_id}")
def get_sponsorship(sponsorship_id: UUID, _: Member = Depends(get_current_member), db: Session = Depends(get_db)):
    row = db.execute(text("SELECT * FROM ward_sponsorships WHERE id = CAST(:id AS UUID)"), {"id": str(sponsorship_id)}).fetchone()
    if not row:
        raise HTTPException(404, "Sponsorship not found")
    return _ok(_row(row))


# ═══════════════════════════════════════════════════════════════════════════
# WARD EXECUTIVES  /api/v2/ward-executives
# ═══════════════════════════════════════════════════════════════════════════

ward_exec_router = APIRouter(prefix="/api/v2/ward-executives", tags=["ward_executives"])

class WardExecCreateIn(BaseModel):
    ward_id: int
    position: str = Field(..., min_length=3, max_length=200)
    party_affiliation: Optional[str] = None
    term_start: Optional[date] = None
    term_end: Optional[date] = None
    is_current: bool = True
    biography: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


@ward_exec_router.post("/", status_code=201)
def create_ward_exec(
    p: WardExecCreateIn,
    member: Member = Depends(get_current_member), db: Session = Depends(get_db),
):
    row = db.execute(text("""
        INSERT INTO ward_executives
            (member_id, ward_id, position, party_affiliation, term_start,
             term_end, is_current, biography, contact_email, contact_phone)
        VALUES
            (CAST(:mid AS UUID), :ward_id, :pos, :party, :tstart,
             :tend, :current, :bio, :email, :phone)
        RETURNING *
    """), {
        "mid": str(member.id), "ward_id": p.ward_id, "pos": p.position,
        "party": p.party_affiliation, "tstart": p.term_start,
        "tend": p.term_end, "current": p.is_current,
        "bio": p.biography, "email": p.contact_email, "phone": p.contact_phone,
    }).fetchone()
    db.commit()
    return _ok(_row(row))


@ward_exec_router.get("/")
def list_ward_execs(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    ward_id: Optional[int] = None, is_current: Optional[bool] = None,
    _: Member = Depends(get_current_member), db: Session = Depends(get_db),
):
    conds = ["deleted_at IS NULL"]
    params = {}
    if ward_id:
        conds.append("ward_id = :ward_id"); params["ward_id"] = ward_id
    if is_current is not None:
        conds.append("is_current = :is_current"); params["is_current"] = is_current
    where = "WHERE " + " AND ".join(conds)
    rows, meta = _paginate(db,
        f"SELECT * FROM ward_executives {where} ORDER BY created_at DESC",
        f"SELECT COUNT(*) FROM ward_executives {where}",
        params, page, page_size)
    return _ok(rows, meta)


@ward_exec_router.post("/{exec_id}/verify")
def verify_ward_exec(
    exec_id: UUID,
    member: Member = Depends(require_member_role("verifier","chapter_admin","national_director","super_admin")),
    db: Session = Depends(get_db),
):
    db.execute(text("""
        UPDATE ward_executives
        SET verification_status = 'verified',
            verified_by = CAST(:vid AS UUID),
            verified_at = now(),
            updated_at = now()
        WHERE id = CAST(:id AS UUID) AND deleted_at IS NULL
    """), {"vid": str(member.id), "id": str(exec_id)})
    db.commit()
    return _ok({"exec_id": str(exec_id), "verification_status": "verified"})


# ═══════════════════════════════════════════════════════════════════════════
# VERIFICATION  /api/v2/verification
# ═══════════════════════════════════════════════════════════════════════════

verification_router = APIRouter(prefix="/api/v2/verification", tags=["verification"])

SUBMISSION_TYPES = ["identity","credential","ward_executive","residence","employment"]

class VerificationSubmitIn(BaseModel):
    submission_type: str
    documents: list[str] = []  # media_asset IDs or external URLs
    notes: Optional[str] = None


class VerificationReviewIn(BaseModel):
    decision: str  # approved | rejected
    notes: Optional[str] = None
    rejection_reason: Optional[str] = None


@verification_router.post("/", status_code=201)
def submit_verification(
    p: VerificationSubmitIn,
    member: Member = Depends(get_current_member), db: Session = Depends(get_db),
):
    if p.submission_type not in SUBMISSION_TYPES:
        raise HTTPException(400, f"Invalid submission_type. Must be one of: {SUBMISSION_TYPES}")
    row = db.execute(text("""
        INSERT INTO verification_submissions (member_id, submission_type, documents, notes, status)
        VALUES (CAST(:mid AS UUID), :stype, CAST(:docs AS jsonb), :notes, 'pending')
        RETURNING *
    """), {
        "mid": str(member.id), "stype": p.submission_type,
        "docs": json.dumps(p.documents), "notes": p.notes,
    }).fetchone()
    db.commit()
    return _ok(_row(row))


@verification_router.get("/my")
def my_verifications(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    member: Member = Depends(get_current_member), db: Session = Depends(get_db),
):
    params = {"mid": str(member.id)}
    rows, meta = _paginate(db,
        "SELECT * FROM verification_submissions WHERE member_id = CAST(:mid AS UUID) AND deleted_at IS NULL ORDER BY created_at DESC",
        "SELECT COUNT(*) FROM verification_submissions WHERE member_id = CAST(:mid AS UUID) AND deleted_at IS NULL",
        params, page, page_size)
    return _ok(rows, meta)


@verification_router.get("/queue")
def verification_queue(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    member: Member = Depends(require_member_role("verifier","chapter_admin","national_director","super_admin")),
    db: Session = Depends(get_db),
):
    params = {"vid": str(member.id)}
    # Verifiers see their assigned queue; admins see all pending
    if member.role == "verifier":
        where = "WHERE assigned_to = CAST(:vid AS UUID) AND status IN ('pending','assigned','under_review') AND deleted_at IS NULL"
    else:
        where = "WHERE status IN ('pending','assigned','under_review') AND deleted_at IS NULL"
        params = {}
    rows, meta = _paginate(db,
        f"SELECT * FROM verification_submissions {where} ORDER BY created_at",
        f"SELECT COUNT(*) FROM verification_submissions {where}",
        params, page, page_size)
    return _ok(rows, meta)


@verification_router.post("/{submission_id}/review")
def review_verification(
    submission_id: UUID, payload: VerificationReviewIn,
    member: Member = Depends(require_member_role("verifier","chapter_admin","national_director","super_admin")),
    db: Session = Depends(get_db),
):
    if payload.decision not in ("approved", "rejected"):
        raise HTTPException(400, "Decision must be 'approved' or 'rejected'")

    row = db.execute(text("""
        SELECT * FROM verification_submissions
        WHERE id = CAST(:id AS UUID) AND deleted_at IS NULL
    """), {"id": str(submission_id)}).fetchone()
    if not row:
        raise HTTPException(404, "Submission not found")

    db.execute(text("""
        UPDATE verification_submissions
        SET status = :decision,
            reviewed_by = CAST(:reviewer AS UUID),
            reviewed_at = now(),
            rejection_reason = :reason,
            updated_at = now()
        WHERE id = CAST(:id AS UUID)
    """), {
        "decision": payload.decision,
        "reviewer": str(member.id),
        "reason": payload.rejection_reason,
        "id": str(submission_id),
    })

    # If approved identity verification, mark member as verified
    if payload.decision == "approved" and row.submission_type == "identity":
        db.execute(text("""
            UPDATE members SET is_verified = TRUE, updated_at = now()
            WHERE id = CAST(:mid AS UUID)
        """), {"mid": str(row.member_id)})

    db.commit()
    return _ok({"submission_id": str(submission_id), "status": payload.decision})


# ═══════════════════════════════════════════════════════════════════════════
# IMPACT  /api/v2/impact
# ═══════════════════════════════════════════════════════════════════════════

impact_router = APIRouter(prefix="/api/v2/impact", tags=["impact"])


@impact_router.get("/me")
def my_impact(member: Member = Depends(get_current_member), db: Session = Depends(get_db)):
    row = db.execute(text("""
        SELECT * FROM diaspora_impact_scores
        WHERE member_id = CAST(:mid AS UUID)
        ORDER BY score_date DESC LIMIT 1
    """), {"mid": str(member.id)}).fetchone()
    if not row:
        return _ok({"member_id": str(member.id), "total_score": 0, "message": "No score computed yet"})
    return _ok(_row(row))


@impact_router.get("/leaderboard")
def leaderboard(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    chapter_id: Optional[UUID] = None,
    _: Member = Depends(get_current_member), db: Session = Depends(get_db),
):
    if chapter_id:
        base_q = """
            SELECT dis.*, m.full_name, m.membership_number, m.chapter_id
            FROM diaspora_impact_scores dis
            JOIN members m ON dis.member_id = m.id
            WHERE dis.score_date = CURRENT_DATE
              AND m.chapter_id = CAST(:chapter_id AS UUID)
              AND m.deleted_at IS NULL
            ORDER BY dis.total_score DESC
        """
        count_q = """
            SELECT COUNT(*) FROM diaspora_impact_scores dis JOIN members m ON dis.member_id = m.id
            WHERE dis.score_date = CURRENT_DATE AND m.chapter_id = CAST(:chapter_id AS UUID) AND m.deleted_at IS NULL
        """
        params = {"chapter_id": str(chapter_id)}
    else:
        base_q = """
            SELECT dis.*, m.full_name, m.membership_number, m.chapter_id
            FROM diaspora_impact_scores dis JOIN members m ON dis.member_id = m.id
            WHERE dis.score_date = CURRENT_DATE AND m.deleted_at IS NULL
            ORDER BY dis.national_rank ASC NULLS LAST
        """
        count_q = "SELECT COUNT(*) FROM diaspora_impact_scores WHERE score_date = CURRENT_DATE"
        params = {}
    rows, meta = _paginate(db, base_q, count_q, params, page, page_size)
    return _ok(rows, meta)


@impact_router.get("/member/{member_id}")
def member_impact_history(
    member_id: UUID,
    _: Member = Depends(require_member_role("chapter_admin","national_director","super_admin","intelligence_analyst")),
    db: Session = Depends(get_db),
):
    rows = db.execute(text("""
        SELECT * FROM diaspora_impact_scores
        WHERE member_id = CAST(:mid AS UUID)
        ORDER BY score_date DESC LIMIT 90
    """), {"mid": str(member_id)}).fetchall()
    return _ok(_rows(rows))


# ═══════════════════════════════════════════════════════════════════════════
# ADMIN  /api/v2/admin
# ═══════════════════════════════════════════════════════════════════════════

admin_router = APIRouter(prefix="/api/v2/admin", tags=["admin"])


@admin_router.get("/members")
def admin_list_members(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    role: Optional[str] = None, is_verified: Optional[bool] = None,
    chapter_id: Optional[UUID] = None, search: Optional[str] = None,
    _: Member = Depends(require_member_role("chapter_admin","national_director","super_admin")),
    db: Session = Depends(get_db),
):
    conds = ["deleted_at IS NULL"]
    params = {}
    if role:
        conds.append("role = :role"); params["role"] = role
    if is_verified is not None:
        conds.append("is_verified = :iv"); params["iv"] = is_verified
    if chapter_id:
        conds.append("chapter_id = CAST(:chapter_id AS UUID)"); params["chapter_id"] = str(chapter_id)
    if search:
        conds.append("(full_name ILIKE :search OR email ILIKE :search OR membership_number ILIKE :search)")
        params["search"] = f"%{search}%"
    where = "WHERE " + " AND ".join(conds)
    rows, meta = _paginate(db,
        f"SELECT id, email, full_name, membership_number, role, is_active, is_verified, chapter_id, created_at FROM members {where} ORDER BY created_at DESC",
        f"SELECT COUNT(*) FROM members {where}",
        params, page, page_size)
    return _ok(rows, meta)


@admin_router.put("/members/{member_id}/role")
def admin_set_role(
    member_id: UUID, payload: dict,
    admin: Member = Depends(require_member_role("national_director","super_admin")),
    db: Session = Depends(get_db),
):
    from app.models.member import MEMBER_ROLES
    new_role = payload.get("role")
    if new_role not in MEMBER_ROLES:
        raise HTTPException(400, f"Invalid role. Must be one of: {list(MEMBER_ROLES)}")
    db.execute(text("""
        UPDATE members SET role = :role, updated_at = now()
        WHERE id = CAST(:id AS UUID) AND deleted_at IS NULL
    """), {"role": new_role, "id": str(member_id)})
    db.commit()
    return _ok({"member_id": str(member_id), "role": new_role})


@admin_router.put("/members/{member_id}/activate")
def admin_activate_member(
    member_id: UUID,
    admin: Member = Depends(require_member_role("chapter_admin","national_director","super_admin")),
    db: Session = Depends(get_db),
):
    db.execute(text("""
        UPDATE members SET is_active = TRUE, updated_at = now()
        WHERE id = CAST(:id AS UUID) AND deleted_at IS NULL
    """), {"id": str(member_id)})
    db.commit()
    return _ok({"member_id": str(member_id), "is_active": True})


@admin_router.put("/members/{member_id}/deactivate")
def admin_deactivate_member(
    member_id: UUID,
    admin: Member = Depends(require_member_role("chapter_admin","national_director","super_admin")),
    db: Session = Depends(get_db),
):
    db.execute(text("""
        UPDATE members SET is_active = FALSE, updated_at = now()
        WHERE id = CAST(:id AS UUID) AND deleted_at IS NULL
    """), {"id": str(member_id)})
    # Revoke all sessions
    db.execute(text("""
        UPDATE member_sessions SET revoked_at = now()
        WHERE member_id = CAST(:id AS UUID) AND revoked_at IS NULL
    """), {"id": str(member_id)})
    db.commit()
    return _ok({"member_id": str(member_id), "is_active": False})


@admin_router.get("/audit-log")
def admin_audit_log(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    endpoint: Optional[str] = None, user_email: Optional[str] = None,
    _: Member = Depends(require_member_role("national_director","super_admin","intelligence_analyst")),
    db: Session = Depends(get_db),
):
    conds = []
    params = {}
    if endpoint:
        conds.append("endpoint ILIKE :ep"); params["ep"] = f"%{endpoint}%"
    if user_email:
        conds.append("user_email = :ue"); params["ue"] = user_email
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    rows, meta = _paginate(db,
        f"SELECT * FROM audit_log {where} ORDER BY created_at DESC",
        f"SELECT COUNT(*) FROM audit_log {where}",
        params, page, page_size)
    return _ok(rows, meta)


@admin_router.get("/scheduler-log")
def admin_scheduler_log(
    limit: int = Query(50, ge=1, le=200),
    job_name: Optional[str] = None,
    _: Member = Depends(require_member_role("national_director","super_admin")),
    db: Session = Depends(get_db),
):
    params = {"limit": limit}
    where = ""
    if job_name:
        where = "WHERE job_name = :job_name"
        params["job_name"] = job_name
    rows = db.execute(text(f"""
        SELECT * FROM scheduler_job_log {where}
        ORDER BY started_at DESC LIMIT :limit
    """), params).fetchall()
    return _ok(_rows(rows))


@admin_router.get("/platform-stats")
def platform_stats(
    _: Member = Depends(require_member_role("national_director","super_admin")),
    db: Session = Depends(get_db),
):
    stats = db.execute(text("""
        SELECT
            (SELECT COUNT(*) FROM members WHERE deleted_at IS NULL) as total_members,
            (SELECT COUNT(*) FROM members WHERE is_active = TRUE AND deleted_at IS NULL) as active_members,
            (SELECT COUNT(*) FROM members WHERE is_verified = TRUE AND deleted_at IS NULL) as verified_members,
            (SELECT COUNT(*) FROM chapters WHERE is_active = TRUE AND deleted_at IS NULL) as total_chapters,
            (SELECT COUNT(*) FROM engagement_reports WHERE status = 'approved' AND deleted_at IS NULL) as approved_reports,
            (SELECT COUNT(*) FROM verification_submissions WHERE status = 'pending' AND deleted_at IS NULL) as pending_verifications,
            (SELECT COUNT(*) FROM platform_projects WHERE status = 'active' AND deleted_at IS NULL) as active_projects,
            (SELECT COUNT(*) FROM notifications WHERE status = 'failed') as failed_notifications
    """)).fetchone()
    return _ok(dict(stats._mapping) if stats else {})


@admin_router.get("/chapter-summaries")
def chapter_summaries(
    _: Member = Depends(require_member_role("national_director","super_admin","chapter_admin")),
    db: Session = Depends(get_db),
):
    """Try Redis cache first; fall back to live DB query."""
    try:
        import redis, json, os
        r = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
        cached = r.get("ndip:chapter_summaries")
        if cached:
            return _ok(json.loads(cached))
    except Exception:
        pass

    # Live fallback
    chapters = db.execute(text("""
        SELECT c.id, c.name,
               COUNT(DISTINCT m.id) FILTER (WHERE m.is_active AND m.deleted_at IS NULL) as member_count,
               COUNT(DISTINCT m.id) FILTER (WHERE m.is_verified AND m.deleted_at IS NULL) as verified_count
        FROM chapters c
        LEFT JOIN members m ON m.chapter_id = c.id
        WHERE c.is_active = TRUE AND c.deleted_at IS NULL
        GROUP BY c.id, c.name
        ORDER BY c.name
    """)).fetchall()
    return _ok(_rows(chapters))
