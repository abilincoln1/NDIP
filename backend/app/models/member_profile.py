"""Phase D.2 — Members Foundation: MemberProfile model (one-to-one with Member)."""
import uuid
from datetime import date, datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, Date, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.models import utcnow

if TYPE_CHECKING:
    from app.models.member import Member


class MemberProfile(Base):
    __tablename__ = "member_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("members.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date)
    gender: Mapped[Optional[str]] = mapped_column(String(30))
    occupation: Mapped[Optional[str]] = mapped_column(String(150))
    organisation: Mapped[Optional[str]] = mapped_column(String(200))
    biography: Mapped[Optional[str]] = mapped_column(Text)
    skills: Mapped[Optional[list]] = mapped_column(JSONB)
    interests: Mapped[Optional[list]] = mapped_column(JSONB)
    languages: Mapped[Optional[list]] = mapped_column(JSONB)
    profile_photo_url: Mapped[Optional[str]] = mapped_column(String(500))
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500))
    facebook_url: Mapped[Optional[str]] = mapped_column(String(500))
    twitter_url: Mapped[Optional[str]] = mapped_column(String(500))
    website: Mapped[Optional[str]] = mapped_column(String(500))
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), default=utcnow, onupdate=utcnow
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    member: Mapped["Member"] = relationship(back_populates="profile")
