"""
Phase D.2 — Members Foundation: API layer.

Prefix: /api/v2/members (matches the /api/v2/geography convention
established in Phase D.1). Error translation from the framework-agnostic
service-layer exceptions (app/services/member_service.py) into HTTP
responses happens only here — the service layer raises plain Python
exceptions and never imports FastAPI.

Access policy assumptions (disclosed — no explicit policy was specified
for these two routes in the D.2 directive):
  - GET /profile/{member_id}: any authenticated member may view another
    member's public profile (no PII beyond what MemberResponse/
    ProfileResponse already expose — no hashed_password, no session data).
  - GET /chapter/{chapter_id}/members: restricted to chapter_admin,
    national_director, or super_admin — a full member roster is more
    sensitive than a single profile.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.member import Member
from app.core.member_rbac import get_current_member, require_member_role
from app.services.member_service import (
    MemberService,
    DuplicateEmailError,
    WeakPasswordError,
    InvalidCredentialsError,
    InactiveAccountError,
    NotFoundError,
)
from app.schemas.member_schemas import (
    RegistrationRequest,
    LoginRequest,
    RefreshRequest,
    UpdateProfileRequest,
    MemberResponse,
    MemberListResponse,
    MemberTokenResponse,
    ProfileResponse,
    DashboardResponse,
)

router = APIRouter(prefix="/api/v2/members", tags=["members"])


def _client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/register", response_model=MemberTokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegistrationRequest, request: Request, db: Session = Depends(get_db)):
    service = MemberService(db)
    try:
        member, access_token, refresh_token = service.register(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            phone=payload.phone,
            state_of_origin_id=payload.state_of_origin_id,
            lga_of_origin_id=payload.lga_of_origin_id,
            residence_country=payload.residence_country,
            chapter_id=payload.chapter_id,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except DuplicateEmailError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except WeakPasswordError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return MemberTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        member=MemberResponse.model_validate(member),
    )


@router.post("/login", response_model=MemberTokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    service = MemberService(db)
    try:
        member, access_token, refresh_token = service.authenticate(
            email=payload.email,
            password=payload.password,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except InvalidCredentialsError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    except InactiveAccountError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    return MemberTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        member=MemberResponse.model_validate(member),
    )


@router.post("/refresh", response_model=MemberTokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    service = MemberService(db)
    try:
        access_token, refresh_token = service.refresh(payload.refresh_token)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except InactiveAccountError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    # Re-derive the member for the response body without a second DB round
    # trip on member_id parsed out of the fresh access token would require
    # decoding it here; simplest correct approach is to look the member up
    # via the (now-rotated) session's member_id through the repository.
    session_id, _ = MemberService._split_refresh_token(refresh_token)
    session = service.repo.get_session(session_id)
    member = service.repo.find_by_id(session.member_id)

    return MemberTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        member=MemberResponse.model_validate(member),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    service = MemberService(db)
    service.logout(payload.refresh_token)
    return None


@router.get("/me", response_model=MemberResponse)
def get_me(member: Member = Depends(get_current_member)):
    return member


@router.put("/me", response_model=MemberResponse)
def update_me(
    payload: UpdateProfileRequest,
    member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    service = MemberService(db)
    updated = service.update_me(member, payload.model_dump(exclude_unset=True))
    return updated


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(member: Member = Depends(get_current_member), db: Session = Depends(get_db)):
    service = MemberService(db)
    return service.get_dashboard(member)


@router.get("/profile/{member_id}", response_model=ProfileResponse)
def get_profile(
    member_id: UUID,
    _: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    from app.repositories.member_repository import MemberRepository

    repo = MemberRepository(db)
    target = repo.find_by_id(member_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Member {member_id} not found")
    profile = repo.get_profile(member_id)
    if profile is None:
        # A member always gets a profile row created at registration
        # (MemberService.register), so this indicates a member created
        # through some other path — return an empty-but-valid profile
        # rather than a 404 for a member that does exist.
        return ProfileResponse(member_id=member_id)
    return profile


@router.get("/chapter/{chapter_id}/members", response_model=MemberListResponse)
def list_chapter_members(
    chapter_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    _: Member = Depends(require_member_role("chapter_admin", "national_director", "super_admin")),
    db: Session = Depends(get_db),
):
    service = MemberService(db)
    try:
        result = service.list_chapter_members(chapter_id, page=page, page_size=page_size)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return result
