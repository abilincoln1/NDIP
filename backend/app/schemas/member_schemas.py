"""
Phase D.2 — Members Foundation: Pydantic schemas.

Follows the same convention as app/schemas/schemas.py and
app/schemas/geography_schemas.py — real pydantic BaseModel, EmailStr,
Field, `class Config: from_attributes = True` for ORM-backed responses.

Two schemas beyond the D.2 directive's named list (MemberTokenResponse,
MemberListResponse) were added because register/login/refresh need to
return tokens alongside member data, and chapter/search listing need
pagination — disclosed here and in PHASE_D2_IMPLEMENTATION.md rather than
silently bolted on.
"""
from datetime import date, datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ─── Requests ───────────────────────────────────────────────────────────────

class RegistrationRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=2, max_length=255)
    phone: Optional[str] = None
    state_of_origin_id: Optional[int] = None
    lga_of_origin_id: Optional[int] = None
    residence_country: Optional[str] = None
    chapter_id: Optional[UUID] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    residence_country: Optional[str] = Field(default=None, max_length=100)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(default=None, max_length=30)
    occupation: Optional[str] = Field(default=None, max_length=150)
    organisation: Optional[str] = Field(default=None, max_length=200)
    biography: Optional[str] = None
    skills: Optional[list] = None
    interests: Optional[list] = None
    languages: Optional[list] = None
    profile_photo_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    facebook_url: Optional[str] = None
    twitter_url: Optional[str] = None
    website: Optional[str] = None


# ─── Responses ──────────────────────────────────────────────────────────────

class ChapterResponse(BaseModel):
    id: UUID
    name: str
    country: str
    state_id: Optional[int] = None
    city: Optional[str] = None
    chapter_type: str
    status: str
    is_active: bool

    class Config:
        from_attributes = True


class MemberResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    state_of_origin_id: Optional[int] = None
    lga_of_origin_id: Optional[int] = None
    residence_country: Optional[str] = None
    chapter_id: Optional[UUID] = None
    membership_number: str
    membership_tier: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MemberListResponse(BaseModel):
    items: List[MemberResponse]
    total: int
    page: int
    page_size: int


class MemberTokenResponse(BaseModel):
    """Returned by /register, /login, and /refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    member: MemberResponse


class ProfileResponse(BaseModel):
    member_id: UUID
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    organisation: Optional[str] = None
    biography: Optional[str] = None
    skills: Optional[list] = None
    interests: Optional[list] = None
    languages: Optional[list] = None
    profile_photo_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    facebook_url: Optional[str] = None
    twitter_url: Optional[str] = None
    website: Optional[str] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class DashboardMemberSummary(BaseModel):
    id: str
    full_name: str
    membership_number: str
    membership_tier: str
    role: str
    is_verified: bool
    is_active: bool


class DashboardChapterInfo(BaseModel):
    id: str
    name: str
    country: str


class DashboardResponse(BaseModel):
    member_summary: DashboardMemberSummary
    chapter: Optional[DashboardChapterInfo] = None
    verification_status: str
    impact_score: Optional[float] = None  # placeholder — Impact Index is a later phase
    recent_activity: list = Field(default_factory=list)  # placeholder
