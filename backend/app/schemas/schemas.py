from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
import hashlib


# ─── Auth ─────────────────────────────────────────────────────────────────────

class AdminRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str

class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Participants ─────────────────────────────────────────────────────────────

class ParticipantCreate(BaseModel):
    email: EmailStr  # hashed before storage, never persisted
    country: Optional[str] = None
    city: Optional[str] = None
    profession: Optional[str] = None
    skills: Optional[str] = None
    interests: Optional[str] = None
    consent_given: bool = True

    def email_hash(self) -> str:
        return hashlib.sha256(self.email.lower().strip().encode()).hexdigest()

class ParticipantOut(BaseModel):
    id: int
    country: Optional[str]
    city: Optional[str]
    profession: Optional[str]
    skills: Optional[str]
    interests: Optional[str]
    consent_given: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ParticipantFilter(BaseModel):
    country: Optional[str] = None
    profession: Optional[str] = None
    skills: Optional[str] = None
    page: int = 1
    page_size: int = 50


# ─── Events ───────────────────────────────────────────────────────────────────

class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    event_type: str
    location: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    starts_at: datetime
    ends_at: Optional[datetime] = None
    capacity: Optional[int] = None
    is_online: bool = False

class EventOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    event_type: str
    location: Optional[str]
    country: Optional[str]
    city: Optional[str]
    starts_at: datetime
    ends_at: Optional[datetime]
    capacity: Optional[int]
    is_online: bool
    attendance_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True

class AttendEventRequest(BaseModel):
    event_id: int
    participant_id: int


# ─── Engagements ──────────────────────────────────────────────────────────────

class EngagementCreate(BaseModel):
    participant_id: Optional[int] = None
    engagement_type: str
    source: Optional[str] = None
    metadata_json: Optional[str] = None

class EngagementSummary(BaseModel):
    total_engagements: int
    by_type: dict
    period_days: int
    engagement_index: float
    growth_rate: float


# ─── Social ───────────────────────────────────────────────────────────────────

class SocialOverview(BaseModel):
    platform_counts: dict
    total_posts_analysed: int
    date_range_days: int

class SentimentOverview(BaseModel):
    overall_score: float
    positive_pct: float
    neutral_pct: float
    negative_pct: float
    by_platform: dict
    trend: list

class TopicOut(BaseModel):
    name: str
    mention_count: int
    momentum_score: Optional[float]
    platform: Optional[str]
    date_bucket: datetime

    class Config:
        from_attributes = True


# ─── Analytics ────────────────────────────────────────────────────────────────

class AnalyticsOverview(BaseModel):
    engagement_index: float
    participation_index: float
    growth_rate: float
    sentiment_score: float
    topic_momentum_score: float
    total_participants: int
    total_engagements: int
    new_participants_7d: int
    snapshot_date: datetime

class AnalyticsTrend(BaseModel):
    snapshots: list
    metric: str


# ─── Reports ──────────────────────────────────────────────────────────────────

class ReportGenerateRequest(BaseModel):
    period: str  # weekly | monthly | custom
    period_start: datetime
    period_end: datetime
    title: Optional[str] = None

class ReportOut(BaseModel):
    id: int
    title: str
    period: str
    period_start: datetime
    period_end: datetime
    content_json: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─── V6.0 Strategic Outcome Intelligence ───────────────────────────────────────

class StakeholderRegistryCreate(BaseModel):
    name: str
    short_name: Optional[str] = None
    category: str
    sector: Optional[str] = None
    role_description: Optional[str] = None
    aliases: Optional[List[str]] = None
    notes: Optional[str] = None

class OpportunityRegistryCreate(BaseModel):
    name: str
    category: str
    description: Optional[str] = None
    aliases: Optional[List[str]] = None

class OpportunityStatusUpdate(BaseModel):
    new_status: str
    description: str
    stakeholder_engaged: Optional[str] = None
    probability_of_success: Optional[float] = None
    next_milestone: Optional[str] = None

class OutcomeChainLinkCreate(BaseModel):
    recommendation_id: int
    opportunity_id: Optional[int] = None
    leadership_action: Optional[str] = None
    stakeholder_engagement: Optional[str] = None
    outcome: Optional[str] = None
    impact: Optional[str] = None


# --- V6.1 Stakeholder Influence & Opportunity Execution Intelligence ----------

class StakeholderRelationshipCreate(BaseModel):
    from_stakeholder_id: int
    to_stakeholder_id: int
    relationship_type: str
    description: Optional[str] = None
    relevant_category: Optional[str] = None

class StakeholderRegistryUpdate(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    category: Optional[str] = None
    sector: Optional[str] = None
    role_description: Optional[str] = None
    aliases: Optional[List[str]] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

class OpportunityRegistryUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    aliases: Optional[List[str]] = None
    is_active: Optional[bool] = None

