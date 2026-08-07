"""
Phase D.2 — Members Foundation: service layer.

All business logic for the member subsystem lives here: registration,
authentication, JWT issuance/refresh, membership-number generation,
profile management, chapter assignment, verification, activation, and
password policy. The repository layer (app/repositories/member_repository.py)
is DB-access only and contains none of this.

Authentication reuses the existing app.core.security infrastructure
(bcrypt hashing via hash_password/verify_password, JWT via
create_access_token) rather than introducing a second auth framework, per
the D.2 directive. Member tokens are distinguished from admin tokens by a
"user_type": "member" claim, checked in app/core/member_rbac.py.
"""
import re
import secrets
import unicodedata
from datetime import timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.models.models import utcnow
from app.models.member import Member
from app.models.member_profile import MemberProfile
from app.repositories.member_repository import MemberRepository

# ─── Tunables ───────────────────────────────────────────────────────────────
# Kept local to this service rather than added to app/core/config.py's global
# Settings, since these apply only to member tokens (admin tokens keep using
# settings.access_token_expire_minutes = 1440). See PHASE_D2_IMPLEMENTATION.md.
MEMBER_ACCESS_TOKEN_EXPIRE_MINUTES = 30
MEMBER_REFRESH_TOKEN_EXPIRE_DAYS = 30

# bcrypt has a 72-byte input limit; hashing a fixed dummy value once at
# import time gives authenticate() a constant-shape bcrypt call to make
# even when the email doesn't exist, so response timing doesn't reveal
# whether an email is registered (D.2 directive, Security: "timing attacks").
_DUMMY_PASSWORD_HASH = hash_password("ndip-timing-safety-placeholder-value")


# ─── Errors ─────────────────────────────────────────────────────────────────
# Plain exceptions, translated to HTTP responses in app/api/routes/members.py
# — keeps the service layer framework-agnostic (no FastAPI/HTTPException
# imports here), matching the repository/service split's intent.

class MemberServiceError(Exception):
    pass


class DuplicateEmailError(MemberServiceError):
    pass


class WeakPasswordError(MemberServiceError):
    pass


class InvalidCredentialsError(MemberServiceError):
    pass


class InactiveAccountError(MemberServiceError):
    pass


class NotFoundError(MemberServiceError):
    pass


class MemberService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MemberRepository(db)

    # ─── Sanitisation / validation ──────────────────────────────────────

    @staticmethod
    def _sanitize_text(value: Optional[str]) -> Optional[str]:
        """Strip whitespace and control/NUL characters from free-text input.
        This is a JSON API (no HTML templating in this module), so the
        primary XSS surface is a downstream consumer rendering these
        fields unescaped — stripping control characters and normalising
        unicode removes the most common injection vectors without
        mangling legitimate names (e.g. accented characters)."""
        if value is None:
            return None
        value = unicodedata.normalize("NFKC", value)
        value = "".join(ch for ch in value if ch == "\n" or ch == "\t" or not unicodedata.category(ch).startswith("C"))
        return value.strip()

    @staticmethod
    def validate_password_strength(password: str) -> None:
        if len(password) < 8:
            raise WeakPasswordError("Password must be at least 8 characters long.")
        if len(password) > 72:
            raise WeakPasswordError("Password must be at most 72 characters long.")
        if not re.search(r"[A-Z]", password):
            raise WeakPasswordError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", password):
            raise WeakPasswordError("Password must contain at least one lowercase letter.")
        if not re.search(r"[0-9]", password):
            raise WeakPasswordError("Password must contain at least one digit.")

    # ─── Membership number generation ───────────────────────────────────

    def generate_membership_number(self, year: Optional[int] = None) -> str:
        """Format: NDIP-YYYY-000001. Sequential and unique per year via
        MemberRepository.lock_and_increment_counter, which row-locks the
        counter for `year` for the duration of the enclosing transaction —
        safe under concurrent registration (see repository docstring)."""
        year = year or utcnow().year
        sequence = self.repo.lock_and_increment_counter(year)
        return f"NDIP-{year}-{sequence:06d}"

    # ─── Registration ────────────────────────────────────────────────────

    def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        phone: Optional[str] = None,
        state_of_origin_id: Optional[int] = None,
        lga_of_origin_id: Optional[int] = None,
        residence_country: Optional[str] = None,
        chapter_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        device: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> tuple[Member, str, str]:
        """Returns (member, access_token, refresh_token) — registration
        issues tokens directly rather than re-authenticating with the
        just-hashed password (that would double the bcrypt cost of every
        registration for no security benefit, since the caller already
        proved the password by successfully forming this request)."""
        email = email.strip().lower()
        full_name = self._sanitize_text(full_name)
        phone = self._sanitize_text(phone)
        residence_country = self._sanitize_text(residence_country)

        if self.repo.find_by_email(email) is not None:
            raise DuplicateEmailError(f"Email already registered: {email}")

        self.validate_password_strength(password)

        if chapter_id is not None and self.repo.get_chapter(chapter_id) is None:
            raise NotFoundError(f"Chapter not found: {chapter_id}")

        membership_number = self.generate_membership_number()

        try:
            member = self.repo.create_member(
                email=email,
                hashed_password=hash_password(password),
                full_name=full_name,
                phone=phone,
                state_of_origin_id=state_of_origin_id,
                lga_of_origin_id=lga_of_origin_id,
                residence_country=residence_country,
                chapter_id=chapter_id,
                membership_number=membership_number,
                membership_tier="standard",
                role="standard_member",
                is_active=True,
                is_verified=False,
            )
            self.repo.create_profile(member.id)
            access_token = self._issue_access_token(member)
            refresh_token = self._issue_refresh_token(member, ip_address, device, user_agent)
            self.db.commit()
        except IntegrityError:
            # Defense in depth: the pre-check above closes the common case,
            # but a concurrent registration with the same email racing
            # between the check and the commit is still possible — the
            # partial unique index (see migrations/phase_d_02_members.sql)
            # is the actual source of truth and will raise here if so.
            self.db.rollback()
            raise DuplicateEmailError(f"Email already registered: {email}")

        self.db.refresh(member)
        return member, access_token, refresh_token

    # ─── Authentication ──────────────────────────────────────────────────

    def authenticate(
        self,
        *,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        device: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> tuple[Member, str, str]:
        """Returns (member, access_token, refresh_token). Raises
        InvalidCredentialsError / InactiveAccountError on failure."""
        member = self.repo.find_by_email(email.strip().lower())

        # Always run a bcrypt comparison, even when no member was found, so
        # the response time for "unknown email" and "wrong password" is the
        # same shape of work (see _DUMMY_PASSWORD_HASH above).
        hash_to_check = member.hashed_password if member else _DUMMY_PASSWORD_HASH
        password_ok = verify_password(password, hash_to_check)

        if member is None or not password_ok:
            raise InvalidCredentialsError("Invalid email or password")
        if not member.is_active:
            raise InactiveAccountError("Account is deactivated")

        access_token = self._issue_access_token(member)
        refresh_token = self._issue_refresh_token(member, ip_address, device, user_agent)
        self.db.commit()
        return member, access_token, refresh_token

    def _issue_access_token(self, member: Member) -> str:
        payload = {
            "sub": str(member.id),
            "member_id": str(member.id),
            "membership_number": member.membership_number,
            "chapter_id": str(member.chapter_id) if member.chapter_id else None,
            "role": member.role,
            "user_type": "member",
            "verified": member.is_verified,
            "active": member.is_active,
        }
        return create_access_token(payload, expires_delta=timedelta(minutes=MEMBER_ACCESS_TOKEN_EXPIRE_MINUTES))

    def _issue_refresh_token(
        self,
        member: Member,
        ip_address: Optional[str],
        device: Optional[str],
        user_agent: Optional[str],
    ) -> str:
        raw_secret = secrets.token_urlsafe(48)
        session = self.repo.create_session(
            member_id=member.id,
            refresh_token_hash=hash_password(raw_secret),
            ip_address=ip_address,
            device=device,
            user_agent=user_agent,
            expires_at=utcnow() + timedelta(days=MEMBER_REFRESH_TOKEN_EXPIRE_DAYS),
        )
        # The returned refresh token embeds the session id so refresh()/
        # logout() can look up the exact session row in O(1) instead of
        # re-hashing (bcrypt is deliberately slow) against every active
        # session for this member. Only the bcrypt hash is ever persisted —
        # this raw value exists only in the HTTP response.
        return f"{session.id}.{raw_secret}"

    @staticmethod
    def _split_refresh_token(refresh_token: str) -> tuple[UUID, str]:
        try:
            session_id_str, raw_secret = refresh_token.split(".", 1)
            return UUID(session_id_str), raw_secret
        except (ValueError, AttributeError, TypeError):
            raise InvalidCredentialsError("Invalid refresh token")

    def refresh(self, refresh_token: str) -> tuple[str, str]:
        """Validates and rotates a refresh token. Returns
        (new_access_token, new_refresh_token)."""
        session_id, raw_secret = self._split_refresh_token(refresh_token)
        session = self.repo.get_session(session_id)

        if session is None or session.revoked_at is not None or session.expires_at < utcnow():
            raise InvalidCredentialsError("Refresh token is invalid, expired, or revoked")
        if not verify_password(raw_secret, session.refresh_token_hash):
            raise InvalidCredentialsError("Invalid refresh token")

        member = self.repo.find_by_id(session.member_id)
        if member is None:
            raise InvalidCredentialsError("Invalid refresh token")
        if not member.is_active:
            raise InactiveAccountError("Account is deactivated")

        # Rotation: the presented refresh token is single-use.
        self.repo.revoke_session(session)
        new_access_token = self._issue_access_token(member)
        new_refresh_token = self._issue_refresh_token(member, session.ip_address, session.device, session.user_agent)
        self.db.commit()
        return new_access_token, new_refresh_token

    def logout(self, refresh_token: str) -> None:
        """Revokes the session backing this refresh token. Idempotent and
        silent on an already-invalid token — logout should never error."""
        try:
            session_id, _ = self._split_refresh_token(refresh_token)
        except InvalidCredentialsError:
            return
        session = self.repo.get_session(session_id)
        if session is not None and session.revoked_at is None:
            self.repo.revoke_session(session)
            self.db.commit()

    # ─── Profile / chapter / dashboard ───────────────────────────────────

    _MEMBER_UPDATABLE_FIELDS = {"full_name", "phone", "residence_country"}
    _PROFILE_UPDATABLE_FIELDS = {
        "date_of_birth", "gender", "occupation", "organisation", "biography",
        "skills", "interests", "languages", "profile_photo_url",
        "linkedin_url", "facebook_url", "twitter_url", "website",
    }

    def get_profile(self, member: Member) -> Optional[MemberProfile]:
        return self.repo.get_profile(member.id)

    def update_me(self, member: Member, updates: dict) -> Member:
        text_fields = {"full_name", "phone", "residence_country", "occupation", "organisation", "biography"}
        updates = {
            k: (self._sanitize_text(v) if k in text_fields and isinstance(v, str) else v)
            for k, v in updates.items()
            if v is not None
        }
        member_fields = {k: v for k, v in updates.items() if k in self._MEMBER_UPDATABLE_FIELDS}
        profile_fields = {k: v for k, v in updates.items() if k in self._PROFILE_UPDATABLE_FIELDS}

        if member_fields:
            self.repo.update_member(member, **member_fields)
        if profile_fields:
            profile = self.repo.get_profile(member.id)
            if profile is None:
                self.repo.create_profile(member.id, **profile_fields)
            else:
                self.repo.update_profile(profile, **profile_fields)

        self.db.commit()
        self.db.refresh(member)
        return member

    def assign_chapter(self, member: Member, chapter_id: UUID) -> Member:
        if self.repo.get_chapter(chapter_id) is None:
            raise NotFoundError(f"Chapter not found: {chapter_id}")
        member = self.repo.assign_chapter(member, chapter_id)
        self.db.commit()
        return member

    def get_dashboard(self, member: Member) -> dict:
        """Members-Foundation dashboard scaffold. impact_score and
        recent_activity are explicit placeholders — the D.2 directive
        requires the shape to exist without computing real Impact Index
        values, which belong to a later phase."""
        chapter = self.repo.get_chapter(member.chapter_id) if member.chapter_id else None
        return {
            "member_summary": {
                "id": str(member.id),
                "full_name": member.full_name,
                "membership_number": member.membership_number,
                "membership_tier": member.membership_tier,
                "role": member.role,
                "is_verified": member.is_verified,
                "is_active": member.is_active,
            },
            "chapter": (
                {"id": str(chapter.id), "name": chapter.name, "country": chapter.country}
                if chapter is not None
                else None
            ),
            "verification_status": "verified" if member.is_verified else "unverified",
            "impact_score": None,
            "recent_activity": [],
        }

    # ─── Verification / activation (service methods — no API route wired
    # yet; see PHASE_D2_IMPLEMENTATION.md "Known Limitations") ───────────

    def verify_member(self, member: Member) -> Member:
        member = self.repo.verify_member(member)
        self.db.commit()
        return member

    def activate_member(self, member: Member) -> Member:
        member = self.repo.update_member(member, is_active=True)
        self.db.commit()
        return member

    def deactivate_member(self, member: Member) -> Member:
        member = self.repo.deactivate_member(member)
        self.repo.revoke_all_sessions_for_member(member.id)
        self.db.commit()
        return member

    # ─── Search / listing ────────────────────────────────────────────────

    def search_members(self, **kwargs) -> dict:
        return self.repo.search_members(**kwargs)

    def list_chapter_members(self, chapter_id: UUID, page: int = 1, page_size: int = 50) -> dict:
        if self.repo.get_chapter(chapter_id) is None:
            raise NotFoundError(f"Chapter not found: {chapter_id}")
        return self.repo.list_chapter_members(chapter_id, page=page, page_size=page_size)
