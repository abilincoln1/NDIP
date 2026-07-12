"""
NDIP V6.1.1 Phase F pre-check -- what does generate_execution_plan()
already produce for the "Mini-Grid Programmes" opportunity (the one
opportunity with genuine office-holder linkage), so the Executive
Opportunity Dossier builds on top of real existing output rather than
duplicating it.

Run: docker exec agora-backend-1 python scripts/v611_phase_f_precheck.py
"""
import sys
sys.path.insert(0, '/app')
import json

from app.db.database import SessionLocal
from app.models.models import OpportunityAssessment

db = SessionLocal()

opp = db.query(OpportunityAssessment).filter(OpportunityAssessment.title == "Mini-Grid Programmes").first()
if not opp:
    print("Mini-Grid Programmes opportunity not found.")
else:
    print(f"Opportunity #{opp.id}: {opp.title}")
    print(f"  category: {opp.category}")
    print(f"  status: {opp.status}")
    print(f"  strategic_value: {opp.strategic_value}")
    print(f"  stakeholders_json: {opp.stakeholders_json}")
    print()

    try:
        from app.services.opportunity_intelligence import generate_execution_plan
        plan = generate_execution_plan(db, opp.id)
        print("generate_execution_plan() output:")
        print(json.dumps(plan, indent=2, default=str))
    except Exception as e:
        print(f"generate_execution_plan() failed: {type(e).__name__}: {e}")

db.close()
