from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    String, Integer, Float, Boolean, Text, DateTime, ForeignKey,
    Index, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.database import Base


def utcnow():
    return datetime.now(timezone.utc)


# ─── Enums ────────────────────────────────────────────────────────────────────

class EngagementType(str, enum.Enum):
    registration = "registration"
    event_attendance = "event_attendance"
    newsletter = "newsletter"
    content_interaction = "content_interaction"
    survey_response = "survey_response"
    volunteer = "volunteer"


class SentimentLabel(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class ReportPeriod(str, enum.Enum):
    weekly = "weekly"
    monthly = "monthly"
    custom = "custom"


class SocialPlatform(str, enum.Enum):
    youtube = "youtube"
    twitter = "twitter"
    reddit = "reddit"
    meta = "meta"
    news = "news"
    gdelt = "gdelt"


# ─── Admin users (platform operators) ────────────────────────────────────────

class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ─── Participants (opt-in, GDPR-aware) ────────────────────────────────────────

class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # GDPR: email hashed for lookup, never stored plain
    email_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    country: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    profession: Mapped[Optional[str]] = mapped_column(String(150))
    skills: Mapped[Optional[str]] = mapped_column(Text)  # comma-separated
    interests: Mapped[Optional[str]] = mapped_column(Text)  # comma-separated
    consent_given: Mapped[bool] = mapped_column(Boolean, default=True)
    consent_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    attendances: Mapped[list["EventAttendance"]] = relationship(back_populates="participant")
    engagements: Mapped[list["Engagement"]] = relationship(back_populates="participant")

    __table_args__ = (
        Index("ix_participants_country", "country"),
        Index("ix_participants_profession", "profession"),
    )


# ─── Events ───────────────────────────────────────────────────────────────────

class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(String(100))
    location: Mapped[Optional[str]] = mapped_column(String(300))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    capacity: Mapped[Optional[int]] = mapped_column(Integer)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    attendances: Mapped[list["EventAttendance"]] = relationship(back_populates="event")

    __table_args__ = (
        Index("ix_events_starts_at", "starts_at"),
        Index("ix_events_country", "country"),
    )


class EventAttendance(Base):
    __tablename__ = "event_attendance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), nullable=False, index=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    attended: Mapped[bool] = mapped_column(Boolean, default=False)

    event: Mapped["Event"] = relationship(back_populates="attendances")
    participant: Mapped["Participant"] = relationship(back_populates="attendances")


# ─── Engagements (aggregated interaction events) ──────────────────────────────

class Engagement(Base):
    __tablename__ = "engagements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    participant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("participants.id"), index=True)
    engagement_type: Mapped[EngagementType] = mapped_column(SAEnum(EngagementType), nullable=False, index=True)
    source: Mapped[Optional[str]] = mapped_column(String(200))  # e.g. "newsletter-june"
    metadata_json: Mapped[Optional[str]] = mapped_column(Text)  # JSON blob, no PII
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    participant: Mapped[Optional["Participant"]] = relationship(back_populates="engagements")

    __table_args__ = (
        Index("ix_engagements_type_date", "engagement_type", "created_at"),
    )


# ─── Surveys ──────────────────────────────────────────────────────────────────

class Survey(Base):
    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closes_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    response_count: Mapped[int] = mapped_column(Integer, default=0)


# ─── Social posts (aggregated, no individual attribution) ─────────────────────

class SocialPost(Base):
    __tablename__ = "social_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    platform: Mapped[SocialPlatform] = mapped_column(SAEnum(SocialPlatform), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(200), nullable=False)
    # No author data stored — aggregated content only
    content_text: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(String(500))
    language: Mapped[Optional[str]] = mapped_column(String(10))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    query_tag: Mapped[Optional[str]] = mapped_column(String(200))

    sentiment: Mapped[Optional["SentimentRecord"]] = relationship(back_populates="post", uselist=False)

    __table_args__ = (
        Index("ix_social_posts_platform_date", "platform", "published_at"),
        Index("ix_social_posts_external", "platform", "external_id", unique=True),
    )


class SocialMetric(Base):
    """Aggregated daily metrics per platform — no individual data."""
    __tablename__ = "social_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    platform: Mapped[SocialPlatform] = mapped_column(SAEnum(SocialPlatform), nullable=False)
    metric_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    query_tag: Mapped[Optional[str]] = mapped_column(String(200))
    post_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_sentiment: Mapped[Optional[float]] = mapped_column(Float)
    positive_pct: Mapped[Optional[float]] = mapped_column(Float)
    neutral_pct: Mapped[Optional[float]] = mapped_column(Float)
    negative_pct: Mapped[Optional[float]] = mapped_column(Float)
    top_topics: Mapped[Optional[str]] = mapped_column(Text)  # JSON list
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_social_metrics_platform_date", "platform", "metric_date"),
    )


# ─── Sentiment records ────────────────────────────────────────────────────────

class SentimentRecord(Base):
    __tablename__ = "sentiment_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    post_id: Mapped[Optional[int]] = mapped_column(ForeignKey("social_posts.id"), index=True)
    label: Mapped[SentimentLabel] = mapped_column(SAEnum(SentimentLabel), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)  # -1.0 to 1.0
    model_used: Mapped[str] = mapped_column(String(100), default="textblob")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    post: Mapped[Optional["SocialPost"]] = relationship(back_populates="sentiment")


# ─── Topics ───────────────────────────────────────────────────────────────────

class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    platform: Mapped[Optional[SocialPlatform]] = mapped_column(SAEnum(SocialPlatform))
    mention_count: Mapped[int] = mapped_column(Integer, default=0)
    date_bucket: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    momentum_score: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_topics_name_date", "name", "date_bucket"),
    )


# ─── Analytics snapshots ──────────────────────────────────────────────────────

class AnalyticsSnapshot(Base):
    """Historical storage of all computed metrics."""
    __tablename__ = "analytics_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    engagement_index: Mapped[Optional[float]] = mapped_column(Float)
    participation_index: Mapped[Optional[float]] = mapped_column(Float)
    growth_rate: Mapped[Optional[float]] = mapped_column(Float)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float)
    topic_momentum_score: Mapped[Optional[float]] = mapped_column(Float)
    total_participants: Mapped[int] = mapped_column(Integer, default=0)
    total_engagements: Mapped[int] = mapped_column(Integer, default=0)
    new_participants: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ─── Reports ──────────────────────────────────────────────────────────────────

class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    period: Mapped[ReportPeriod] = mapped_column(SAEnum(ReportPeriod), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)  # full report data
    generated_by: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    __table_args__ = (
        Index("ix_reports_period_date", "period", "created_at"),
    )


# ─── Normalised post (unified schema across all sources) ──────────────────────

class NormalisedPost(Base):
    """
    Unified schema for all ingested content.
    Raw payload stored separately in social_posts.
    This table drives all NLP and analytics.
    """
    __tablename__ = "normalised_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_post_id: Mapped[Optional[int]] = mapped_column(ForeignKey("social_posts.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(300), nullable=False)
    text: Mapped[Optional[str]] = mapped_column(Text)
    language: Mapped[Optional[str]] = mapped_column(String(10))
    geo_country: Mapped[Optional[str]] = mapped_column(String(100))
    geo_region: Mapped[Optional[str]] = mapped_column(String(200))
    url: Mapped[Optional[str]] = mapped_column(String(500))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    query_tag: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    # NLP outputs
    sentiment_label: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float)
    entities_json: Mapped[Optional[str]] = mapped_column(Text)   # JSON list of {text, label}
    topics_json: Mapped[Optional[str]] = mapped_column(Text)     # JSON list of topic strings
    narrative_tags: Mapped[Optional[str]] = mapped_column(Text)  # JSON list
    nlp_processed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    nlp_processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_norm_platform_date", "source_platform", "published_at"),
        Index("ix_norm_sentiment_date", "sentiment_label", "published_at"),
        Index("ix_norm_query_date", "query_tag", "published_at"),
    )


# ─── Named entities ───────────────────────────────────────────────────────────

class NamedEntity(Base):
    __tablename__ = "named_entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("normalised_posts.id"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # PERSON, ORG, GPE, etc.
    platform: Mapped[Optional[str]] = mapped_column(String(50))
    date_bucket: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_entity_text_label", "text", "label"),
        Index("ix_entity_date", "date_bucket"),
    )


# ─── Narrative trends ─────────────────────────────────────────────────────────

class NarrativeTrend(Base):
    __tablename__ = "narrative_trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    narrative: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    platform: Mapped[Optional[str]] = mapped_column(String(50))
    mention_count: Mapped[int] = mapped_column(Integer, default=0)
    sentiment_avg: Mapped[Optional[float]] = mapped_column(Float)
    velocity: Mapped[Optional[float]] = mapped_column(Float)   # % change vs previous period
    date_bucket: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    query_tag: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_narrative_date", "narrative", "date_bucket"),
    )


# ─── Connector health log ─────────────────────────────────────────────────────

class ConnectorHealthLog(Base):
    __tablename__ = "connector_health_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # ok | error | rate_limited | unconfigured
    records_fetched: Mapped[int] = mapped_column(Integer, default=0)
    records_new: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    __table_args__ = (
        Index("ix_connector_health_platform_date", "platform", "checked_at"),
    )


# ─── Ingestion jobs ───────────────────────────────────────────────────────────

class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    platforms: Mapped[Optional[str]] = mapped_column(String(200))  # comma-separated
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    total_fetched: Mapped[int] = mapped_column(Integer, default=0)
    total_new: Mapped[int] = mapped_column(Integer, default=0)
    total_normalised: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    triggered_by: Mapped[Optional[str]] = mapped_column(String(100))


# ─── Decision Support — Recommendation Tracking (V5.6) ───────────────────────

class RecommendationStatus(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    VALIDATED = "VALIDATED"
    PARTIALLY_VALIDATED = "PARTIALLY_VALIDATED"
    INVALIDATED = "INVALIDATED"


class RecommendationRecord(Base):
    """
    NDIP V5.6 Decision Quality Framework.
    Tracks every recommendation generated by the Decision Support Engine,
    enabling automated effectiveness evaluation and a learning feedback loop.
    """
    __tablename__ = "recommendation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    module: Mapped[Optional[str]] = mapped_column(String(50), index=True, default="decision_support")
    narrative: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    recommendation_text: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation_category: Mapped[str] = mapped_column(String(30), index=True)  # ACT/PREPARE/MONITOR/ESCALATE/INVESTIGATE/ENGAGE
    priority: Mapped[str] = mapped_column(String(20), default="Medium")
    confidence: Mapped[str] = mapped_column(String(20), default="Medium")
    time_horizon: Mapped[Optional[str]] = mapped_column(String(50))

    supporting_evidence: Mapped[Optional[str]] = mapped_column(Text)
    expected_outcome: Mapped[Optional[str]] = mapped_column(Text)

    # Snapshot of the metric that triggered this recommendation, for later comparison
    trigger_metric_name: Mapped[Optional[str]] = mapped_column(String(100))   # e.g. "share_of_voice", "momentum"
    trigger_metric_value: Mapped[Optional[float]] = mapped_column(Float)

    status: Mapped[str] = mapped_column(
        SAEnum(RecommendationStatus, native_enum=False),
        default=RecommendationStatus.OPEN,
        index=True,
    )

    evaluation_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    outcome_score: Mapped[Optional[int]] = mapped_column(Integer)   # 0/25/50/75/100
    outcome_notes: Mapped[Optional[str]] = mapped_column(Text)
    outcome_metric_value: Mapped[Optional[float]] = mapped_column(Float)  # actual value observed at evaluation time

    period_days: Mapped[int] = mapped_column(Integer, default=7)

    __table_args__ = (
        Index("ix_recommendation_status_created", "status", "created_at"),
        Index("ix_recommendation_narrative_created", "narrative", "created_at"),
    )


# ─── V6.0 Strategic Outcome Intelligence ───────────────────────────────────────
# Design principle (per platform owner instruction): NO stakeholder or
# opportunity taxonomy is hard-coded into business logic. Everything below is
# a REGISTRY — seeded with an initial baseline list via a seed script, but
# readable/writable at runtime with no code changes required to add a new
# institution, programme category, or opportunity type. All V6.0 classification,
# scoring, and intelligence functions read from these tables rather than from
# fixed keyword dicts (contrast with V5.7's ELECTION_SUBCATEGORIES, which is
# intentionally NOT the pattern followed here).

class StakeholderCategory(str, enum.Enum):
    POLITICAL = "POLITICAL"                # Presidency, ministers, governors, NASS, party leadership
    PUBLIC_INSTITUTION = "PUBLIC_INSTITUTION"  # Federal/state ministries, departments, agencies, regulators
    DIASPORA = "DIASPORA"                  # RTIFN, diaspora orgs, community/business leaders, professional networks
    INVESTMENT = "INVESTMENT"              # DFIs, sovereign funds, PE, impact/infrastructure investors
    INTERNATIONAL = "INTERNATIONAL"        # World Bank, AfDB, UN agencies, foreign missions, INGOs


class StakeholderRegistry(Base):
    """
    V6.0 Phase C/D — the canonical, expandable list of named stakeholders
    (institutions and roles) NDIP tracks. Seeded with a baseline list; new
    rows can be added at any time (via admin/config, not a code change) to
    extend coverage beyond the initial energy/infrastructure/diaspora/Nigeria
    scope without redeployment.
    """
    __tablename__ = "stakeholder_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    short_name: Mapped[Optional[str]] = mapped_column(String(50))   # e.g. "REA", "NSIA"
    category: Mapped[str] = mapped_column(
        SAEnum(StakeholderCategory, native_enum=False), index=True, nullable=False
    )
    sector: Mapped[Optional[str]] = mapped_column(String(100))      # e.g. "Energy", "Climate", "Diaspora"
    role_description: Mapped[Optional[str]] = mapped_column(Text)
    # Aliases/keywords used to match this stakeholder in discourse text —
    # itself stored as data, not hard-coded, so it's editable without a
    # deployment. Stored as a JSON list of strings.
    aliases_json: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("ix_stakeholder_category_active", "category", "is_active"),
    )


class StakeholderProfile(Base):
    """
    V6.0 Phase D — computed, time-stamped scoring snapshot for a stakeholder.
    A new row is written each time scores are recomputed (rather than
    updating one row in place), so trend/momentum can be derived from
    history — same pattern as AnalyticsSnapshot elsewhere in this schema.
    """
    __tablename__ = "stakeholder_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stakeholder_id: Mapped[int] = mapped_column(ForeignKey("stakeholder_registry.id"), nullable=False, index=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    period_days: Mapped[int] = mapped_column(Integer, default=30)

    influence_score: Mapped[float] = mapped_column(Float, default=0.0)
    visibility_score: Mapped[float] = mapped_column(Float, default=0.0)
    engagement_score: Mapped[float] = mapped_column(Float, default=0.0)
    opportunity_alignment_score: Mapped[float] = mapped_column(Float, default=0.0)
    strategic_relevance_score: Mapped[float] = mapped_column(Float, default=0.0)

    mention_count: Mapped[int] = mapped_column(Integer, default=0)
    associated_narratives_json: Mapped[Optional[str]] = mapped_column(Text)   # JSON list
    associated_opportunities_json: Mapped[Optional[str]] = mapped_column(Text)  # JSON list of opportunity_registry ids
    recent_activity_summary: Mapped[Optional[str]] = mapped_column(Text)
    monitoring_priority: Mapped[str] = mapped_column(String(20), default="Medium")  # Low/Medium/High/Critical

    __table_args__ = (
        Index("ix_stakeholder_profile_computed", "stakeholder_id", "computed_at"),
    )


class OpportunityCategory(str, enum.Enum):
    INFRASTRUCTURE = "INFRASTRUCTURE"
    ENERGY = "ENERGY"
    WASTE_TO_ENERGY = "WASTE_TO_ENERGY"
    CLIMATE_FINANCE = "CLIMATE_FINANCE"
    CARBON_MARKETS = "CARBON_MARKETS"
    DIASPORA_INVESTMENT = "DIASPORA_INVESTMENT"
    PPP = "PPP"
    FEDERAL_PROGRAMMES = "FEDERAL_PROGRAMMES"
    STATE_PROGRAMMES = "STATE_PROGRAMMES"
    DEVELOPMENT_FINANCE = "DEVELOPMENT_FINANCE"
    INTERNATIONAL_DONOR = "INTERNATIONAL_DONOR"
    INNOVATION_ENTREPRENEURSHIP = "INNOVATION_ENTREPRENEURSHIP"
    TRADE_INVESTMENT = "TRADE_INVESTMENT"
    INDUSTRIAL_DEVELOPMENT = "INDUSTRIAL_DEVELOPMENT"
    # V6.1 Phase L additions — distinct from the broader ENERGY/INFRASTRUCTURE
    # buckets above because the spec asks to track these as their own
    # strategic lens (Waste, Energy & Climate Intelligence), not merged in.
    WASTE_MANAGEMENT = "WASTE_MANAGEMENT"
    RENEWABLE_ENERGY = "RENEWABLE_ENERGY"
    RURAL_ELECTRIFICATION = "RURAL_ELECTRIFICATION"
    ENERGY_ACCESS = "ENERGY_ACCESS"
    GREEN_INVESTMENT = "GREEN_INVESTMENT"


# V6.1 Phase L — the strategic category cluster this release tracks as a
# dedicated lens. Defined once here (data, not scattered hard-coded lists)
# so the reporting service and any future route/UI reads from a single
# source of truth.
WASTE_ENERGY_CLIMATE_CATEGORIES = [
    OpportunityCategory.WASTE_MANAGEMENT,
    OpportunityCategory.WASTE_TO_ENERGY,
    OpportunityCategory.CLIMATE_FINANCE,
    OpportunityCategory.RENEWABLE_ENERGY,
    OpportunityCategory.RURAL_ELECTRIFICATION,
    OpportunityCategory.ENERGY_ACCESS,
    OpportunityCategory.CARBON_MARKETS,
    OpportunityCategory.INFRASTRUCTURE,
    OpportunityCategory.GREEN_INVESTMENT,
]


class OpportunityRegistry(Base):
    """
    V6.0 Phase A — the canonical, expandable list of opportunity programme
    types NDIP watches for (e.g. "Mini-grid programmes", "Diaspora bonds").
    Same registry pattern as StakeholderRegistry: seeded, then editable
    without a code change.
    """
    __tablename__ = "opportunity_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category: Mapped[str] = mapped_column(
        SAEnum(OpportunityCategory, native_enum=False), index=True, nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    aliases_json: Mapped[Optional[str]] = mapped_column(Text)   # JSON list of keywords/phrases
    typical_lead_stakeholder_ids_json: Mapped[Optional[str]] = mapped_column(Text)  # JSON list of stakeholder_registry ids
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_opportunity_category_active", "category", "is_active"),
    )


class OpportunityPipelineStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    ASSESSED = "ASSESSED"
    ENGAGED = "ENGAGED"
    IN_PROGRESS = "IN_PROGRESS"
    ADVANCED = "ADVANCED"
    SECURED = "SECURED"
    CLOSED = "CLOSED"
    EXPIRED = "EXPIRED"


class OpportunityAssessment(Base):
    """
    V6.0 Phase A/B/F — a single, concrete opportunity instance detected in
    discourse, with its full assessment (why it matters, strategic value,
    stakeholders, recommended engagement) and current pipeline lifecycle
    status. This is the flagship V6.0 record type.
    """
    __tablename__ = "opportunity_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    opportunity_registry_id: Mapped[Optional[int]] = mapped_column(ForeignKey("opportunity_registry.id"), index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(
        SAEnum(OpportunityCategory, native_enum=False), index=True, nullable=False
    )

    what_opportunity_exists: Mapped[str] = mapped_column(Text, nullable=False)
    why_it_matters: Mapped[Optional[str]] = mapped_column(Text)
    strategic_value: Mapped[str] = mapped_column(String(20), default="Medium")  # Low/Medium/High/Critical

    # Stakeholders — stored as JSON list of {stakeholder_id, name, role} so the
    # assessment is self-contained even if a registry entry later changes.
    stakeholders_json: Mapped[Optional[str]] = mapped_column(Text)
    recommended_engagement: Mapped[Optional[str]] = mapped_column(Text)
    recommended_stakeholders_first_json: Mapped[Optional[str]] = mapped_column(Text)  # ranked JSON list

    expected_outcome: Mapped[Optional[str]] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(20), default="Medium")

    # Evidence linking this assessment back to the discourse that triggered it.
    source_narrative: Mapped[Optional[str]] = mapped_column(String(100))
    evidence_post_count: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(
        SAEnum(OpportunityPipelineStatus, native_enum=False),
        default=OpportunityPipelineStatus.DETECTED, index=True,
    )
    probability_of_success: Mapped[Optional[float]] = mapped_column(Float)  # 0.0-1.0
    next_milestone: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("ix_opportunity_status_created", "status", "created_at"),
        Index("ix_opportunity_category_status", "category", "status"),
    )


class OpportunityPipelineEvent(Base):
    """
    V6.0 Phase F — append-only lifecycle log for an OpportunityAssessment.
    Every status change, engagement action, or milestone update is recorded
    here, so the pipeline tracker has a full audit trail (who engaged, when,
    what happened, what's next) rather than only the current snapshot.
    """
    __tablename__ = "opportunity_pipeline_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunity_assessments.id"), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # status_change/engagement/milestone/note
    from_status: Mapped[Optional[str]] = mapped_column(String(20))
    to_status: Mapped[Optional[str]] = mapped_column(String(20))
    stakeholder_engaged: Mapped[Optional[str]] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_by: Mapped[Optional[str]] = mapped_column(String(100))  # admin user email, if manually logged

    __table_args__ = (
        Index("ix_pipeline_event_opportunity_time", "opportunity_id", "occurred_at"),
    )


class OutcomeChainLink(Base):
    """
    V6.0 Phase E — extends the existing RecommendationRecord evaluation loop
    (Recommendation -> Evaluation) with the fuller chain the platform owner
    specified: Recommendation -> Leadership Action -> Stakeholder Engagement
    -> Outcome -> Impact. This is intentionally a SEPARATE, linked table
    rather than new columns bolted onto RecommendationRecord, so V5.6-V5.9's
    existing evaluation logic (record_recommendation, run_evaluation_cycle,
    compute_decision_quality_metrics) continues to work completely unchanged
    on RecommendationRecord alone. A RecommendationRecord with no
    OutcomeChainLink rows is simply a recommendation that hasn't had a
    leadership action logged against it yet — not an error state.
    """
    __tablename__ = "outcome_chain_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recommendation_id: Mapped[int] = mapped_column(ForeignKey("recommendation_records.id"), nullable=False, index=True)
    opportunity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("opportunity_assessments.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    leadership_action: Mapped[Optional[str]] = mapped_column(Text)
    leadership_action_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    stakeholder_engagement: Mapped[Optional[str]] = mapped_column(Text)
    stakeholder_engagement_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    outcome: Mapped[Optional[str]] = mapped_column(Text)
    outcome_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    impact: Mapped[Optional[str]] = mapped_column(Text)
    impact_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    recorded_by: Mapped[Optional[str]] = mapped_column(String(100))

    __table_args__ = (
        Index("ix_outcome_chain_recommendation", "recommendation_id"),
    )


# ─── V6.1 Stakeholder Influence & Opportunity Execution Intelligence ─────────
# Same registry-driven design principle as V6.0: relationships are DATA in a
# table, seeded with a known baseline, expandable without code changes —
# not a hard-coded institutional org chart in business logic.

class RelationshipType(str, enum.Enum):
    REPORTS_TO = "REPORTS_TO"            # agency -> supervising ministry
    OWNS_PROGRAMME = "OWNS_PROGRAMME"      # institution -> programme it runs
    FUNDS = "FUNDS"                       # funder -> recipient/programme
    REGULATES = "REGULATES"               # regulator -> regulated entity
    PARTNERS_WITH = "PARTNERS_WITH"        # peer institutional partnership


class StakeholderInfluenceLevel(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class StakeholderRelationship(Base):
    """
    V6.1 Phase B — Stakeholder Network Mapping. A directed edge between two
    StakeholderRegistry entries (e.g. Rural Electrification Agency REPORTS_TO
    Federal Ministry of Power). Seeded with a known baseline of real
    institutional relationships; expandable via the same registry-management
    routes/UI as stakeholders and opportunities themselves (Phase K) — no
    code change required to add a new relationship.
    """
    __tablename__ = "stakeholder_relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    from_stakeholder_id: Mapped[int] = mapped_column(ForeignKey("stakeholder_registry.id"), nullable=False, index=True)
    to_stakeholder_id: Mapped[int] = mapped_column(ForeignKey("stakeholder_registry.id"), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(
        SAEnum(RelationshipType, native_enum=False), nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    # Optional link to the opportunity category this relationship is most
    # relevant for (e.g. REA->Ministry of Power is most relevant to ENERGY
    # opportunities) — used by the alignment/pathway engines, not required.
    relevant_category: Mapped[Optional[str]] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_relationship_from_type", "from_stakeholder_id", "relationship_type"),
        Index("ix_relationship_to_type", "to_stakeholder_id", "relationship_type"),
    )


class StakeholderInfluenceProfile(Base):
    """
    V6.1 Phase A — Stakeholder Influence Analysis. A richer, time-stamped
    scoring snapshot than V6.0's StakeholderProfile (which this extends
    rather than replaces — V6.0's profile remains the source for raw
    mention/visibility/engagement numbers; this table adds the V6.1-specific
    composite scores derived from those plus network and narrative data).
    """
    __tablename__ = "stakeholder_influence_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stakeholder_id: Mapped[int] = mapped_column(ForeignKey("stakeholder_registry.id"), nullable=False, index=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    period_days: Mapped[int] = mapped_column(Integer, default=30)

    influence_score: Mapped[float] = mapped_column(Float, default=0.0)
    momentum_score: Mapped[float] = mapped_column(Float, default=0.0)
    narrative_impact_score: Mapped[float] = mapped_column(Float, default=0.0)
    opportunity_relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    engagement_priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    relationship_strength_score: Mapped[float] = mapped_column(Float, default=0.0)

    composite_index: Mapped[float] = mapped_column(Float, default=0.0)
    influence_level: Mapped[str] = mapped_column(
        SAEnum(StakeholderInfluenceLevel, native_enum=False), default=StakeholderInfluenceLevel.LOW
    )

    __table_args__ = (
        Index("ix_influence_profile_stakeholder_time", "stakeholder_id", "computed_at"),
    )


class StakeholderMomentumSnapshot(Base):
    """
    V6.1 Phase G — Stakeholder Momentum Tracker. Append-only time series
    (separate from StakeholderInfluenceProfile so momentum direction can be
    derived from real history — comparing consecutive snapshots — rather
    than estimated from a single period like V6.0's "Stakeholder Influence
    Shifts" proxy, which the V6.0 audit flagged as a known limitation).
    """
    __tablename__ = "stakeholder_momentum_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stakeholder_id: Mapped[int] = mapped_column(ForeignKey("stakeholder_registry.id"), nullable=False, index=True)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    mention_count: Mapped[int] = mapped_column(Integer, default=0)
    narrative_visibility: Mapped[float] = mapped_column(Float, default=0.0)
    opportunity_relevance: Mapped[float] = mapped_column(Float, default=0.0)
    policy_visibility: Mapped[float] = mapped_column(Float, default=0.0)

    momentum_label: Mapped[str] = mapped_column(String(20), default="Stable")  # Rising/Stable/Declining/Accelerating

    __table_args__ = (
        Index("ix_momentum_stakeholder_time", "stakeholder_id", "snapshot_at"),
    )


class OpportunityAlignmentScore(Base):
    """
    V6.1 Phase D — Opportunity Alignment Engine. Replaces V6.0's placeholder
    opportunity_alignment_score (always 0.0, flagged as a known limitation
    in the V6.0 audit) with a genuine multi-factor score, computed and
    stored per opportunity-stakeholder pair so the full breakdown (not just
    the final number) is auditable.
    """
    __tablename__ = "opportunity_alignment_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunity_assessments.id"), nullable=False, index=True)
    stakeholder_id: Mapped[int] = mapped_column(ForeignKey("stakeholder_registry.id"), nullable=False, index=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    stakeholder_relevance: Mapped[float] = mapped_column(Float, default=0.0)
    narrative_alignment: Mapped[float] = mapped_column(Float, default=0.0)
    policy_alignment: Mapped[float] = mapped_column(Float, default=0.0)
    sector_alignment: Mapped[float] = mapped_column(Float, default=0.0)
    historical_engagement_relevance: Mapped[float] = mapped_column(Float, default=0.0)

    alignment_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    classification: Mapped[str] = mapped_column(String(20), default="Weak")  # Weak/Moderate/Strong/Strategic

    __table_args__ = (
        Index("ix_alignment_opportunity_stakeholder", "opportunity_id", "stakeholder_id"),
    )


class OpportunityReadinessAssessment(Base):
    """V6.1 Phase E — Opportunity Readiness Index."""
    __tablename__ = "opportunity_readiness_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunity_assessments.id"), nullable=False, index=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    stakeholder_readiness: Mapped[float] = mapped_column(Float, default=0.0)
    policy_environment: Mapped[float] = mapped_column(Float, default=0.0)
    narrative_momentum: Mapped[float] = mapped_column(Float, default=0.0)
    public_sentiment: Mapped[float] = mapped_column(Float, default=0.0)
    funding_environment: Mapped[float] = mapped_column(Float, default=0.0)
    implementation_complexity: Mapped[float] = mapped_column(Float, default=0.0)  # higher = MORE complex (penalises readiness)

    readiness_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    readiness_label: Mapped[str] = mapped_column(String(30), default="Not Ready")
    # Not Ready / Emerging / Developing / Ready / Strategic Window

    __table_args__ = (
        Index("ix_readiness_opportunity_time", "opportunity_id", "computed_at"),
    )


class EngagementPathway(Base):
    """
    V6.1 Phase F — Engagement Pathway Engine. The generated, ordered
    engagement plan for a single opportunity. Steps are stored as a related
    table (EngagementStep) rather than JSON so each step can later be
    individually marked complete/in-progress as real engagement unfolds —
    consistent with the V6.0 OpportunityPipelineEvent audit-trail pattern.
    """
    __tablename__ = "engagement_pathways"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunity_assessments.id"), nullable=False, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)  # superseded pathways kept for history, not deleted

    __table_args__ = (
        Index("ix_pathway_opportunity_current", "opportunity_id", "is_current"),
    )


class EngagementStep(Base):
    """A single ordered step within an EngagementPathway."""
    __tablename__ = "engagement_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pathway_id: Mapped[int] = mapped_column(ForeignKey("engagement_pathways.id"), nullable=False, index=True)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    stakeholder_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stakeholder_registry.id"))
    status: Mapped[str] = mapped_column(String(20), default="Pending")  # Pending/In Progress/Complete/Skipped
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_step_pathway_number", "pathway_id", "step_number"),
    )
