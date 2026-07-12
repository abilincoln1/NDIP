"""
NDIP V6.1 Architecture Consolidation Report -- final live evidence pull.
Every number in this output is sourced directly from the live database
or live function calls, for direct citation in the report.

Run: docker exec agora-backend-1 python scripts/v61_final_evidence_pull.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.models import (
    StakeholderRegistry, StakeholderRelationship, OpportunityAssessment,
    RecommendationRecord, OutcomeChainLink, StakeholderEngagement,
    OpportunityAlignmentScore, OpportunityReadinessAssessment,
)

db = SessionLocal()

print("=" * 70)
print("  FINAL EVIDENCE PULL")
print("=" * 70)

print(f"\nStakeholderRegistry total active: {db.query(StakeholderRegistry).filter(StakeholderRegistry.is_active==True).count()}")
print(f"StakeholderRegistry with stakeholder_type set (named/typed): {db.query(StakeholderRegistry).filter(StakeholderRegistry.stakeholder_type.isnot(None)).count()}")
from sqlalchemy import func
type_counts = db.query(StakeholderRegistry.stakeholder_type, func.count(StakeholderRegistry.id)).filter(
    StakeholderRegistry.stakeholder_type.isnot(None)
).group_by(StakeholderRegistry.stakeholder_type).all()
for t, c in type_counts:
    print(f"    {t}: {c}")

print(f"\nStakeholderRelationship total active: {db.query(StakeholderRelationship).filter(StakeholderRelationship.is_active==True).count()}")
rel_counts = db.query(StakeholderRelationship.relationship_type, func.count(StakeholderRelationship.id)).filter(
    StakeholderRelationship.is_active==True
).group_by(StakeholderRelationship.relationship_type).all()
for t, c in rel_counts:
    print(f"    {t}: {c}")

print(f"\nOpportunityAssessment total: {db.query(OpportunityAssessment).count()}")
print(f"OpportunityAlignmentScore total: {db.query(OpportunityAlignmentScore).count()}")
print(f"OpportunityReadinessAssessment total: {db.query(OpportunityReadinessAssessment).count()}")

print(f"\nRecommendationRecord total: {db.query(RecommendationRecord).count()}")
evaluated = db.query(RecommendationRecord).filter(RecommendationRecord.status != "OPEN").count()
print(f"RecommendationRecord evaluated (non-OPEN): {evaluated}")
ede_tagged = db.query(RecommendationRecord).filter(RecommendationRecord.module.in_(["decision_support", "national_pulse", "election_intelligence"])).count()
print(f"RecommendationRecord from the 3 EDE-consuming modules: {ede_tagged}")
module_counts = db.query(RecommendationRecord.module, func.count(RecommendationRecord.id)).group_by(RecommendationRecord.module).all()
for m, c in module_counts:
    print(f"    module={m}: {c}")

print(f"\nOutcomeChainLink (deprecated V6.0 model): {db.query(OutcomeChainLink).count()}")
print(f"StakeholderEngagement (V6.2 unified system): {db.query(StakeholderEngagement).count()}")

db.close()
print("\n" + "=" * 70)
print("  EVIDENCE PULL COMPLETE")
print("=" * 70)
