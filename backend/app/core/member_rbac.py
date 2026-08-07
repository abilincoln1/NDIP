"""
Phase D.2 — Members Foundation: member-facing RBAC.

Why this is a new file rather than an extension of app/core/rbac.py:
app/core/rbac.py's require_permission() resolves roles via three tables —
roles, permissions, role_permissions, user_roles — joined against
admin_users. Those tables have no migration anywhere in this codebase
(confirmed: no CREATE TABLE for any of them exists in migrations/, and
rbac.py's own _get_role_permissions() catches the resulting exception and
falls back to "allow all" — see its `except Exception: return {}` /
`if not role_permissions: return True`). That system is currently a
scaffold running in permissive/degraded mode, not a populated permission
store, and it is keyed to admin_users (staff), a different identity space
from members.

Building member RBAC on top of a table set that doesn't exist would
silently produce permission checks that always pass — worse than not
having the check at all. Per the D.2 directive's own instruction to
disclose every deviation, this is disclosed here and in
PHASE_D2_COMPLIANCE_REPORT.md rather than quietly reusing a scaffold.

Instead, member roles are resolved directly from the members table's
`role` column (populated at registration, changeable only through
MemberService — never trusted blindly from the JWT; see get_current_member
below). This follows the same *shape* as rbac.py — a reusable FastAPI
dependency factory, no per-endpoint hardcoding — while resolving against
data that actually exists.

JWT decoding, verification, and expiry are reused as-is from
app.core.security (create_access_token / decode_token / bearer_scheme) —
no second authentication framework was introduced, per the directive.
"""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.security import bearer_scheme, decode_token
from app.models.member import Member, MEMBER_ROLES


def get_current_member_claims(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Decode the bearer token and require it to be a member-scoped token
    (user_type == 'member'), not an admin token from app/core/security's
    existing /auth flow. Prevents an admin access token from being
    replayed against member endpoints and vice versa."""
    claims = decode_token(credentials.credentials)
    if claims.get("user_type") != "member":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not a member access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return claims


def get_current_member(
    claims: dict = Depends(get_current_member_claims),
    db: Session = Depends(get_db),
) -> Member:
    """
    Load the authenticated member fresh from the database on every request
    (rather than trusting the role/active/verified claims baked into the
    JWT at issuance time). This is a deliberate security choice: if an
    admin deactivates a member or changes their role, that change takes
    effect immediately, not after the access token happens to expire.
    """
    member_id = claims.get("member_id")
    member: Optional[Member] = (
        db.query(Member).filter(Member.id == member_id, Member.deleted_at.is_(None)).first()
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Member not found")
    if not member.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")
    return member


def require_member_role(*roles: str):
    """
    FastAPI dependency factory — the reusable, non-hardcoded permission
    mechanism the D.2 directive asks for.

    Usage:
        @router.get("/chapter/{chapter_id}/members")
        def list_chapter_members(
            member: Member = Depends(require_member_role("chapter_admin", "national_director", "super_admin")),
        ):
            ...
    """
    invalid = set(roles) - set(MEMBER_ROLES)
    if invalid:
        raise ValueError(f"Unknown member role(s) in require_member_role: {invalid}")

    def _check(member: Member = Depends(get_current_member)) -> Member:
        if member.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Requires one of: {', '.join(roles)}.",
            )
        return member

    return _check
