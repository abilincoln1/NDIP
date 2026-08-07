"""
Phase D.2 — Members Foundation: repository layer.

Database access only — no password hashing, no JWT creation, no
membership-number formatting, no validation rules. Those live in
app/services/member_service.py. This mirrors the repository/service split
established in Phase D.1 (app/repositories/geography_repository.py).

Covers members, chapters (read + assignment), member_profiles,
member_sessions, and the member_number_counters support table — kept in
one file because the D.2 directive names exactly one repository file
(repositories/member_repository.py).
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.member import Member, MemberNumberCounter
from app.models.models import utcnow
from app.models.chapter import Chapter
from app.models.member_profile import MemberProfile
from app.models.member_session import MemberSession


class MemberRepository:
    def __init__(self, db: Session):
        self.db = db

    # ─── Members ────────────────────────────────────────────────────────

    def create_member(self, **fields) -> Member:
        member = Member(**fields)
        self.db.add(member)
        self.db.flush()  # populate member.id without ending the transaction —
        # membership-number generation and profile creation happen in the
        # same DB transaction in the service layer.
        return member

    def update_member(self, member: Member, **fields) -> Member:
        for key, value in fields.items():
            setattr(member, key, value)
        self.db.flush()
        return member

    def find_by_email(self, email: str, include_deleted: bool = False) -> Optional[Member]:
        q = self.db.query(Member).filter(func.lower(Member.email) == email.lower().strip())
        if not include_deleted:
            q = q.filter(Member.deleted_at.is_(None))
        return q.first()

    def find_by_membership_number(self, membership_number: str) -> Optional[Member]:
        return (
            self.db.query(Member)
            .filter(Member.membership_number == membership_number, Member.deleted_at.is_(None))
            .first()
        )

    def find_by_id(self, member_id, include_deleted: bool = False) -> Optional[Member]:
        q = self.db.query(Member).options(joinedload(Member.chapter), joinedload(Member.profile))
        q = q.filter(Member.id == member_id)
        if not include_deleted:
            q = q.filter(Member.deleted_at.is_(None))
        return q.first()

    def search_members(
        self,
        q: Optional[str] = None,
        chapter_id: Optional[UUID] = None,
        state_of_origin_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        query = self.db.query(Member).filter(Member.deleted_at.is_(None))
        if q:
            like = f"%{q.strip()}%"
            query = query.filter(
                (Member.full_name.ilike(like))
                | (Member.email.ilike(like))
                | (Member.membership_number.ilike(like))
            )
        if chapter_id is not None:
            query = query.filter(Member.chapter_id == chapter_id)
        if state_of_origin_id is not None:
            query = query.filter(Member.state_of_origin_id == state_of_origin_id)
        if is_active is not None:
            query = query.filter(Member.is_active == is_active)

        total = query.count()
        rows = (
            query.order_by(Member.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return {"items": rows, "total": total, "page": page, "page_size": page_size}

    def assign_chapter(self, member: Member, chapter_id) -> Member:
        member.chapter_id = chapter_id
        self.db.flush()
        return member

    def verify_member(self, member: Member) -> Member:
        member.is_verified = True
        self.db.flush()
        return member

    def deactivate_member(self, member: Member) -> Member:
        member.is_active = False
        self.db.flush()
        return member

    def soft_delete_member(self, member: Member) -> Member:
        member.deleted_at = utcnow()
        member.is_active = False
        self.db.flush()
        return member

    def list_chapter_members(self, chapter_id, page: int = 1, page_size: int = 50) -> dict:
        query = (
            self.db.query(Member)
            .filter(Member.chapter_id == chapter_id, Member.deleted_at.is_(None))
        )
        total = query.count()
        rows = (
            query.order_by(Member.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return {"items": rows, "total": total, "page": page, "page_size": page_size}

    # ─── Chapters (read-side support for assignment/listing) ──────────────

    def get_chapter(self, chapter_id) -> Optional[Chapter]:
        return (
            self.db.query(Chapter)
            .filter(Chapter.id == chapter_id, Chapter.deleted_at.is_(None))
            .first()
        )

    # ─── Profiles (one-to-one) ──────────────────────────────────────────

    def get_profile(self, member_id) -> Optional[MemberProfile]:
        return (
            self.db.query(MemberProfile)
            .filter(MemberProfile.member_id == member_id, MemberProfile.deleted_at.is_(None))
            .first()
        )

    def create_profile(self, member_id, **fields) -> MemberProfile:
        profile = MemberProfile(member_id=member_id, **fields)
        self.db.add(profile)
        self.db.flush()
        return profile

    def update_profile(self, profile: MemberProfile, **fields) -> MemberProfile:
        for key, value in fields.items():
            setattr(profile, key, value)
        self.db.flush()
        return profile

    def touch_last_login(self, profile: MemberProfile) -> None:
        profile.last_login = utcnow()
        self.db.flush()

    # ─── Sessions (refresh tokens) ──────────────────────────────────────

    def create_session(self, **fields) -> MemberSession:
        session = MemberSession(**fields)
        self.db.add(session)
        self.db.flush()
        return session

    def get_session(self, session_id) -> Optional[MemberSession]:
        return self.db.query(MemberSession).filter(MemberSession.id == session_id).first()

    def get_active_sessions_for_member(self, member_id) -> list[MemberSession]:
        return (
            self.db.query(MemberSession)
            .filter(
                MemberSession.member_id == member_id,
                MemberSession.revoked_at.is_(None),
                MemberSession.expires_at > utcnow(),
            )
            .all()
        )

    def revoke_session(self, session: MemberSession) -> MemberSession:
        session.revoked_at = utcnow()
        self.db.flush()
        return session

    def revoke_all_sessions_for_member(self, member_id) -> int:
        sessions = (
            self.db.query(MemberSession)
            .filter(MemberSession.member_id == member_id, MemberSession.revoked_at.is_(None))
            .all()
        )
        for s in sessions:
            s.revoked_at = utcnow()
        self.db.flush()
        return len(sessions)

    # ─── Membership number counter ──────────────────────────────────────

    def lock_and_increment_counter(self, year: int) -> int:
        """
        Atomically increment and return the running sequence for `year`.
        Uses SELECT ... FOR UPDATE so concurrent registrations serialize on
        this single row instead of racing on a COUNT(*)-derived number.
        Must be called inside the same DB transaction as the member INSERT
        (see MemberService.register) so a rolled-back registration also
        rolls back its counter increment.
        """
        counter = (
            self.db.query(MemberNumberCounter)
            .filter(MemberNumberCounter.year == year)
            .with_for_update()
            .first()
        )
        if counter is None:
            # First registration of the year. INSERT then re-select FOR
            # UPDATE to close the (rare) race where two transactions both
            # find no row and both try to insert — the loser's insert
            # blocks on the unique PK, then sees the winner's row.
            counter = MemberNumberCounter(year=year, last_value=0)
            self.db.add(counter)
            self.db.flush()
            counter = (
                self.db.query(MemberNumberCounter)
                .filter(MemberNumberCounter.year == year)
                .with_for_update()
                .first()
            )
        counter.last_value += 1
        self.db.flush()
        return counter.last_value

    # ─── Seed-integrity / counts (used by tests) ─────────────────────────

    def counts(self) -> dict:
        return {
            "chapters": self.db.query(Chapter).filter(Chapter.deleted_at.is_(None)).count(),
            "members": self.db.query(Member).filter(Member.deleted_at.is_(None)).count(),
        }
