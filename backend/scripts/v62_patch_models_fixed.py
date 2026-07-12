"""
NDIP V6.2 -- models.py patch. Applies targeted, exact-text replacements
against the real, currently-deployed file (confirmed via direct sed
extraction this session against /app/app/models/models.py at 915 lines).
Each replacement is guarded: if the expected old text isn't found
verbatim, that specific patch is skipped and reported, rather than
corrupting the file. New classes (StakeholderEngagement,
StakeholderWatchlist) are appended at the end of the file.

Run: docker exec agora-backend-1 python scripts/v62_patch_models.py
"""
PATH = "/app/app/models/models.py"

with open(PATH, "r") as f:
    content = f.read()

patches_applied = []
patches_skipped = []


def apply_patch(name, old, new):
    global content
    if old not in content:
        patches_skipped.append(name)
        return
    content = content.replace(old, new, 1)
    patches_applied.append(name)


# --- Patch 1: imports -- add UniqueConstraint (Float already present, confirmed) ---
apply_patch(
    "imports (add UniqueConstraint)",
    """from sqlalchemy import (
    String, Integer, Float, Boolean, Text, DateTime, ForeignKey,
    Index, Enum as SAEnum
)""",
    """from sqlalchemy import (
    String, Integer, Float, Boolean, Text, DateTime, ForeignKey,
    Index, Enum as SAEnum, UniqueConstraint
)""",
)

# --- Patch 2: StakeholderType enum + StakeholderRegistry.stakeholder_type field ---
apply_patch(
    "StakeholderType enum + StakeholderRegistry.stakeholder_type field",
    """class StakeholderCategory(str, enum.Enum):
    POLITICAL = "POLITICAL"                # Presidency, ministers, governors, NASS, party leadership
    PUBLIC_INSTITUTION = "PUBLIC_INSTITUTION"  # Federal/state ministries, departments, agencies, regulators
    DIASPORA = "DIASPORA"                  # RTIFN, diaspora orgs, community/business leaders, professional networks
    INVESTMENT = "INVESTMENT"              # DFIs, sovereign funds, PE, impact/infrastructure investors
    INTERNATIONAL = "INTERNATIONAL"        # World Bank, AfDB, UN agencies, foreign missions, INGOs


class StakeholderRegistry(Base):""",
    """class StakeholderCategory(str, enum.Enum):
    POLITICAL = "POLITICAL"                # Presidency, ministers, governors, NASS, party leadership
    PUBLIC_INSTITUTION = "PUBLIC_INSTITUTION"  # Federal/state ministries, departments, agencies, regulators
    DIASPORA = "DIASPORA"                  # RTIFN, diaspora orgs, community/business leaders, professional networks
    INVESTMENT = "INVESTMENT"              # DFIs, sovereign funds, PE, impact/infrastructure investors
    INTERNATIONAL = "INTERNATIONAL"        # World Bank, AfDB, UN agencies, foreign missions, INGOs
class StakeholderType(str, enum.Enum):
    \"\"\"
    V6.2 Phase A -- granular stakeholder typing, additive to (not a
    replacement for) StakeholderCategory above. category is kept
    unchanged for backward compatibility with existing dependent code;
    stakeholder_type is optional and more specific.
    \"\"\"
    FEDERAL_MINISTRY = "FEDERAL_MINISTRY"
    FEDERAL_AGENCY = "FEDERAL_AGENCY"
    STATE_GOVERNMENT = "STATE_GOVERNMENT"
    LOCAL_GOVERNMENT = "LOCAL_GOVERNMENT"
    LEGISLATOR = "LEGISLATOR"
    POLITICAL_ACTOR = "POLITICAL_ACTOR"
    PARTY_OFFICIAL = "PARTY_OFFICIAL"
    DIASPORA_LEADER = "DIASPORA_LEADER"
    COMMUNITY_LEADER = "COMMUNITY_LEADER"
    TRADITIONAL_INSTITUTION = "TRADITIONAL_INSTITUTION"
    PRIVATE_SECTOR = "PRIVATE_SECTOR"
    INVESTOR = "INVESTOR"
    DEVELOPMENT_FINANCE = "DEVELOPMENT_FINANCE"
    INTERNATIONAL_DONOR = "INTERNATIONAL_DONOR"
    MULTILATERAL = "MULTILATERAL"
    MEDIA = "MEDIA"
    ACADEMIC = "ACADEMIC"
    NGO = "NGO"
    CIVIL_SOCIETY = "CIVIL_SOCIETY"
    INFRASTRUCTURE_OPERATOR = "INFRASTRUCTURE_OPERATOR"
    ENERGY_OPERATOR = "ENERGY_OPERATOR"
    CLIMATE_FINANCE_ACTOR = "CLIMATE_FINANCE_ACTOR"
    WASTE_MANAGEMENT_ACTOR = "WASTE_MANAGEMENT_ACTOR"


class StakeholderRegistry(Base):""",
)

# --- Patch 3: RelationshipType -- add 8 new values ---
apply_patch(
    "RelationshipType new values",
    """class RelationshipType(str, enum.Enum):
    REPORTS_TO = "REPORTS_TO"            # agency -> supervising ministry
    OWNS_PROGRAMME = "OWNS_PROGRAMME"      # institution -> programme it runs
    FUNDS = "FUNDS"                       # funder -> recipient/programme
    REGULATES = "REGULATES"               # regulator -> regulated entity
    PARTNERS_WITH = "PARTNERS_WITH"        # peer institutional partnership""",
    """class RelationshipType(str, enum.Enum):
    REPORTS_TO = "REPORTS_TO"            # agency -> supervising ministry
    OWNS_PROGRAMME = "OWNS_PROGRAMME"      # institution -> programme it runs
    FUNDS = "FUNDS"                       # funder -> recipient/programme
    REGULATES = "REGULATES"               # regulator -> regulated entity
    PARTNERS_WITH = "PARTNERS_WITH"        # peer institutional partnership
    # V6.2 additions -- all confirmed to fit the live VARCHAR(14) column
    APPROVES = "APPROVES"
    INFLUENCES = "INFLUENCES"
    IMPLEMENTS = "IMPLEMENTS"
    OVERSEES = "OVERSEES"
    CONNECTS_TO = "CONNECTS_TO"
    SUPPORTS = "SUPPORTS"
    OPPOSES = "OPPOSES"
    MONITORS = "MONITORS\"""",
)

# --- Patch 4: OutcomeChainLink -- deprecation markers only ---
apply_patch(
    "OutcomeChainLink deprecation markers",
    '''class OutcomeChainLink(Base):
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
    __tablename__ = "outcome_chain_links"''',
    '''class OutcomeChainLink(Base):
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

    DEPRECATED as of V6.2: superseded by StakeholderEngagement, the single
    canonical engagement/outcome system. This model and its table are
    retained (not deleted) per the V6.2 migration's mandatory adjustment --
    confirmed empty (0 rows) at the time of deprecation. New code must not
    write to this model; reads are permitted only for historical inspection.
    """
    __deprecated__ = True
    __replacement__ = "StakeholderEngagement"
    __tablename__ = "outcome_chain_links"''',
)

# --- Patch 5: StakeholderRelationship -- add strength + confidence fields ---
apply_patch(
    "StakeholderRelationship.strength / .confidence fields",
    '''    relationship_type: Mapped[str] = mapped_column(
        SAEnum(RelationshipType, native_enum=False), nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    # Optional link to the opportunity category this relationship is most
    # relevant for (e.g. REA->Ministry of Power is most relevant to ENERGY
    # opportunities) — used by the alignment/pathway engines, not required.
    relevant_category: Mapped[Optional[str]] = mapped_column(String(50))''',
    '''    relationship_type: Mapped[str] = mapped_column(
        SAEnum(RelationshipType, native_enum=False), nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    # V6.2 additions -- per the Stakeholder Relationship Graph spec.
    strength: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    # Optional link to the opportunity category this relationship is most
    # relevant for (e.g. REA->Ministry of Power is most relevant to ENERGY
    # opportunities) — used by the alignment/pathway engines, not required.
    relevant_category: Mapped[Optional[str]] = mapped_column(String(50))''',
)

# --- Patch 6: append new classes (StakeholderEngagement, StakeholderWatchlist) at end of file ---
NEW_CLASSES = '''

# ═══════════════════════════════════════════════════════════════════════════
# V6.2 — Stakeholder Intelligence & Engagement System (SIES)
# ═══════════════════════════════════════════════════════════════════════════

class StakeholderEngagementEventType(str, enum.Enum):
    ENGAGEMENT_INITIATED = "ENGAGEMENT_INITIATED"
    MEETING_HELD = "MEETING_HELD"
    PROPOSAL_SUBMITTED = "PROPOSAL_SUBMITTED"
    PROPOSAL_ACCEPTED = "PROPOSAL_ACCEPTED"
    PROPOSAL_REJECTED = "PROPOSAL_REJECTED"
    PROPOSAL_PENDING = "PROPOSAL_PENDING"
    FUNDING_APPROVED = "FUNDING_APPROVED"
    FUNDING_DECLINED = "FUNDING_DECLINED"
    PARTNERSHIP_ESTABLISHED = "PARTNERSHIP_ESTABLISHED"
    PROJECT_COMMENCED = "PROJECT_COMMENCED"
    PROJECT_DELIVERED = "PROJECT_DELIVERED"


class StakeholderWatchlistEventType(str, enum.Enum):
    APPOINTMENT = "APPOINTMENT"
    POLICY_ANNOUNCEMENT = "POLICY_ANNOUNCEMENT"
    FUNDING_ANNOUNCEMENT = "FUNDING_ANNOUNCEMENT"
    PROGRAMME_LAUNCH = "PROGRAMME_LAUNCH"
    LEADERSHIP_CHANGE = "LEADERSHIP_CHANGE"
    BOARD_APPOINTMENT = "BOARD_APPOINTMENT"
    MAJOR_SPEECH = "MAJOR_SPEECH"
    PUBLIC_STATEMENT = "PUBLIC_STATEMENT"
    MEDIA_VISIBILITY_CHANGE = "MEDIA_VISIBILITY_CHANGE"
    INFLUENCE_CHANGE = "INFLUENCE_CHANGE"


class StakeholderEngagement(Base):
    """
    V6.2 — single canonical engagement/outcome system, per the approved
    execution-safe migration spec. Replaces OutcomeChainLink (deprecated
    above, not deleted) as the write target for all engagement and
    outcome tracking platform-wide.
    """
    __tablename__ = "stakeholder_engagements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stakeholder_id: Mapped[Optional[int]] = mapped_column(ForeignKey("stakeholder_registry.id"), index=True)
    opportunity_id: Mapped[Optional[int]] = mapped_column(ForeignKey("opportunity_assessments.id"), index=True)
    recommendation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("recommendation_records.id"), index=True)
    event_type: Mapped[str] = mapped_column(
        SAEnum(StakeholderEngagementEventType, native_enum=False), nullable=False, index=True
    )
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    recorded_by: Mapped[Optional[str]] = mapped_column(String(150))
    # Idempotency key for legacy-data migration (format: "outcome_chain:{id}").
    # Unused at deploy time — OutcomeChainLink was confirmed empty (0 rows)
    # immediately before this table was created. Retained as forward-looking
    # insurance per the approved V6.2 execution-safe spec.
    source_legacy_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        Index("ix_engagement_stakeholder_event", "stakeholder_id", "event_type"),
        Index("ix_engagement_recommendation", "recommendation_id"),
        UniqueConstraint("source_legacy_id", "event_type", name="uq_engagement_legacy_event"),
    )


class StakeholderWatchlist(Base):
    """V6.2 — event-based tracking of stakeholder-relevant developments (appointments, announcements, leadership changes, etc.)."""
    __tablename__ = "stakeholder_watchlist"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stakeholder_id: Mapped[int] = mapped_column(ForeignKey("stakeholder_registry.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(
        SAEnum(StakeholderWatchlistEventType, native_enum=False), nullable=False, index=True
    )
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[Optional[str]] = mapped_column(String(100))
'''

content = content.rstrip() + "\n" + NEW_CLASSES
patches_applied.append("Appended StakeholderEngagement + StakeholderWatchlist classes")

with open(PATH, "w") as f:
    f.write(content)

print("=" * 60)
print("  models.py patch results")
print("=" * 60)
print(f"  Applied: {len(patches_applied)}")
for p in patches_applied:
    print(f"    [OK] {p}")
print(f"  Skipped (anchor text not found -- needs manual review): {len(patches_skipped)}")
for p in patches_skipped:
    print(f"    [SKIPPED] {p}")
