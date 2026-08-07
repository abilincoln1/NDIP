"""
Phase D.2 — Members Foundation: MemberSession model.

Stores refresh-token sessions. Only a bcrypt hash of the refresh token is
ever stored (see app/services/member_service.py) — never the raw token.
"""
import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.models import utcnow

if TYPE_CHECKING:
    from app.models.member import Member


class MemberSession(Base):
    __tablename__ = "member_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("members.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64))
    device: Mapped[Optional[str]] = mapped_column(String(255))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), default=utcnow
    )

    member: Mapped["Member"] = relationship(back_populates="sessions")

    __table_args__ = (
        Index("ix_member_sessions_member_id", "member_id"),
        Index("ix_member_sessions_expires_at", "expires_at"),
        Index("ix_member_sessions_revoked_at", "revoked_at"),
    )
