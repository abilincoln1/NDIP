"""
NDIP on Orion Platform Kernel
/api/v3/donations/ and /api/v3/communications/ — Donations & Communications Engine
Phase D5A-S6

Orion Kernel capability — domain-agnostic record primitives.
Donations: structured financial contribution records.
Communications: structured organisational correspondence records.

EXPLICITLY NOT IMPLEMENTED:
  - payment processing, gateways, card processing
  - message delivery, email/SMS/WhatsApp sending
  - bulk messaging, campaigns, donor profiling

Archive convention: PATCH with is_archived=True (no HTTP DELETE)
Financial visibility: donations NOT auto-visible to project participants
ward_sponsorships: UNTOUCHED
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
from app.api.routes.activities_v3 import (
    set_tenant_context, require_active_membership, can_verify, can_admin
)

donations_router = APIRouter(prefix="/api/v3/donations", tags=["v3-donations"])
comms_router = APIRouter(prefix="/api/v3/communications", tags=["v3-communications"])

DONATION_TYPES = ['donation', 'sponsorship', 'grant', 'in_kind', 'pledge', 'subscription', 'other']
COMM_TYPES = ['email', 'letter', 'meeting_minutes', 'phone_call', 'report', 'memo', 'correspondence', 'other']
DONATION_STATUSES = ['recorded', 'submitted', 'verified', 'rejected', 'archived']
COMM_STATUSES = ['draft', 'sent', 'received', 'acknowledged', 'archived']


# ── Financial access control ───────────────────────────────────────────────────

def can_access_donation(db: Session, donation, current: dict) -> bool:
    """
    Financial visibility is SEPARATE from project visibility.
    Project participation does NOT grant access to donation records.
    """
    identity_id = current["sub"]
    tenant_id = current.get("tenant_id")

    if current.get("admin_level"):
        return True

    # Tenant-owned donation: match tenant
    if donation.tenant_id is not None:
        return str(donation.tenant_id) == tenant_id

    # Independent donation (tenant_id NULL): only recorder or platform admin
    return str(donation.recorded_by) == identity_id


# ── Schemas ────────────────────────────────────────────────────────────────────

class DonationCreate(BaseModel):
    donation_type: str
    donation_date: date
    # Donor — all optional to support anonymous/external
    donor_identity_id: Optional[str] = None
    donor_organisation_id: Optional[str] = None
    donor_external_name: Optional[str] = None
    # Project linkage
    project_id: Optional[str] = None
    # Financial
    amount: Optional[float] = None
    currency: str = 'GBP'
    payment_reference: Optional[str] = None
    notes: Optional[str] = None
    is_independent: bool = False


class DonationUpdate(BaseModel):
    donation_type: Optional[str] = None
    donation_date: Optional[date] = None
    donor_external_name: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    payment_reference: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    is_archived: Optional[bool] = None


class CommCreate(BaseModel):
    communication_type: str
    subject: str
    communication_date: date
    recipient_identity_id: Optional[str] = None
    recipient_external: Optional[str] = None
    organisation_id: Optional[str] = None
    project_id: Optional[str] = None
    reference: Optional[str] = None
    notes: Optional[str] = None
    status: str = 'draft'
    is_independent: bool = False


class CommUpdate(BaseModel):
    communication_type: Optional[str] = None
    subject: Optional[str] = None
    communication_date: Optional[date] = None
    reference: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    is_archived: Optional[bool] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

DONATION_SELECT = """
    SELECT
        d.id, d.tenant_id, d.donor_identity_id, d.donor_organisation_id,
        d.donor_external_name, d.project_id, d.donation_type,
        d.amount, d.currency, d.payment_reference, d.donation_date,
        d.status, d.notes, d.verified_by, d.verified_at, d.verification_notes,
        d.recorded_by, d.created_at, d.updated_at, d.is_archived,
        pi_donor.full_name AS donor_name,
        o_donor.name AS donor_org_name,
        pi_rec.full_name AS recorded_by_name,
        p.name AS project_name
    FROM donations d
    LEFT JOIN platform_identities pi_donor ON pi_donor.id = d.donor_identity_id
    LEFT JOIN organisations o_donor ON o_donor.id = d.donor_organisation_id
    LEFT JOIN platform_identities pi_rec ON pi_rec.id = d.recorded_by
    LEFT JOIN projects p ON p.id = d.project_id
"""

COMM_SELECT = """
    SELECT
        c.id, c.tenant_id, c.sender_identity_id, c.recipient_identity_id,
        c.recipient_external, c.organisation_id, c.project_id,
        c.communication_type, c.subject, c.reference, c.communication_date,
        c.status, c.notes, c.created_at, c.updated_at, c.is_archived,
        pi_s.full_name AS sender_name,
        pi_r.full_name AS recipient_name,
        o.name AS organisation_name,
        p.name AS project_name
    FROM communications c
    JOIN platform_identities pi_s ON pi_s.id = c.sender_identity_id
    LEFT JOIN platform_identities pi_r ON pi_r.id = c.recipient_identity_id
    LEFT JOIN organisations o ON o.id = c.organisation_id
    LEFT JOIN projects p ON p.id = c.project_id
"""


def format_donation(row) -> dict:
    return {
        "id": str(row.id),
        "donation_type": row.donation_type,
        "donation_date": row.donation_date.isoformat() if row.donation_date else None,
        "donor": {
            "identity_name": row.donor_name,
            "organisation_name": row.donor_org_name,
            "external_name": row.donor_external_name,
        },
        "project": row.project_name,
        "project_id": str(row.project_id) if row.project_id else None,
        "amount": row.amount,
        "currency": row.currency,
        "payment_reference": row.payment_reference,
        "status": row.status,
        "notes": row.notes,
        "verification_status": {
            "verified_by": str(row.verified_by) if row.verified_by else None,
            "verified_at": row.verified_at.isoformat() if row.verified_at else None,
            "notes": row.verification_notes,
        },
        "recorded_by": row.recorded_by_name,
        "is_independent": row.tenant_id is None,
        "tenant_id": str(row.tenant_id) if row.tenant_id else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "is_archived": row.is_archived,
    }


def format_comm(row) -> dict:
    return {
        "id": str(row.id),
        "communication_type": row.communication_type,
        "subject": row.subject,
        "communication_date": row.communication_date.isoformat() if row.communication_date else None,
        "sender": row.sender_name,
        "recipient": row.recipient_name or row.recipient_external,
        "organisation": row.organisation_name,
        "project": row.project_name,
        "project_id": str(row.project_id) if row.project_id else None,
        "reference": row.reference,
        "status": row.status,
        "notes": row.notes,
        "is_independent": row.tenant_id is None,
        "tenant_id": str(row.tenant_id) if row.tenant_id else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "is_archived": row.is_archived,
    }


# ── DONATION ROUTES (D1–D5) ────────────────────────────────────────────────────

@donations_router.post("/", status_code=201)
def create_donation(
    payload: DonationCreate,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """D1 — Create donation record. NOT payment processing."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)
    require_active_membership(current, db, tenant_id)

    if payload.donation_type not in DONATION_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid donation_type. Valid: {DONATION_TYPES}")

    # Must have at least one donor identifier
    if not payload.donor_identity_id and not payload.donor_organisation_id and not payload.donor_external_name:
        raise HTTPException(status_code=400, detail="At least one of donor_identity_id, donor_organisation_id, or donor_external_name is required")

    # Validate project belongs to accessible context
    if payload.project_id:
        proj = db.execute(text("SELECT id FROM projects WHERE id = :pid"), {"pid": payload.project_id}).fetchone()
        if not proj:
            raise HTTPException(status_code=400, detail="Project not found")

    donation_tenant_id = None if payload.is_independent else tenant_id
    donation_id = str(uuid.uuid4())

    db.execute(text("""
        INSERT INTO donations (
            id, tenant_id, donor_identity_id, donor_organisation_id, donor_external_name,
            project_id, donation_type, amount, currency, payment_reference,
            donation_date, status, notes, recorded_by, created_at, updated_at
        ) VALUES (
            :id, :tenant_id, :donor_id, :donor_org_id, :donor_ext,
            :project_id, :dtype, :amount, :currency, :pay_ref,
            :ddate, 'recorded', :notes, :recorded_by, now(), now()
        )
    """), {
        "id": donation_id,
        "tenant_id": donation_tenant_id,
        "donor_id": payload.donor_identity_id,
        "donor_org_id": payload.donor_organisation_id,
        "donor_ext": payload.donor_external_name,
        "project_id": payload.project_id,
        "dtype": payload.donation_type,
        "amount": payload.amount,
        "currency": payload.currency,
        "pay_ref": payload.payment_reference,
        "ddate": payload.donation_date,
        "notes": payload.notes,
        "recorded_by": current["sub"],
    })
    db.commit()
    return {"id": donation_id, "status": "recorded", "message": "Donation record created"}


@donations_router.get("/")
def list_donations(
    status: Optional[str] = Query(None),
    donation_type: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """D2 — List donations. Financial visibility restricted — NOT project participant visibility."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    # Financial access: only tenant-owned or recorded by this identity
    # Project participation does NOT grant access to donation amounts
    filters = ["d.is_archived = FALSE", "(d.tenant_id = :tid OR d.recorded_by = :iid)"]
    params = {"tid": tenant_id, "iid": current["sub"]}

    if status:
        filters.append("d.status = :status")
        params["status"] = status
    if donation_type:
        filters.append("d.donation_type = :dtype")
        params["dtype"] = donation_type
    if project_id:
        filters.append("d.project_id = :pid")
        params["pid"] = project_id

    where = " AND ".join(filters)
    offset = (page - 1) * page_size

    total = db.execute(text(f"SELECT COUNT(*) FROM donations d WHERE {where}"), params).scalar()
    rows = db.execute(
        text(f"{DONATION_SELECT} WHERE {where} ORDER BY d.donation_date DESC LIMIT :limit OFFSET :offset"),
        {**params, "limit": page_size, "offset": offset}
    ).fetchall()

    return {"total": total, "page": page, "page_size": page_size, "items": [format_donation(r) for r in rows]}


@donations_router.get("/{donation_id}")
def get_donation(
    donation_id: str,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """D3 — Retrieve donation. Financial access check applied."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    row = db.execute(
        text(f"{DONATION_SELECT} WHERE d.id = :id"), {"id": donation_id}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Donation not found")
    if not can_access_donation(db, row, current):
        raise HTTPException(status_code=403, detail="Access denied — financial records require explicit authorisation")

    return format_donation(row)


@donations_router.patch("/{donation_id}")
def update_donation(
    donation_id: str,
    payload: DonationUpdate,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """D4 — Update donation record."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    donation = db.execute(
        text("SELECT id, recorded_by, status, tenant_id FROM donations WHERE id = :id"),
        {"id": donation_id}
    ).fetchone()

    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")
    if not can_access_donation(db, donation, current):
        raise HTTPException(status_code=403, detail="Access denied")
    if donation.status in ('verified', 'archived') and not can_admin(current):
        raise HTTPException(status_code=409, detail=f"Cannot edit donation in status: {donation.status}")
    if str(donation.recorded_by) != current["sub"] and not can_admin(current):
        raise HTTPException(status_code=403, detail="Only recorder or admin can update donation")

    if payload.status and payload.status not in DONATION_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {DONATION_STATUSES}")

    updates = {"id": donation_id, "updated_at": datetime.utcnow()}
    set_parts = ["updated_at = :updated_at"]

    if payload.donation_type is not None:
        if payload.donation_type not in DONATION_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid donation_type")
        updates["dtype"] = payload.donation_type
        set_parts.append("donation_type = :dtype")
    if payload.donation_date is not None:
        updates["ddate"] = payload.donation_date
        set_parts.append("donation_date = :ddate")
    if payload.donor_external_name is not None:
        updates["donor_ext"] = payload.donor_external_name
        set_parts.append("donor_external_name = :donor_ext")
    if payload.amount is not None:
        updates["amount"] = payload.amount
        set_parts.append("amount = :amount")
    if payload.currency is not None:
        updates["currency"] = payload.currency
        set_parts.append("currency = :currency")
    if payload.payment_reference is not None:
        updates["pay_ref"] = payload.payment_reference
        set_parts.append("payment_reference = :pay_ref")
    if payload.notes is not None:
        updates["notes"] = payload.notes
        set_parts.append("notes = :notes")
    if payload.status is not None:
        updates["status"] = payload.status
        set_parts.append("status = :status")
    if payload.is_archived is not None:
        updates["is_archived"] = payload.is_archived
        set_parts.append("is_archived = :is_archived")
        if payload.is_archived:
            updates["status"] = "archived"
            set_parts.append("status = :status")

    db.execute(
        text(f"UPDATE donations SET {', '.join(set_parts)} WHERE id = :id"),
        updates
    )
    db.commit()
    return {"message": "Donation updated"}


# D5 — Archive uses PATCH with is_archived=True (established NDIP convention — no HTTP DELETE)
# Implemented via the update endpoint above with is_archived=True in payload


# ── COMMUNICATIONS ROUTES (C1–C4) ─────────────────────────────────────────────

@comms_router.post("/", status_code=201)
def create_communication(
    payload: CommCreate,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """C1 — Create communication record. Record-only — no delivery."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)
    require_active_membership(current, db, tenant_id)

    if payload.communication_type not in COMM_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid communication_type. Valid: {COMM_TYPES}")
    if payload.status not in COMM_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {COMM_STATUSES}")

    comm_tenant_id = None if payload.is_independent else tenant_id
    comm_id = str(uuid.uuid4())

    db.execute(text("""
        INSERT INTO communications (
            id, tenant_id, sender_identity_id, recipient_identity_id, recipient_external,
            organisation_id, project_id, communication_type, subject, reference,
            communication_date, status, notes, created_at, updated_at
        ) VALUES (
            :id, :tenant_id, :sender, :recipient_id, :recipient_ext,
            :org_id, :project_id, :ctype, :subject, :reference,
            :cdate, :status, :notes, now(), now()
        )
    """), {
        "id": comm_id,
        "tenant_id": comm_tenant_id,
        "sender": current["sub"],
        "recipient_id": payload.recipient_identity_id,
        "recipient_ext": payload.recipient_external,
        "org_id": payload.organisation_id,
        "project_id": payload.project_id,
        "ctype": payload.communication_type,
        "subject": payload.subject,
        "reference": payload.reference,
        "cdate": payload.communication_date,
        "status": payload.status,
        "notes": payload.notes,
    })
    db.commit()
    return {"id": comm_id, "status": payload.status, "message": "Communication record created"}


@comms_router.get("/")
def list_communications(
    status: Optional[str] = Query(None),
    communication_type: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """C2 — List communications. Tenant-scoped."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    filters = [
        "c.is_archived = FALSE",
        "(c.tenant_id = :tid OR c.sender_identity_id = :iid OR c.recipient_identity_id = :iid)"
    ]
    params = {"tid": tenant_id, "iid": current["sub"]}

    if status:
        filters.append("c.status = :status")
        params["status"] = status
    if communication_type:
        filters.append("c.communication_type = :ctype")
        params["ctype"] = communication_type
    if project_id:
        filters.append("c.project_id = :pid")
        params["pid"] = project_id

    where = " AND ".join(filters)
    offset = (page - 1) * page_size

    total = db.execute(text(f"SELECT COUNT(*) FROM communications c WHERE {where}"), params).scalar()
    rows = db.execute(
        text(f"{COMM_SELECT} WHERE {where} ORDER BY c.communication_date DESC LIMIT :limit OFFSET :offset"),
        {**params, "limit": page_size, "offset": offset}
    ).fetchall()

    return {"total": total, "page": page, "page_size": page_size, "items": [format_comm(r) for r in rows]}


@comms_router.get("/{comm_id}")
def get_communication(
    comm_id: str,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """C3 — Retrieve communication record."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    row = db.execute(
        text(f"{COMM_SELECT} WHERE c.id = :id"), {"id": comm_id}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Communication not found")

    # Access: sender, recipient, or tenant member
    identity_id = current["sub"]
    is_sender = str(row.sender_identity_id) == identity_id
    is_recipient = row.recipient_identity_id and str(row.recipient_identity_id) == identity_id
    is_tenant = row.tenant_id and str(row.tenant_id) == tenant_id

    if not (is_sender or is_recipient or is_tenant or can_admin(current)):
        raise HTTPException(status_code=403, detail="Access denied")

    return format_comm(row)


@comms_router.patch("/{comm_id}")
def update_communication(
    comm_id: str,
    payload: CommUpdate,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db)
):
    """C4 — Update communication record. Archive via is_archived=True."""
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    comm = db.execute(
        text("SELECT id, sender_identity_id, status, tenant_id FROM communications WHERE id = :id"),
        {"id": comm_id}
    ).fetchone()

    if not comm:
        raise HTTPException(status_code=404, detail="Communication not found")

    is_sender = str(comm.sender_identity_id) == current["sub"]
    is_tenant = comm.tenant_id and str(comm.tenant_id) == tenant_id

    if not (is_sender or is_tenant or can_admin(current)):
        raise HTTPException(status_code=403, detail="Access denied")

    if comm.status == 'archived' and not can_admin(current):
        raise HTTPException(status_code=409, detail="Cannot edit archived communication")

    if payload.status and payload.status not in COMM_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {COMM_STATUSES}")

    updates = {"id": comm_id, "updated_at": datetime.utcnow()}
    set_parts = ["updated_at = :updated_at"]

    if payload.communication_type is not None:
        if payload.communication_type not in COMM_TYPES:
            raise HTTPException(status_code=400, detail="Invalid communication_type")
        updates["ctype"] = payload.communication_type
        set_parts.append("communication_type = :ctype")
    if payload.subject is not None:
        updates["subject"] = payload.subject
        set_parts.append("subject = :subject")
    if payload.communication_date is not None:
        updates["cdate"] = payload.communication_date
        set_parts.append("communication_date = :cdate")
    if payload.reference is not None:
        updates["reference"] = payload.reference
        set_parts.append("reference = :reference")
    if payload.notes is not None:
        updates["notes"] = payload.notes
        set_parts.append("notes = :notes")
    if payload.status is not None:
        updates["status"] = payload.status
        set_parts.append("status = :status")
    if payload.is_archived is not None:
        updates["is_archived"] = payload.is_archived
        set_parts.append("is_archived = :is_archived")
        if payload.is_archived:
            updates["status"] = "archived"
            if "status = :status" not in set_parts:
                set_parts.append("status = :status")

    db.execute(
        text(f"UPDATE communications SET {', '.join(set_parts)} WHERE id = :id"),
        updates
    )
    db.commit()
    return {"message": "Communication updated"}
