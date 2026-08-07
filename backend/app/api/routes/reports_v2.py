"""
NDIP Phase D.3 — Engagement Reports API (D3.2)
File: app/api/routes/reports_v2.py

/api/v2/reports — NERS (Nigerian Engagement Reporting System)

Endpoints:
  POST   /api/v2/reports/                         Create report (any member)
  GET    /api/v2/reports/                         List reports (filtered)
  GET    /api/v2/reports/{report_id}              Get single report
  PUT    /api/v2/reports/{report_id}              Update own draft report
  DELETE /api/v2/reports/{report_id}              Soft-delete own draft
  POST   /api/v2/reports/{report_id}/submit       Submit draft for review
  POST   /api/v2/reports/{report_id}/review       Review (chapter_admin+)
  GET    /api/v2/reports/my                       My reports (paginated)
  GET    /api/v2/reports/chapter/{chapter_id}     Chapter reports (chapter_admin+)

All list endpoints: pagination, sorting, filtering.
Consistent response envelope: {"ok": true, "data": {...}, "meta": {...}}
"""
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

router = APIRouter(prefix="/api/v2/reports", tags=["reports_v2"])

REPORT_TYPES = [
    "community_event", "fundraiser", "advocacy",
    "cultural", "educational", "outreach", "other",
]
REPORT_STATUSES = ["draft", "submitted", "under_review", "approved", "rejected"]


# ─── Schemas ───────────────────────────────────────────────────────────────

class ReportCreateIn(BaseModel):
    report_type: str
    title: str = Field(..., min_length=3, max_length=500)
    description: str = Field(..., min_length=10)
    event_date: date
    location: Optional[str] = None
    country: Optional[str] = None
    attendees_count: int = Field(0, ge=0)
    outcome_summary: Optional[str] = None
    tags: list[str] = []


class ReportUpdateIn(BaseModel):
    report_type: Optional[str] = None
    title: Optional[str] = Field(None, min_length=3, max_length=500)
    description: Optional[str] = None
    event_date: Optional[date] = None
    location: Optional[str] = None
    country: Optional[str] = None
    attendees_count: Optional[int] = Field(None, ge=0)
    outcome_summary: Optional[str] = None
    tags: Optional[list[str]] = None


class ReviewIn(BaseModel):
    decision: str   # approved | rejected
    notes: Optional[str] = None


# ─── Helpers ───────────────────────────────────────────────────────────────

def _ok(data, meta=None):
    return {"ok": True, "data": data, "meta": meta or {}}


def _paginate(db, query: str, params: dict, page: int, page_size: int, count_query: str):
    total = db.execute(text(count_query), params).scalar() or 0
    offset = (page - 1) * page_size
    params_p = {**params, "limit": page_size, "offset": offset}
    rows = db.execute(text(query + " LIMIT :limit OFFSET :offset"), params_p).fetchall()
    return rows, {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": -(-total // page_size),
    }


def _row_to_dict(row) -> dict:
    d = dict(row._mapping)
    for k, v in d.items():
        if hasattr(v, '__str__') and type(v).__name__ == 'UUID':
            d[k] = str(v)
    return d


def _get_report_or_404(db: Session, report_id: UUID) -> dict:
    row = db.execute(text("""
        SELECT * FROM engagement_reports
        WHERE id = CAST(:id AS UUID) AND deleted_at IS NULL
    """), {"id": str(report_id)}).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    return _row_to_dict(row)


# ─── Routes ────────────────────────────────────────────────────────────────

@router.post("/", status_code=status.HTTP_201_CREATED, summary="Create engagement report")
def create_report(
    payload: ReportCreateIn,
    member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    if payload.report_type not in REPORT_TYPES:
        raise HTTPException(400, f"Invalid report_type. Must be one of: {REPORT_TYPES}")

    import json
    row = db.execute(text("""
        INSERT INTO engagement_reports
            (member_id, chapter_id, report_type, title, description,
             event_date, location, country, attendees_count, outcome_summary,
             tags, status)
        VALUES
            (CAST(:mid AS UUID), CAST(:cid AS UUID), :rtype, :title, :desc,
             :edate, :loc, :country, :att, :outcome,
             CAST(:tags AS jsonb), 'draft')
        RETURNING *
    """), {
        "mid": str(member.id),
        "cid": str(member.chapter_id) if member.chapter_id else None,
        "rtype": payload.report_type,
        "title": payload.title,
        "desc": payload.description,
        "edate": payload.event_date,
        "loc": payload.location,
        "country": payload.country,
        "att": payload.attendees_count,
        "outcome": payload.outcome_summary,
        "tags": json.dumps(payload.tags),
    }).fetchone()
    db.commit()
    return _ok(_row_to_dict(row))


@router.get("/my", summary="My engagement reports")
def my_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    params = {"mid": str(member.id)}
    where = "WHERE member_id = CAST(:mid AS UUID) AND deleted_at IS NULL"
    if status_filter and status_filter in REPORT_STATUSES:
        where += " AND status = :status"
        params["status"] = status_filter

    rows, meta = _paginate(
        db,
        f"SELECT * FROM engagement_reports {where} ORDER BY created_at DESC",
        params, page, page_size,
        f"SELECT COUNT(*) FROM engagement_reports {where}",
    )
    return _ok([_row_to_dict(r) for r in rows], meta)


@router.get("/", summary="List engagement reports")
def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    chapter_id: Optional[UUID] = None,
    report_type: Optional[str] = None,
    member: Member = Depends(require_member_role(
        "chapter_admin", "national_director", "super_admin", "intelligence_analyst"
    )),
    db: Session = Depends(get_db),
):
    params = {}
    conditions = ["deleted_at IS NULL"]
    if status_filter and status_filter in REPORT_STATUSES:
        conditions.append("status = :status")
        params["status"] = status_filter
    if chapter_id:
        conditions.append("chapter_id = CAST(:chapter_id AS UUID)")
        params["chapter_id"] = str(chapter_id)
    if report_type and report_type in REPORT_TYPES:
        conditions.append("report_type = :report_type")
        params["report_type"] = report_type

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    rows, meta = _paginate(
        db,
        f"SELECT * FROM engagement_reports {where} ORDER BY created_at DESC",
        params, page, page_size,
        f"SELECT COUNT(*) FROM engagement_reports {where}",
    )
    return _ok([_row_to_dict(r) for r in rows], meta)


@router.get("/{report_id}", summary="Get single report")
def get_report(
    report_id: UUID,
    member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    report = _get_report_or_404(db, report_id)
    # Own reports always visible; others require elevated role
    if str(report["member_id"]) != str(member.id):
        if member.role not in ("chapter_admin", "national_director", "super_admin", "intelligence_analyst"):
            raise HTTPException(403, "Access denied")
    return _ok(report)


@router.put("/{report_id}", summary="Update draft report")
def update_report(
    report_id: UUID,
    payload: ReportUpdateIn,
    member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    report = _get_report_or_404(db, report_id)
    if str(report["member_id"]) != str(member.id):
        raise HTTPException(403, "You can only edit your own reports")
    if report["status"] != "draft":
        raise HTTPException(409, f"Cannot edit a report with status '{report['status']}'")

    import json
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _ok(report)

    set_clauses = []
    params = {"id": str(report_id)}
    for key, val in updates.items():
        if key == "tags":
            set_clauses.append(f"tags = CAST(:{key} AS jsonb)")
            params[key] = json.dumps(val)
        else:
            set_clauses.append(f"{key} = :{key}")
            params[key] = val

    set_clauses.append("updated_at = now()")
    db.execute(text(f"""
        UPDATE engagement_reports SET {', '.join(set_clauses)}
        WHERE id = CAST(:id AS UUID)
    """), params)
    db.commit()
    return _ok(_get_report_or_404(db, report_id))


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete draft report")
def delete_report(
    report_id: UUID,
    member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    report = _get_report_or_404(db, report_id)
    if str(report["member_id"]) != str(member.id):
        raise HTTPException(403, "You can only delete your own reports")
    if report["status"] not in ("draft", "rejected"):
        raise HTTPException(409, "Only draft or rejected reports can be deleted")

    db.execute(text("""
        UPDATE engagement_reports SET deleted_at = now(), updated_at = now()
        WHERE id = CAST(:id AS UUID)
    """), {"id": str(report_id)})
    db.commit()
    return None


@router.post("/{report_id}/submit", summary="Submit report for review")
def submit_report(
    report_id: UUID,
    member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    report = _get_report_or_404(db, report_id)
    if str(report["member_id"]) != str(member.id):
        raise HTTPException(403, "You can only submit your own reports")
    if report["status"] != "draft":
        raise HTTPException(409, f"Report is already in status '{report['status']}'")

    db.execute(text("""
        UPDATE engagement_reports
        SET status = 'submitted', updated_at = now()
        WHERE id = CAST(:id AS UUID)
    """), {"id": str(report_id)})
    db.commit()
    return _ok({"status": "submitted"})


@router.post("/{report_id}/review", summary="Review submitted report")
def review_report(
    report_id: UUID,
    payload: ReviewIn,
    member: Member = Depends(require_member_role("chapter_admin", "national_director", "super_admin")),
    db: Session = Depends(get_db),
):
    report = _get_report_or_404(db, report_id)
    if report["status"] not in ("submitted", "under_review"):
        raise HTTPException(409, f"Cannot review a report with status '{report['status']}'")
    if payload.decision not in ("approved", "rejected"):
        raise HTTPException(400, "Decision must be 'approved' or 'rejected'")

    db.execute(text("""
        UPDATE engagement_reports
        SET status = :decision,
            reviewed_by = CAST(:reviewer AS UUID),
            reviewed_at = now(),
            reviewer_notes = :notes,
            updated_at = now()
        WHERE id = CAST(:id AS UUID)
    """), {
        "decision": payload.decision,
        "reviewer": str(member.id),
        "notes": payload.notes,
        "id": str(report_id),
    })
    db.commit()
    return _ok({"status": payload.decision, "reviewed_by": str(member.id)})
