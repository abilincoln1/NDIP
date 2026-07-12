"""
NDIP V6.1.4 -- Executive Decision Engine (EDE)

The single, authoritative recommendation-CONSTRUCTION service for NDIP.

DESIGN NOTE on scope (grounded in the live audit that preceded this
build): the thing that was genuinely duplicated across Decision Support,
National Pulse Executive, and Election Intelligence was not each
module's narrative-trigger DETECTION logic (e.g. "governance momentum
>200 and rising" vs "days_to_election > 180") -- that logic is
legitimately different per module's domain and is preserved unchanged
in each module. What was duplicated was the CONSTRUCTION of the
recommendation dict itself: hand-assembling category/priority/action/
reasoning fields, and -- critically -- each module either omitted or
inconsistently attached responsible_stakeholders, time_horizon, and
confidence (V6.1.3's stakeholder enrichment only ever reached Decision
Support's output, never National Pulse Executive's or Election
Intelligence's).

This module is therefore a shared BUILDER, not a shared narrative-rules
engine. Each calling module still decides WHEN to recommend something
and WHAT the action text says (their domain expertise, unchanged); this
module is the one place responsible for turning that into the standard,
fully-enriched recommendation object, including stakeholder resolution
via the real StakeholderRegistry/sector mapping built in V6.1.3.
"""
import sys
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session


# Narrative -> sector mapping, identical to the one built and verified
# live in V6.1.3's decision_support.py enrichment step. Centralised here
# now so all three calling modules share exactly one mapping, rather than
# each module potentially drifting to its own version.
NARRATIVE_SECTOR_MAP = {
    "governance": "Executive",
    "economy": "Finance",
    "global nigerian engagement": "Diaspora",
    "diaspora": "Diaspora",
    "elections": "Legislature",
    "electoral": "Legislature",
    "energy": "Energy",
    "infrastructure": "Infrastructure",
    "climate": "Climate",
    "investment": "Investment",
    "trade": "Trade",
}


def resolve_responsible_stakeholders(db: Session, issue_text: str, limit: int = 3) -> list:
    """
    Looks up real stakeholders from StakeholderRegistry by matching the
    recommendation's issue text against known narrative keywords, mapped
    to real sector values (confirmed live in V6.1.3 -- not invented).
    Prefers named office-holders (stakeholder_type set) over plain
    institutions where both exist in the same sector, per the platform's
    explicit anti-anonymity rule. Returns an empty list -- not a
    fabricated name -- when no sector match exists, per V6.1.4 Phase F's
    explicit instruction to state insufficient evidence rather than
    invent stakeholders.
    """
    from app.models.models import StakeholderRegistry

    issue_lower = (issue_text or "").lower()
    sector = None
    for keyword, mapped_sector in NARRATIVE_SECTOR_MAP.items():
        if keyword in issue_lower:
            sector = mapped_sector
            break
    if not sector:
        return []
    try:
        rows = db.query(StakeholderRegistry).filter(
            StakeholderRegistry.sector == sector,
            StakeholderRegistry.is_active == True,
        ).all()
    except Exception:
        return []
    named = [r for r in rows if r.stakeholder_type is not None]
    institutional = [r for r in rows if r.stakeholder_type is None]
    ordered = named + institutional
    return [r.name for r in ordered[:limit]]


def resolve_opportunity_context(db: Session, issue_text: str) -> Optional[dict]:
    """
    Phase G -- where a tracked OpportunityAssessment's category plausibly
    matches the recommendation's topic, attach its strategic value and
    title. Best-effort: returns None (not a fabricated link) if no
    category match exists.
    """
    from app.models.models import OpportunityAssessment

    issue_lower = (issue_text or "").lower()
    topic_to_category_keyword = {
        "energy": "ENERGY", "infrastructure": "INFRASTRUCTURE", "climate": "CLIMATE_FINANCE",
        "waste": "WASTE_TO_ENERGY", "diaspora": "DIASPORA_INVESTMENT", "ppp": "PPP",
    }
    matched_category = None
    for keyword, category in topic_to_category_keyword.items():
        if keyword in issue_lower:
            matched_category = category
            break
    if not matched_category:
        return None
    try:
        opp = db.query(OpportunityAssessment).filter(
            OpportunityAssessment.category == matched_category
        ).order_by(OpportunityAssessment.id.desc()).first()
    except Exception:
        return None
    if not opp:
        return None
    return {"opportunity": opp.title, "strategic_value": opp.strategic_value}


CONFIDENCE_MAP = {"Critical": "High", "High": "High", "Medium": "Medium", "Low": "Low"}


def build_recommendation(
    db: Session,
    *,
    category: str,
    priority: str,
    issue: str,
    action: str,
    reasoning: str,
    expected_outcome: str,
    evidence: str,
    time_horizon: str,
    monitoring_requirements: Optional[list] = None,
    confidence: Optional[str] = None,
) -> dict:
    """
    Phase A/C -- the single, authoritative recommendation-construction
    function. Every calling module (Decision Support, National Pulse
    Executive, Election Intelligence) supplies its own domain-specific
    trigger evaluation and text; this function is responsible for
    producing the standard, fully-enriched output structure every time,
    so no module can return a partial structure (Phase C's explicit
    requirement).
    """
    responsible_stakeholders = resolve_responsible_stakeholders(db, issue)
    opportunity_context = resolve_opportunity_context(db, issue)

    resolved_confidence = confidence or CONFIDENCE_MAP.get(priority, "Medium")

    supporting_evidence = [evidence] if isinstance(evidence, str) else list(evidence or [])

    recommendation = {
        "category": category,
        "priority": priority,
        "action": action,
        "reasoning": reasoning,
        "responsible_stakeholders": responsible_stakeholders,
        "supporting_evidence": supporting_evidence,
        "expected_outcome": expected_outcome,
        "time_horizon": time_horizon,
        "confidence": resolved_confidence,
        "monitoring_requirements": monitoring_requirements or [],
        "generated_by": "Executive Decision Engine",
        # Preserved for backward compatibility with existing consumers
        # (Decision Support's existing fields, used by Leadership Pack /
        # Situation Room / the recommendation tracker) -- not removed,
        # per "preserve existing functionality."
        "issue": issue,
        "evidence": evidence,
    }
    if opportunity_context:
        recommendation["opportunity_alignment"] = opportunity_context

    return recommendation


if __name__ == "__main__":
    # Live self-test: confirm the engine produces a fully-populated
    # recommendation against the real database, for at least one
    # genuinely sector-matched and one genuinely unmatched case.
    sys.path.insert(0, '/app')
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        print("=" * 70)
        print("  Executive Decision Engine -- live self-test")
        print("=" * 70)
        rec1 = build_recommendation(
            db,
            category="ENGAGE", priority="High",
            issue="Governance discourse surged 220%",
            action="Prepare a governance situation brief for diaspora community leaders.",
            reasoning="Governance is the dominant narrative this period.",
            expected_outcome="Informed diaspora community with reduced uncertainty.",
            evidence="312 governance records",
            time_horizon="30 days",
        )
        print("\nSample 1 (Governance -- expect real stakeholders):")
        import json
        print(json.dumps(rec1, indent=2, default=str))

        rec2 = build_recommendation(
            db,
            category="MONITOR", priority="Medium",
            issue="Security narrative geographic concentration",
            action="Monitor security discourse daily.",
            reasoning="Security situations can escalate quickly.",
            expected_outcome="Early warning of security developments.",
            evidence="45 records",
            time_horizon="Ongoing",
        )
        print("\nSample 2 (Security -- expect EMPTY stakeholders, honestly, no sector mapping exists):")
        print(json.dumps(rec2, indent=2, default=str))
    finally:
        db.close()
