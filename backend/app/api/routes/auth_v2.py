"""
NDIP Phase D.3 — Auth V2 Router (D3.2 + D3.3)
File: app/api/routes/auth_v2.py

Implements /api/v2/auth endpoints:
  POST /api/v2/auth/verify-email/request   — send verification email
  POST /api/v2/auth/verify-email/confirm   — confirm token
  POST /api/v2/auth/password-reset/request — send reset email
  POST /api/v2/auth/password-reset/confirm — set new password
  POST /api/v2/auth/logout-everywhere      — revoke all sessions
  GET  /api/v2/auth/me                     — current authenticated member

The existing /auth router (Phase A admin auth) is NOT modified.
The existing /api/v2/members/login|register|refresh|logout (Phase D.2)
are NOT modified — they remain the primary session endpoints.
This router adds the verification and recovery flows on top.

All endpoints return consistent JSON responses:
  {"ok": true, "message": "...", "data": {...}}
  {"ok": false, "error": "...", "code": "ERROR_CODE"}
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.member_rbac import get_current_member
from app.models.member import Member
from app.services.auth_service import (
    AuthService,
    AccountLockedError,
    TokenExpiredError,
    TokenAlreadyUsedError,
    InvalidTokenError,
    TooManyRequestsError,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/api/v2/auth", tags=["auth_v2"])


# ─── Schemas ───────────────────────────────────────────────────────────────

class EmailVerifyRequestIn(BaseModel):
    member_id: UUID


class EmailVerifyConfirmIn(BaseModel):
    member_id: UUID
    token: str


class PasswordResetRequestIn(BaseModel):
    email: EmailStr


class PasswordResetConfirmIn(BaseModel):
    member_id: UUID
    token: str
    new_password: str


# ─── Helpers ───────────────────────────────────────────────────────────────

def _ok(message: str, data: Optional[dict] = None) -> dict:
    return {"ok": True, "message": message, "data": data or {}}


def _client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _map_auth_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AccountLockedError):
        return HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))
    if isinstance(exc, TooManyRequestsError):
        return HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))
    if isinstance(exc, TokenExpiredError):
        return HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc))
    if isinstance(exc, TokenAlreadyUsedError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, InvalidTokenError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")


# ─── Email verification ────────────────────────────────────────────────────

@router.post("/verify-email/request", summary="Request email verification link")
def request_email_verification(
    payload: EmailVerifyRequestIn,
    db: Session = Depends(get_db),
    member: Member = Depends(get_current_member),
):
    """
    Generates and sends an email verification link for the authenticated
    member. Rate-limited: the auth service allows one active token at a
    time (previous tokens are invalidated on each request).

    Authorization: any authenticated member may request for their own account.
    """
    if member.id != payload.member_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You may only request verification for your own account.",
        )
    if member.is_verified:
        return _ok("Email is already verified.")

    auth_svc = AuthService(db)
    notif_svc = NotificationService(db)

    raw_token = auth_svc.create_verification_token(member.id)
    notif_svc.send_email_verification(
        member_id=member.id,
        email=member.email,
        full_name=member.full_name,
        raw_token=raw_token,
    )

    return _ok("Verification email sent. Please check your inbox.")


@router.post("/verify-email/confirm", summary="Confirm email verification token")
def confirm_email_verification(
    payload: EmailVerifyConfirmIn,
    db: Session = Depends(get_db),
):
    """
    Public endpoint — no auth required (the token itself is the credential).
    Marks the member as verified and advances their onboarding wizard.
    """
    auth_svc = AuthService(db)
    try:
        member = auth_svc.confirm_email_verification(payload.member_id, payload.token)
    except Exception as exc:
        raise _map_auth_error(exc)

    # Advance onboarding wizard step
    try:
        auth_svc.advance_onboarding_step(member.id, "email_verified", True)
    except Exception:
        pass  # Non-fatal — verification succeeded, wizard update is best-effort

    return _ok(
        "Email verified successfully. You now have Verified Member status.",
        data={"member_id": str(member.id), "is_verified": member.is_verified},
    )


# ─── Password reset ────────────────────────────────────────────────────────

@router.post("/password-reset/request", summary="Request password reset email")
def request_password_reset(
    payload: PasswordResetRequestIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Public endpoint. Always returns 200 OK regardless of whether the email
    exists — this prevents user enumeration.
    Rate-limited: max 3 requests per email per hour.
    """
    auth_svc = AuthService(db)
    notif_svc = NotificationService(db)
    ip = _client_ip(request)

    try:
        result = auth_svc.create_password_reset_token(str(payload.email), ip_address=ip)
    except TooManyRequestsError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))

    if result is not None:
        member_id, raw_token = result
        # Look up member details for the email template
        from app.repositories.member_repository import MemberRepository
        repo = MemberRepository(db)
        member = repo.find_by_id(member_id)
        if member:
            notif_svc.send_password_reset(
                member_id=member_id,
                email=member.email,
                full_name=member.full_name,
                raw_token=raw_token,
            )

    # Always return the same response to prevent email enumeration
    return _ok(
        "If an account exists for this email, a password reset link has been sent."
    )


@router.post("/password-reset/confirm", summary="Set new password using reset token")
def confirm_password_reset(
    payload: PasswordResetConfirmIn,
    db: Session = Depends(get_db),
):
    """
    Public endpoint. Sets the new password and revokes all active sessions
    (logout everywhere). The member must log in again after reset.
    """
    auth_svc = AuthService(db)
    try:
        auth_svc.confirm_password_reset(payload.member_id, payload.token, payload.new_password)
    except Exception as exc:
        raise _map_auth_error(exc)

    return _ok(
        "Password reset successfully. All active sessions have been revoked. "
        "Please log in with your new password.",
        data={"member_id": str(payload.member_id)},
    )


# ─── Logout everywhere ─────────────────────────────────────────────────────

@router.post("/logout-everywhere", summary="Revoke all active sessions")
def logout_everywhere(
    db: Session = Depends(get_db),
    member: Member = Depends(get_current_member),
):
    """
    Revokes every active refresh token for the authenticated member.
    The current access token remains valid until it expires (max 30 min).
    Use this when a device is lost or suspected compromise is detected.
    """
    auth_svc = AuthService(db)
    count = auth_svc.logout_everywhere(member.id)
    return _ok(
        f"All sessions revoked. {count} active session(s) terminated.",
        data={"sessions_revoked": count},
    )


# ─── Current member ────────────────────────────────────────────────────────

@router.get("/me", summary="Current authenticated member summary")
def get_me(member: Member = Depends(get_current_member)):
    """
    Lightweight current-member endpoint for the frontend to verify
    token validity and retrieve core identity without a full dashboard load.
    """
    return _ok("Authenticated", data={
        "id": str(member.id),
        "email": member.email,
        "full_name": member.full_name,
        "membership_number": member.membership_number,
        "role": member.role,
        "membership_tier": member.membership_tier,
        "is_verified": member.is_verified,
        "is_active": member.is_active,
        "chapter_id": str(member.chapter_id) if member.chapter_id else None,
    })


# ─── Onboarding wizard ─────────────────────────────────────────────────────

@router.get("/onboarding", summary="Member onboarding wizard state")
def get_onboarding_state(
    db: Session = Depends(get_db),
    member: Member = Depends(get_current_member),
):
    """Returns the member's first-login wizard completion state."""
    auth_svc = AuthService(db)
    state = auth_svc.get_or_create_onboarding_state(member.id)
    return _ok("Onboarding state", data=state)


@router.post("/onboarding/step", summary="Advance onboarding wizard step")
def advance_onboarding(
    payload: dict,
    db: Session = Depends(get_db),
    member: Member = Depends(get_current_member),
):
    """
    Mark an onboarding wizard step as complete.
    Payload: {"step": "email_verified"|"photo_uploaded"|"profile_completed"|
                       "state_selected"|"lga_selected"|"ward_selected"|
                       "chapter_confirmed"|"terms_accepted"|"wizard_completed"}
    """
    step = payload.get("step")
    if not step:
        raise HTTPException(status_code=400, detail="Missing 'step' in request body.")

    auth_svc = AuthService(db)
    try:
        state = auth_svc.advance_onboarding_step(member.id, step, True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return _ok(f"Step '{step}' marked complete.", data=state)
