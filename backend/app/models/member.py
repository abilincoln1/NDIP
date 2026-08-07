"""
Phase D.2 — Members Foundation: Member model.

`role` is an addition beyond the D.2 directive's explicit "Required fields"
list for `members`. It is required to support the RBAC roles the directive
asks for (super_admin, national_director, chapter_admin, verified_member,
standard_member, verifier, intelligence_analyst) and to embed a `role`
claim in the member JWT, also explicitly requested. See
PHASE_D2_IMPLEMENTATION.md ("RBAC") and PHASE_D2_COMPLIANCE_REPORT.md
(Deviations) for the full rationale — this is disclosed, not silent.
"""
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.models import utcnow

if TYPE_CHECKING:
    from app.models.chapter import Chapter
    from app.models.member_profile import MemberProfile
    from app.models.member_session import MemberSession


# Valid values for Member.role — enforced in the service layer (application
# level), not as a Postgres CHECK constraint, so new roles can be added
# without a schema migration. See app/core/member_rbac.py.
MEMBER_ROLES = (
    "super_admin",
    "national_director",
    "chapter_admin",
    "verified_member",
    "standard_member",
    "verifier",
    "intelligence_analyst",
)

MEMBERSHIP_TIERS = ("standard", "premium", "lifetime", "honorary")


class Member(Base):
    __tablename__ = "members"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    admin_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    state_of_origin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ng_states.id"))
    lga_of_origin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ng_lgas.id"))
    residence_country: Mapped[Optional[str]] = mapped_column(String(100))
    chapter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("chapters.id")
    )
    membership_number: Mapped[str] = mapped_column(String(30), nullable=False)
    membership_tier: Mapped[str] = mapped_column(String(30), nullable=False, default="standard")
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="standard_member")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), default=utcnow, onupdate=utcnow
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    chapter: Mapped[Optional["Chapter"]] = relationship(back_populates="members")
    profile: Mapped[Optional["MemberProfile"]] = relationship(back_populates="member", uselist=False)
    sessions: Mapped[list["MemberSession"]] = relationship(back_populates="member")

    __table_args__ = (
        # Partial unique indexes (soft-delete aware — mirrors
        # migrations/phase_d_02_members.sql exactly, so ORM-created and
        # migration-created tables are never out of sync. See Phase D.1
        # compliance report §7 for why this matters: a mismatch here bit us
        # in production last phase.)
        Index("ux_members_email_live", "email", unique=True, postgresql_where=text("deleted_at IS NULL")),
        Index("ux_members_membership_number_live", "membership_number", unique=True, postgresql_where=text("deleted_at IS NULL")),
        Index("ix_members_chapter_id", "chapter_id"),
        Index("ix_members_state_of_origin_id", "state_of_origin_id"),
        Index("ix_members_lga_of_origin_id", "lga_of_origin_id"),
        Index("ix_members_is_active", "is_active"),
        Index("ix_members_admin_user_id", "admin_user_id"),
    )


class MemberNumberCounter(Base):
    """
    Support table for atomic, per-year, gap-free-under-commit membership
    number generation (format NDIP-YYYY-000001). Not one of the four
    tables named in the D.2 directive — added and disclosed because the
    directive explicitly requires numbering to be "transaction safe" with
    "no duplicates under concurrent registration," which a naive
    COUNT(*)-based scheme cannot guarantee. See
    app/services/member_service.py and PHASE_D2_IMPLEMENTATION.md.
    """
    __tablename__ = "member_number_counters"

    year: Mapped[int] = mapped_column(primary_key=True)
    last_value: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), default=utcnow, onupdate=utcnow
    )
