"""
NDIP Phase D.3 — Authentication Service (D3.3)
File: app/services/auth_service.py

Implements the missing production authentication features on top of the
existing member_service.py infrastructure:
  - Email verification (token generation + confirmation)
  - Password reset (request + confirm)
  - Account lockout after repeated failures
  - Login throttling (per-email and per-IP)
  - Logout everywhere (revoke all sessions)

Does NOT duplicate anything in member_service.py. That service owns
registration/login/refresh/logout. This service owns the verification
and security hardening layer.

All token secrets are generated with secrets.token_urlsafe(48), then
bcrypt-hashed before storage. The raw token is returned to the caller
for delivery (via notification service) — it is never stored.
"""
import secrets
from datetime import timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text, func

from app.core.security import hash_password, verify_password
from app.models.models import utcnow
from app.models.member import Member
from app.repositories.member_repository import MemberRepository

# ─── Tunables ──────────────────────────────────────────────────────────────
EMAIL_VERIFY_TOKEN_EXPIRE_HOURS = 24
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 30
MAX_FAILED_ATTEMPTS_PER_EMAIL = 10   # within the window below
MAX_FAILED_ATTEMPTS_PER_IP = 20
LOCKOUT_WINDOW_MINUTES = 15
LOCKOUT_DURATION_MINUTES = 30
TOKEN_BYTES = 48


# ─── Exceptions ────────────────────────────────────────────────────────────
class AuthServiceError(Exception):
    pass

class AccountLockedError(AuthServiceError):
    pass

class TokenExpiredError(AuthServiceError):
    pass

class TokenAlreadyUsedError(AuthServiceError):
    pass

class InvalidTokenError(AuthServiceError):
    pass

class TooManyRequestsError(AuthServiceError):
    pass


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MemberRepository(db)

    # ─── Login throttling ──────────────────────────────────────────────────

    def record_login_attempt(
        self,
        email: str,
        success: bool,
        ip_address: Optional[str] = None,
    ) -> None:
        """Record a login attempt. Called by the members route after
        authenticate() returns or raises InvalidCredentialsError."""
        self.db.execute(text("""
            INSERT INTO login_attempts (email, ip_address, success)
            VALUES (:email, CAST(:ip AS INET), :success)
        """), {
            "email": email.lower().strip(),
            "ip": ip_address,
            "success": success,
        })
        self.db.commit()

    def check_lockout(self, email: str, ip_address: Optional[str] = None) -> None:
        """Raises AccountLockedError if the email or IP is currently locked
        out. Call this BEFORE attempting authentication."""
        window_start = utcnow() - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)

        # Check per-email failures
        email_failures = self.db.execute(text("""
            SELECT COUNT(*) FROM login_attempts
            WHERE email = :email
              AND success = FALSE
              AND created_at >= :window_start
        """), {"email": email.lower().strip(), "window_start": window_start}).scalar()

        if email_failures >= MAX_FAILED_ATTEMPTS_PER_EMAIL:
            raise AccountLockedError(
                f"Too many failed attempts. Please wait {LOCKOUT_DURATION_MINUTES} minutes "
                "before trying again, or use the password reset flow."
            )

        # Check per-IP failures (only when IP is provided)
        if ip_address:
            ip_failures = self.db.execute(text("""
                SELECT COUNT(*) FROM login_attempts
                WHERE ip_address = CAST(:ip AS INET)
                  AND success = FALSE
                  AND created_at >= :window_start
            """), {"ip": ip_address, "window_start": window_start}).scalar()

            if ip_failures >= MAX_FAILED_ATTEMPTS_PER_IP:
                raise AccountLockedError(
                    f"Too many failed attempts from this location. "
                    f"Please wait {LOCKOUT_DURATION_MINUTES} minutes."
                )

    # ─── Email verification ────────────────────────────────────────────────

    def create_verification_token(self, member_id: UUID) -> str:
        """Generate a verification token, store its hash, return the raw
        token for delivery. Any existing unused tokens for this member are
        invalidated first (one active token at a time)."""
        # Invalidate prior tokens
        self.db.execute(text("""
            UPDATE email_verification_tokens
            SET used_at = now()
            WHERE member_id = :member_id AND used_at IS NULL
        """), {"member_id": str(member_id)})

        raw_token = secrets.token_urlsafe(TOKEN_BYTES)
        token_hash = hash_password(raw_token)
        expires_at = utcnow() + timedelta(hours=EMAIL_VERIFY_TOKEN_EXPIRE_HOURS)

        self.db.execute(text("""
            INSERT INTO email_verification_tokens (member_id, token_hash, expires_at)
            VALUES (CAST(:member_id AS UUID), :token_hash, :expires_at)
        """), {
            "member_id": str(member_id),
            "token_hash": token_hash,
            "expires_at": expires_at,
        })
        self.db.commit()
        return raw_token

    def confirm_email_verification(self, member_id: UUID, raw_token: str) -> Member:
        """Verify the token and mark the member as verified."""
        row = self.db.execute(text("""
            SELECT id, token_hash, expires_at, used_at
            FROM email_verification_tokens
            WHERE member_id = CAST(:member_id AS UUID)
              AND used_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
        """), {"member_id": str(member_id)}).fetchone()

        if row is None:
            raise InvalidTokenError("No pending verification token found.")

        if row.used_at is not None:
            raise TokenAlreadyUsedError("This verification link has already been used.")

        if row.expires_at < utcnow():
            raise TokenExpiredError(
                "This verification link has expired. Please request a new one."
            )

        if not verify_password(raw_token, row.token_hash):
            raise InvalidTokenError("Invalid verification token.")

        # Mark token used
        self.db.execute(text("""
            UPDATE email_verification_tokens
            SET used_at = now()
            WHERE id = CAST(:id AS UUID)
        """), {"id": str(row.id)})

        # Mark member verified
        member = self.repo.find_by_id(member_id)
        if member is None:
            raise InvalidTokenError("Member not found.")
        member = self.repo.verify_member(member)
        self.db.commit()
        return member

    # ─── Password reset ────────────────────────────────────────────────────

    def create_password_reset_token(
        self,
        email: str,
        ip_address: Optional[str] = None,
    ) -> Optional[tuple[UUID, str]]:
        """Generate a password reset token. Returns (member_id, raw_token)
        or None if the email is not found (deliberately silent to prevent
        user enumeration — callers should always return 200 OK).

        Rate-limited: max 3 requests per email per hour."""
        member = self.repo.find_by_email(email.strip().lower())
        if member is None:
            return None  # Silent — do not reveal whether email exists

        # Rate limit: max 3 reset requests per hour per email
        one_hour_ago = utcnow() - timedelta(hours=1)
        recent_count = self.db.execute(text("""
            SELECT COUNT(*) FROM password_reset_tokens
            WHERE member_id = CAST(:member_id AS UUID)
              AND created_at >= :since
        """), {"member_id": str(member.id), "since": one_hour_ago}).scalar()

        if recent_count >= 3:
            raise TooManyRequestsError(
                "Too many password reset requests. Please wait before trying again."
            )

        # Invalidate prior tokens
        self.db.execute(text("""
            UPDATE password_reset_tokens
            SET used_at = now()
            WHERE member_id = CAST(:member_id AS UUID) AND used_at IS NULL
        """), {"member_id": str(member.id)})

        raw_token = secrets.token_urlsafe(TOKEN_BYTES)
        token_hash = hash_password(raw_token)
        expires_at = utcnow() + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)

        self.db.execute(text("""
            INSERT INTO password_reset_tokens (member_id, token_hash, expires_at, ip_address)
            VALUES (CAST(:member_id AS UUID), :token_hash, :expires_at, CAST(:ip AS INET))
        """), {
            "member_id": str(member.id),
            "token_hash": token_hash,
            "expires_at": expires_at,
            "ip": ip_address,
        })
        self.db.commit()
        return member.id, raw_token

    def confirm_password_reset(
        self,
        member_id: UUID,
        raw_token: str,
        new_password: str,
    ) -> Member:
        """Validate token and set the new password. Revokes all sessions
        (logout everywhere) after a successful reset."""
        from app.services.member_service import MemberService
        MemberService.validate_password_strength(new_password)

        row = self.db.execute(text("""
            SELECT id, token_hash, expires_at, used_at
            FROM password_reset_tokens
            WHERE member_id = CAST(:member_id AS UUID)
              AND used_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
        """), {"member_id": str(member_id)}).fetchone()

        if row is None:
            raise InvalidTokenError("No pending password reset token found.")

        if row.used_at is not None:
            raise TokenAlreadyUsedError("This reset link has already been used.")

        if row.expires_at < utcnow():
            raise TokenExpiredError(
                "This password reset link has expired. Please request a new one."
            )

        if not verify_password(raw_token, row.token_hash):
            raise InvalidTokenError("Invalid password reset token.")

        # Mark token used
        self.db.execute(text("""
            UPDATE password_reset_tokens
            SET used_at = now()
            WHERE id = CAST(:id AS UUID)
        """), {"id": str(row.id)})

        # Update password + revoke all sessions (logout everywhere)
        member = self.repo.find_by_id(member_id)
        if member is None:
            raise InvalidTokenError("Member not found.")

        member = self.repo.update_member(member, hashed_password=hash_password(new_password))
        self.repo.revoke_all_sessions_for_member(member_id)
        self.db.commit()
        return member

    # ─── Logout everywhere ─────────────────────────────────────────────────

    def logout_everywhere(self, member_id: UUID) -> int:
        """Revoke all active sessions for a member. Returns count revoked."""
        result = self.db.execute(text("""
            UPDATE member_sessions
            SET revoked_at = now()
            WHERE member_id = CAST(:member_id AS UUID)
              AND revoked_at IS NULL
        """), {"member_id": str(member_id)})
        self.db.commit()
        return result.rowcount

    # ─── Onboarding wizard state ───────────────────────────────────────────

    def get_or_create_onboarding_state(self, member_id: UUID) -> dict:
        """Return the member's onboarding wizard state, creating it if
        it doesn't exist (e.g. for members registered before D3.10)."""
        row = self.db.execute(text("""
            SELECT * FROM member_onboarding_state
            WHERE member_id = CAST(:member_id AS UUID)
        """), {"member_id": str(member_id)}).fetchone()

        if row is None:
            # Bootstrap from the member's current state
            member = self.repo.find_by_id(member_id)
            if member is None:
                raise InvalidTokenError("Member not found.")

            profile = self.repo.get_profile(member_id)
            photo_uploaded = bool(profile and profile.profile_photo_url)
            profile_completed = bool(
                profile and profile.occupation and profile.biography
            )
            state_selected = member.state_of_origin_id is not None
            lga_selected = member.lga_of_origin_id is not None
            chapter_confirmed = member.chapter_id is not None

            self.db.execute(text("""
                INSERT INTO member_onboarding_state
                    (member_id, email_verified, photo_uploaded, profile_completed,
                     state_selected, lga_selected, chapter_confirmed, wizard_completed,
                     completion_pct)
                VALUES
                    (CAST(:member_id AS UUID), :ev, :pu, :pc, :ss, :ls, :cc, :wc, :pct)
                ON CONFLICT (member_id) DO NOTHING
            """), {
                "member_id": str(member_id),
                "ev": member.is_verified,
                "pu": photo_uploaded,
                "pc": profile_completed,
                "ss": state_selected,
                "ls": lga_selected,
                "cc": chapter_confirmed,
                "wc": False,
                "pct": self._compute_pct(
                    member.is_verified, True, photo_uploaded, profile_completed,
                    state_selected, lga_selected, False, chapter_confirmed, False
                ),
            })
            self.db.commit()
            row = self.db.execute(text("""
                SELECT * FROM member_onboarding_state
                WHERE member_id = CAST(:member_id AS UUID)
            """), {"member_id": str(member_id)}).fetchone()

        return dict(row._mapping)

    def advance_onboarding_step(self, member_id: UUID, step_name: str, value: bool = True) -> dict:
        """Mark a wizard step as complete and recompute completion_pct."""
        valid_steps = {
            "email_verified", "photo_uploaded", "profile_completed",
            "state_selected", "lga_selected", "ward_selected",
            "chapter_confirmed", "terms_accepted", "wizard_completed",
        }
        if step_name not in valid_steps:
            raise ValueError(f"Unknown onboarding step: {step_name}")

        extra = {}
        if step_name == "terms_accepted" and value:
            extra["terms_accepted_at"] = utcnow()
        if step_name == "wizard_completed" and value:
            extra["wizard_completed_at"] = utcnow()

        self.db.execute(text(f"""
            UPDATE member_onboarding_state
            SET {step_name} = :value,
                updated_at = now()
            WHERE member_id = CAST(:member_id AS UUID)
        """), {"value": value, "member_id": str(member_id)})

        if extra:
            for col, val in extra.items():
                self.db.execute(text(f"""
                    UPDATE member_onboarding_state
                    SET {col} = :value
                    WHERE member_id = CAST(:member_id AS UUID)
                """), {"value": val, "member_id": str(member_id)})

        # Recompute completion percentage
        row = self.db.execute(text("""
            SELECT * FROM member_onboarding_state
            WHERE member_id = CAST(:member_id AS UUID)
        """), {"member_id": str(member_id)}).fetchone()

        if row:
            pct = self._compute_pct(
                row.email_verified, row.password_set, row.photo_uploaded,
                row.profile_completed, row.state_selected, row.lga_selected,
                row.ward_selected, row.chapter_confirmed, row.terms_accepted,
            )
            self.db.execute(text("""
                UPDATE member_onboarding_state
                SET completion_pct = :pct
                WHERE member_id = CAST(:member_id AS UUID)
            """), {"pct": pct, "member_id": str(member_id)})

        self.db.commit()
        return self.get_or_create_onboarding_state(member_id)

    @staticmethod
    def _compute_pct(*flags: bool) -> int:
        """Each wizard step is worth an equal share of 100%."""
        total = len(flags)
        completed = sum(1 for f in flags if f)
        return int((completed / total) * 100) if total else 0

    # ─── Cleanup ───────────────────────────────────────────────────────────

    def purge_expired_tokens(self) -> dict:
        """Called by the nightly cleanup job. Returns counts of purged rows."""
        now = utcnow()
        evt = self.db.execute(text("""
            DELETE FROM email_verification_tokens
            WHERE expires_at < :now AND used_at IS NOT NULL
        """), {"now": now}).rowcount

        prt = self.db.execute(text("""
            DELETE FROM password_reset_tokens
            WHERE expires_at < :now AND used_at IS NOT NULL
        """), {"now": now}).rowcount

        attempts = self.db.execute(text("""
            DELETE FROM login_attempts
            WHERE created_at < now() - INTERVAL '7 days'
        """)).rowcount

        sessions = self.db.execute(text("""
            DELETE FROM member_sessions
            WHERE expires_at < :now AND revoked_at IS NOT NULL
        """), {"now": now}).rowcount

        self.db.commit()
        return {
            "email_verification_tokens_purged": evt,
            "password_reset_tokens_purged": prt,
            "login_attempts_purged": attempts,
            "revoked_sessions_purged": sessions,
        }
