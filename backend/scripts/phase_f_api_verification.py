"""
NDIP V6.0A Phase F -- Live API Verification

Calls the actual route handler functions (not the underlying service
functions directly) to confirm the fixes are visible through the real
API layer a frontend would hit, not just through direct service calls.

Run: docker exec agora-backend-1 python scripts/phase_f_api_verification.py
"""
import sys
sys.path.insert(0, '/app')
import json

from app.db.database import SessionLocal
from app.models.models import OpportunityAssessment

db = SessionLocal()
user = {"email": "admin@agora.rtifn.org"}

try:
    opportunities = db.query(OpportunityAssessment).all()
    opp_ids = [o.id for o in opportunities]

    print("=" * 70)
    print("  PHASE F -- /strategic-outcome/* ROUTE VERIFICATION")
    print("=" * 70)

    from app.api.routes.strategic_outcome import get_opportunity_alignment, get_opportunity_readiness_route, get_execution_plan

    for opp_id in opp_ids:
        print(f"\n--- Opportunity #{opp_id} via real route handlers ---")

        align_response = get_opportunity_alignment(opp_id, db=db, _=user)
        print(f"  GET /strategic-outcome/v61/opportunities/{opp_id}/alignment")
        print(f"    {len(align_response['alignment'])} stakeholders returned, top: "
              f"{align_response['alignment'][0]['stakeholder_name']} ({align_response['alignment'][0]['alignment_score']})")

        ready_response = get_opportunity_readiness_route(opp_id, db=db, _=user)
        print(f"  GET /strategic-outcome/v61/opportunities/{opp_id}/readiness")
        print(f"    readiness_score={ready_response['readiness_score']} label={ready_response['readiness_label']}")

        plan_response = get_execution_plan(opp_id, db=db, _=user)
        print(f"  GET /strategic-outcome/v61/opportunities/{opp_id}/execution-plan")
        print(f"    lead stakeholder (step 1 / 'who matters' #1 agree): "
              f"{plan_response['required_stakeholders'][0]['name']} == "
              f"{plan_response['recommended_engagement_sequence'][0]['description'].split('confirm ')[1].split(' as')[0]}")

    print("\n" + "=" * 70)
    print("  PHASE F -- Leadership Pack route (consumer of this data)")
    print("=" * 70)
    from app.api.routes.leadership_pack import leadership_pack
    lp = leadership_pack(days=30, db=db, _=user)
    print(f"  strategic_opportunities count: {len(lp.get('strategic_opportunities', []))}")
    print(f"  key_stakeholders count: {len(lp.get('key_stakeholders', []))}")

finally:
    db.close()

print("\n" + "=" * 70)
print("  Phase F API verification complete")
print("=" * 70)
