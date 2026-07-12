"""
NDIP V6.0A Phase E -- Opportunity -> Action Linkage

Runs generate_execution_plan() (built earlier, never confirmed live
against real opportunities per the audit) against both currently-tracked
OpportunityAssessment rows, printing the full structured output the spec
requires: What opportunity exists? Why does it matter? Who matters?
What should leadership do? What outcome is expected?

Run: docker exec agora-backend-1 python scripts/activate_execution_plans.py
"""
import sys
sys.path.insert(0, '/app')
import json

from app.db.database import SessionLocal
from app.models.models import OpportunityAssessment
from app.services.opportunity_intelligence import generate_execution_plan


def main():
    print("=" * 70)
    print("  NDIP V6.0A Phase E -- Opportunity -> Action Linkage")
    print("=" * 70)
    db = SessionLocal()
    try:
        opportunities = db.query(OpportunityAssessment).all()
        for opp in opportunities:
            print(f"\n--- Opportunity #{opp.id}: {opp.title} ---")
            plan = generate_execution_plan(db, opp.id)
            print(f"  What opportunity exists?  {plan['opportunity']}")
            print(f"  Strategic Value:          {plan['strategic_value']}")
            print(f"  Who matters? (Required Stakeholders):")
            for s in plan['required_stakeholders']:
                print(f"    - {s['name']} ({s['classification']}, alignment={s['alignment_score']})")
            print(f"  What should leadership do? (Engagement Sequence):")
            for step in plan['recommended_engagement_sequence']:
                print(f"    {step['step_number']}. {step['description']}")
            print(f"  Potential Barriers:")
            for b in plan['potential_barriers']:
                print(f"    - {b}")
            print(f"  Required Approvals: {plan['required_approvals']}")
            print(f"  Required Partnerships: {plan['required_partnerships']}")
            print(f"  Expected Outcome: {plan['expected_outcomes']}")
            print(f"  Confidence Assessment: {plan['confidence_assessment']}")
    finally:
        db.close()
    print("\n" + "=" * 70)
    print("  Phase E complete -- execution plans generated and printed live above")
    print("=" * 70)


if __name__ == "__main__":
    main()
