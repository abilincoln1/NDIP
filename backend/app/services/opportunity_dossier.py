"""
NDIP V6.1.1 Phase F -- Executive Opportunity Dossier

DESIGN PRINCIPLE: this is a structuring/labeling layer on top of the
existing, real, V6.0A-built generate_execution_plan() -- confirmed via
live precheck to already compute real alignment-classified stakeholders
for tracked opportunities. This module does NOT recompute alignment,
readiness, or stakeholder detection; it re-presents that same real data
into the dossier's specific section headings, classifying each
stakeholder by their actual stakeholder_type (now that V6.1.1 office-
holders carry that field) into Decision Makers / Funding / Implementation
/ Oversight buckets, rather than introducing a second classification
system.

Honest about sparsity: for opportunities where stakeholder/office-holder
linkage is empty or thin (confirmed live: 2 of 4 tracked opportunities
have zero linked stakeholders at all), the dossier says so explicitly
rather than rendering empty-looking sections without explanation.

Run standalone for live verification:
docker exec agora-backend-1 python scripts/v611_dossier_service.py
"""
import sys
sys.path.insert(0, '/app')

from sqlalchemy.orm import Session as SQLSession


# --- Classification logic: which StakeholderType values map to which dossier bucket ---
DECISION_MAKER_TYPES = {"FEDERAL_MINISTRY", "STATE_GOVERNMENT", "POLITICAL_ACTOR", "PARTY_OFFICIAL", "LEGISLATOR"}
FUNDING_TYPES = {"DEVELOPMENT_FINANCE", "INTERNATIONAL_DONOR", "MULTILATERAL", "INVESTOR"}
IMPLEMENTATION_TYPES = {"FEDERAL_AGENCY", "LOCAL_GOVERNMENT", "INFRASTRUCTURE_OPERATOR", "ENERGY_OPERATOR",
                         "PRIVATE_SECTOR", "WASTE_MANAGEMENT_ACTOR"}
OVERSIGHT_TYPES = {"CIVIL_SOCIETY", "NGO", "MEDIA", "ACADEMIC"}


def _classify_stakeholder(stakeholder_type: str) -> str:
    """Maps a StakeholderType value to a dossier bucket. Returns 'Unclassified' honestly if the type doesn't fit a known bucket, rather than guessing."""
    if stakeholder_type in DECISION_MAKER_TYPES:
        return "Decision Makers"
    if stakeholder_type in FUNDING_TYPES:
        return "Funding Sources"
    if stakeholder_type in IMPLEMENTATION_TYPES:
        return "Implementation"
    if stakeholder_type in OVERSIGHT_TYPES:
        return "Oversight / Monitoring"
    return "Unclassified"


def generate_opportunity_dossier(db: SQLSession, opportunity_id: int) -> dict:
    """
    Phase F: builds the Executive Opportunity Dossier from existing,
    already-computed data -- generate_execution_plan() (alignment,
    readiness, engagement sequence) plus each stakeholder's real
    stakeholder_type (where set) to classify them into the dossier's
    Decision Makers / Funding / Implementation / Oversight structure.
    """
    from app.models.models import OpportunityAssessment, StakeholderRegistry
    from app.services.opportunity_intelligence import generate_execution_plan

    opp = db.query(OpportunityAssessment).filter(OpportunityAssessment.id == opportunity_id).first()
    if not opp:
        raise ValueError("Opportunity not found")

    plan = generate_execution_plan(db, opportunity_id)

    # Look up each required_stakeholder's real stakeholder_type, by name
    # (the execution plan only returns names, not IDs, for this list).
    name_to_type = {
        s.name: s.stakeholder_type
        for s in db.query(StakeholderRegistry).filter(
            StakeholderRegistry.name.in_([r["name"] for r in plan["required_stakeholders"]])
        ).all()
    }

    buckets = {"Decision Makers": [], "Funding Sources": [], "Implementation": [], "Oversight / Monitoring": [], "Unclassified": []}
    for stakeholder in plan["required_stakeholders"]:
        stype = name_to_type.get(stakeholder["name"])
        bucket = _classify_stakeholder(stype) if stype else "Unclassified"
        buckets[bucket].append({
            "name": stakeholder["name"],
            "alignment_score": stakeholder["alignment_score"],
            "classification": stakeholder["classification"],
            "stakeholder_type": stype,
        })

    # Honest sparsity flag, per the mandatory discipline -- don't render
    # empty sections silently.
    data_quality_notes = []
    if not plan["required_stakeholders"]:
        data_quality_notes.append("No stakeholders are currently linked to this opportunity. This dossier section will be sparse until discourse-based detection identifies relevant institutions or office-holders.")
    if not buckets["Decision Makers"] and not buckets["Funding Sources"]:
        data_quality_notes.append("No named public office-holder with confirmed Decision Maker or Funding Source authority is currently linked. Institutional stakeholders are present, but specific accountable individuals have not yet been identified with sufficient discourse signal.")

    return {
        "opportunity_id": opportunity_id,
        "executive_summary": f"{plan['opportunity']} -- strategic value: {plan['strategic_value']}, readiness: {plan['confidence_assessment']['readiness_label']} ({plan['confidence_assessment']['readiness_score']}).",
        "opportunity_assessment": plan["opportunity"],
        "strategic_importance": plan["strategic_value"],
        "stakeholders_by_role": buckets,
        "implementation_pathway": plan["recommended_engagement_sequence"],
        "strategic_risks": plan["potential_barriers"],
        "recommended_engagement": plan["recommended_engagement_sequence"][:2],
        "expected_outcomes": plan["expected_outcomes"],
        "recommendation_confidence": plan["confidence_assessment"],
        "data_quality_notes": data_quality_notes,
    }


if __name__ == "__main__":
    import json
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        from app.models.models import OpportunityAssessment
        opportunities = db.query(OpportunityAssessment).all()
        print(f"Generating dossiers for all {len(opportunities)} tracked opportunities...\n")
        for opp in opportunities:
            print("=" * 70)
            dossier = generate_opportunity_dossier(db, opp.id)
            print(json.dumps(dossier, indent=2, default=str))
            print()
    finally:
        db.close()
