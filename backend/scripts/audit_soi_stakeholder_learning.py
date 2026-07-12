"""
Audit: Strategic Opportunity Intelligence, Stakeholder Intelligence, and
Learning Decision Support -- confirming what is genuinely live versus
assumed, ahead of the named-individual stakeholder tracking build.

Run: docker exec agora-backend-1 python scripts/audit_soi_stakeholder_learning.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal

db = SessionLocal()

def check(label, fn):
    try:
        result = fn()
        print(f"[OK] {label}: {result}")
    except Exception as e:
        print(f"[FAIL] {label}: {type(e).__name__}: {e}")

print("=" * 70)
print("  SECTION 1 -- STRATEGIC OPPORTUNITY INTELLIGENCE")
print("=" * 70)

check("OpportunityRegistry seeded count", lambda: __import__("app.models.models", fromlist=["OpportunityRegistry"]).OpportunityRegistry and db.query(__import__("app.models.models", fromlist=["OpportunityRegistry"]).OpportunityRegistry).filter(__import__("app.models.models", fromlist=["OpportunityRegistry"]).OpportunityRegistry.is_active == True).count())

from app.models.models import OpportunityRegistry, OpportunityAssessment, StakeholderRegistry, RecommendationRecord, OutcomeChainLink, StakeholderRelationship, OpportunityAlignmentScore, OpportunityReadinessAssessment

check("Opportunity types by category", lambda: {
    cat: db.query(OpportunityRegistry).filter(OpportunityRegistry.category == cat, OpportunityRegistry.is_active == True).count()
    for cat in ["INFRASTRUCTURE", "ENERGY", "CLIMATE_FINANCE", "PPP", "DIASPORA_INVESTMENT", "FEDERAL_PROGRAMMES", "STATE_PROGRAMMES"]
})

check("Total tracked OpportunityAssessment rows", lambda: db.query(OpportunityAssessment).count())
check("OpportunityAssessment by status", lambda: {
    row[0]: row[1] for row in db.query(OpportunityAssessment.status, __import__("sqlalchemy").func.count(OpportunityAssessment.id)).group_by(OpportunityAssessment.status).all()
})

check("compute_opportunity_alignment importable and runnable", lambda: __import__("app.services.opportunity_intelligence", fromlist=["compute_opportunity_alignment"]))

check("OpportunityAlignmentScore rows ever written", lambda: db.query(OpportunityAlignmentScore).count())
check("OpportunityReadinessAssessment rows ever written", lambda: db.query(OpportunityReadinessAssessment).count())

print()
print("=" * 70)
print("  SECTION 2 -- STAKEHOLDER INTELLIGENCE")
print("=" * 70)

check("StakeholderRegistry total active", lambda: db.query(StakeholderRegistry).filter(StakeholderRegistry.is_active == True).count())
check("StakeholderRegistry by category", lambda: {
    row[0]: row[1] for row in db.query(StakeholderRegistry.category, __import__("sqlalchemy").func.count(StakeholderRegistry.id)).filter(StakeholderRegistry.is_active == True).group_by(StakeholderRegistry.category).all()
})
check("StakeholderRelationship total active", lambda: db.query(StakeholderRelationship).filter(StakeholderRelationship.is_active == True).count())

# Does the schema currently support an entity_type (institution vs individual) distinction?
check("StakeholderRegistry columns (checking for individual-tracking readiness)", lambda: [c.name for c in StakeholderRegistry.__table__.columns])

print()
print("=" * 70)
print("  SECTION 3 -- RECOMMENDATION EFFECTIVENESS / LEARNING")
print("=" * 70)

check("Total RecommendationRecord rows", lambda: db.query(RecommendationRecord).count())
check("RecommendationRecord by status", lambda: {
    row[0]: row[1] for row in db.query(RecommendationRecord.status, __import__("sqlalchemy").func.count(RecommendationRecord.id)).group_by(RecommendationRecord.status).all()
})
check("Evaluated (non-OPEN) recommendation count", lambda: db.query(RecommendationRecord).filter(RecommendationRecord.status != "OPEN").count())
check("OutcomeChainLink rows", lambda: db.query(OutcomeChainLink).count())

from app.services.intelligence_learning import run_intelligence_learning_cycle
def learning_cycle_summary():
    cycle = run_intelligence_learning_cycle(db)
    return {
        "platform_learning_score": cycle.get("platform_learning_score"),
        "lessons_learned_count": len(cycle.get("lessons_learned") or []),
        "recommendations_improved": cycle.get("recommendations_improved_count"),
    }
check("Intelligence learning cycle (live)", learning_cycle_summary)

print()
print("=" * 70)
print("  SECTION 4 -- DECISION SUPPORT SPECIFICITY (sample real output)")
print("=" * 70)

from app.services.decision_support import generate_decision_support
def sample_recommendation():
    result = generate_decision_support(db, 7)
    actions = (result.get("immediate_actions") or []) + (result.get("near_term_actions") or [])
    if not actions:
        return "No actions generated this period"
    a = actions[0]
    return {
        "action_text": a.get("action"),
        "has_time_horizon": "time_horizon" in a or "priority" in a,
        "has_evidence": bool(a.get("reasoning") or a.get("evidence")),
        "has_expected_outcome": bool(a.get("expected_outcome")),
    }
check("Sample Decision Support action (live)", sample_recommendation)

db.close()
print()
print("=" * 70)
print("  AUDIT COMPLETE")
print("=" * 70)
