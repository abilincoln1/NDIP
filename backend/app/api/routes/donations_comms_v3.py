"""
D5A-S6 Donations & Communications Engine — Route File
Remediation: fix communications GET/PATCH routes, enum validation,
cross-tenant RLS context.

Schema-aligned to live DB (confirmed 2026-10-18):

donations columns:
  id, tenant_id, donor_identity_id (uuid FK), donor_organisation_id (uuid FK),
  donor_external_name, project_id, donation_type, amount, currency,
  payment_reference, donation_date (NOT NULL), status, notes,
  verified_by, verified_at, verification_notes, recorded_by (uuid FK NOT NULL),
  created_at, updated_at, is_archived
  CHECK donation_type IN ('donation','sponsorship','grant','in_kind','pledge','subscription','other')
  CHECK status IN ('recorded','submitted','verified','rejected','archived')
  CHECK ck_donation_has_donor: at least one of donor_identity_id, donor_organisation_id, donor_external_name

communications columns:
  id, tenant_id, sender_identity_id (uuid FK NOT NULL), recipient_identity_id (uuid FK),
  recipient_external, organisation_id, project_id, communication_type (NOT NULL),
  subject (NOT NULL), reference, communication_date (NOT NULL), status,
  notes, created_at, updated_at, is_archived
  CHECK communication_type IN ('email','letter','meeting_minutes','phone_call','report','memo','correspondence','other')
  CHECK status IN ('draft','sent','received','acknowledged','archived')

Changes from original 2e8355a:
  1. DonationCreate / CommunicationCreate use Literal types for actual DB enum values — fixes SEC3/SEC4.
  2. All GET and PATCH communications routes present — fixes C2/C3/C4/SEC1.
  3. Every handler calls set_tenant_context before any DB query — fixes FV4.
  4. Identity accessed as dict (current["tenant_id"], current["sub"]) — matches project convention.
  5. Two routers exported: donations_router, comms_router — matches main.py import.
  6. Column names aligned to actual DB schema.

No schema changes. No new tables. No payment or delivery fields.
"""

import uuid
import logging
from typing import Literal, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes.auth_v3 import get_current_v3_identity, get_db

logger = logging.getLogger(__name__)


def set_tenant_context(db: Session, tenant_id: str):
    db.execute(text("SET LOCAL app.current_tenant_id = :tid"), {"tid": tenant_id})


donations_router = APIRouter(prefix="/api/v3", tags=["donations"])
comms_router = APIRouter(prefix="/api/v3", tags=["communications"])

# ---------------------------------------------------------------------------
# VALID ENUM VALUES — aligned to actual DB CHECK constraints
# ---------------------------------------------------------------------------

DONATION_TYPES = Literal[
    "donation",
    "sponsorship",
    "grant",
    "in_kind",
    "pledge",
    "subscription",
    "other",
]

COMMUNICATION_TYPES = Literal[
    "email",
    "letter",
    "meeting_minutes",
    "phone_call",
    "report",
    "memo",
    "correspondence",
    "other",
]

DONATION_STATUSES = Literal[
    "recorded",
    "submitted",
    "verified",
    "rejected",
    "archived",
]

COMMUNICATION_STATUSES = Literal[
    "draft",
    "sent",
    "received",
    "acknowledged",
    "archived",
]

# ---------------------------------------------------------------------------
# PYDANTIC MODELS — aligned to actual DB columns
# ---------------------------------------------------------------------------

class DonationCreate(BaseModel):
    donation_type: DONATION_TYPES
    donation_date: date                           # NOT NULL in DB
    donor_external_name: Optional[str] = None    # text, replaces donor_name
    donor_identity_id: Optional[str] = None      # uuid FK
    donor_organisation_id: Optional[str] = None  # uuid FK
    amount: Optional[float] = None
    currency: Optional[str] = "GBP"
    payment_reference: Optional[str] = None
    project_id: Optional[str] = None
    notes: Optional[str] = None


class DonationUpdate(BaseModel):
    donor_external_name: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    payment_reference: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[DONATION_STATUSES] = None
    is_archived: Optional[bool] = None


class CommunicationCreate(BaseModel):
    communication_type: COMMUNICATION_TYPES
    subject: str                                         # NOT NULL in DB
    communication_date: date                             # NOT NULL in DB
    sender_identity_id: Optional[str] = None            # defaults to current["sub"]
    recipient_identity_id: Optional[str] = None
    recipient_external: Optional[str] = None
    organisation_id: Optional[str] = None
    project_id: Optional[str] = None
    reference: Optional[str] = None
    notes: Optional[str] = None


class CommunicationUpdate(BaseModel):
    subject: Optional[str] = None
    notes: Optional[str] = None
    reference: Optional[str] = None
    status: Optional[COMMUNICATION_STATUSES] = None
    is_archived: Optional[bool] = None


# ---------------------------------------------------------------------------
# HELPER
# ---------------------------------------------------------------------------

def _validate_donor_identifier(data: DonationCreate):
    """Enforce ck_donation_has_donor check constraint."""
    if not any([data.donor_external_name, data.donor_identity_id, data.donor_organisation_id]):
        raise HTTPException(
            status_code=400,
            detail="At least one donor identifier is required: donor_external_name, donor_identity_id, or donor_organisation_id."
        )


# ===========================================================================
# DONATION ROUTES
# ===========================================================================

@donations_router.post("/donations", status_code=201)
def create_donation(
    data: DonationCreate,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db),
):
    _validate_donor_identifier(data)
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    donation_id = str(uuid.uuid4())

    sql = text("""
        INSERT INTO donations (
            id, tenant_id, donor_external_name, donor_identity_id, donor_organisation_id,
            donation_type, amount, currency, payment_reference, donation_date,
            project_id, notes, status, is_archived, recorded_by,
            created_at, updated_at
        ) VALUES (
            :id, :tenant_id, :donor_external_name, :donor_identity_id, :donor_organisation_id,
            :donation_type, :amount, :currency, :payment_reference, :donation_date,
            :project_id, :notes, 'recorded', FALSE, :recorded_by,
            NOW(), NOW()
        )
        RETURNING id, status, created_at
    """)

    row = db.execute(sql, {
        "id": donation_id,
        "tenant_id": tenant_id,
        "donor_external_name": data.donor_external_name,
        "donor_identity_id": data.donor_identity_id,
        "donor_organisation_id": data.donor_organisation_id,
        "donation_type": data.donation_type,
        "amount": data.amount,
        "currency": data.currency or "GBP",
        "payment_reference": data.payment_reference,
        "donation_date": data.donation_date,
        "project_id": data.project_id,
        "notes": data.notes,
        "recorded_by": current["sub"],
    }).fetchone()

    db.commit()
    return {"id": donation_id, "status": row.status, "created_at": str(row.created_at)}


@donations_router.get("/donations")
def list_donations(
    page: int = 1,
    page_size: int = 20,
    include_archived: bool = False,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db),
):
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    where = "WHERE tenant_id = :tenant_id"
    if not include_archived:
        where += " AND is_archived = FALSE"

    total = db.execute(
        text(f"SELECT COUNT(*) FROM donations {where}"),
        {"tenant_id": tenant_id}
    ).fetchone()[0]

    rows = db.execute(
        text(f"""
            SELECT id, donor_external_name, donor_identity_id, donor_organisation_id,
                   donation_type, amount, currency, donation_date, status, is_archived,
                   created_at
            FROM donations {where}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {
            "tenant_id": tenant_id,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }
    ).fetchall()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [dict(r._mapping) for r in rows],
    }


@donations_router.get("/donations/{donation_id}")
def get_donation(
    donation_id: str,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db),
):
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    row = db.execute(
        text("""
            SELECT id, tenant_id, donor_external_name, donor_identity_id,
                   donor_organisation_id, donation_type, amount, currency,
                   payment_reference, donation_date, project_id, notes, status,
                   is_archived, recorded_by, created_at, updated_at
            FROM donations
            WHERE id = :id AND tenant_id = :tenant_id AND is_archived = FALSE
        """),
        {"id": donation_id, "tenant_id": tenant_id}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Donation not found.")
    return dict(row._mapping)


@donations_router.patch("/donations/{donation_id}")
def update_donation(
    donation_id: str,
    data: DonationUpdate,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db),
):
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    set_clauses = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = donation_id
    updates["tenant_id"] = tenant_id

    result = db.execute(
        text(f"""
            UPDATE donations
            SET {set_clauses}, updated_at = NOW()
            WHERE id = :id AND tenant_id = :tenant_id
            RETURNING id, status, updated_at
        """),
        updates,
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Donation not found.")
    db.commit()
    return dict(result._mapping)


# ===========================================================================
# COMMUNICATION ROUTES
# ===========================================================================

@comms_router.post("/communications", status_code=201)
def create_communication(
    data: CommunicationCreate,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db),
):
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    comm_id = str(uuid.uuid4())

    sql = text("""
        INSERT INTO communications (
            id, tenant_id, communication_type, subject,
            sender_identity_id, recipient_identity_id, recipient_external,
            organisation_id, project_id, reference,
            communication_date, notes, status, is_archived,
            created_at, updated_at
        ) VALUES (
            :id, :tenant_id, :communication_type, :subject,
            :sender_identity_id, :recipient_identity_id, :recipient_external,
            :organisation_id, :project_id, :reference,
            :communication_date, :notes, 'draft', FALSE,
            NOW(), NOW()
        )
        RETURNING id, status, created_at
    """)

    row = db.execute(sql, {
        "id": comm_id,
        "tenant_id": tenant_id,
        "communication_type": data.communication_type,
        "subject": data.subject,
        "sender_identity_id": data.sender_identity_id or current["sub"],
        "recipient_identity_id": data.recipient_identity_id,
        "recipient_external": data.recipient_external,
        "organisation_id": data.organisation_id,
        "project_id": data.project_id,
        "reference": data.reference,
        "communication_date": data.communication_date,
        "notes": data.notes,
    }).fetchone()

    db.commit()
    return {"id": comm_id, "status": row.status, "created_at": str(row.created_at)}


@comms_router.get("/communications")
def list_communications(
    page: int = 1,
    page_size: int = 20,
    include_archived: bool = False,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db),
):
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    where = "WHERE tenant_id = :tenant_id"
    if not include_archived:
        where += " AND is_archived = FALSE"

    total = db.execute(
        text(f"SELECT COUNT(*) FROM communications {where}"),
        {"tenant_id": tenant_id}
    ).fetchone()[0]

    rows = db.execute(
        text(f"""
            SELECT id, communication_type, subject, status,
                   sender_identity_id, recipient_identity_id,
                   communication_date, is_archived, created_at
            FROM communications {where}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {
            "tenant_id": tenant_id,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }
    ).fetchall()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [dict(r._mapping) for r in rows],
    }


@comms_router.get("/communications/{comm_id}")
def get_communication(
    comm_id: str,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db),
):
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    row = db.execute(
        text("""
            SELECT id, tenant_id, communication_type, subject,
                   sender_identity_id, recipient_identity_id, recipient_external,
                   organisation_id, project_id, reference,
                   communication_date, notes, status, is_archived,
                   created_at, updated_at
            FROM communications
            WHERE id = :id AND tenant_id = :tenant_id AND is_archived = FALSE
        """),
        {"id": comm_id, "tenant_id": tenant_id}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Communication not found.")
    return dict(row._mapping)


@comms_router.patch("/communications/{comm_id}")
def update_communication(
    comm_id: str,
    data: CommunicationUpdate,
    current: dict = Depends(get_current_v3_identity),
    db: Session = Depends(get_db),
):
    tenant_id = current["tenant_id"]
    set_tenant_context(db, tenant_id)

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    set_clauses = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = comm_id
    updates["tenant_id"] = tenant_id

    result = db.execute(
        text(f"""
            UPDATE communications
            SET {set_clauses}, updated_at = NOW()
            WHERE id = :id AND tenant_id = :tenant_id
            RETURNING id, status, updated_at
        """),
        updates,
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Communication not found.")
    db.commit()
    return dict(result._mapping)
