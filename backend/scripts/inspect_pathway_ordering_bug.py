"""
Diagnostic: trace why generate_execution_plan's engagement sequence
named NESREA (lower alignment, 45.6) as lead stakeholder ahead of
Federal Ministry of Environment (higher alignment, 64.3) for the Green
Climate Fund Programmes opportunity -- this looks backwards relative to
the alignment scores the same plan generation reports just above it.

Run: docker exec agora-backend-1 python scripts/inspect_pathway_ordering_bug.py
"""
import sys
sys.path.insert(0, '/app')
import json
import inspect

from app.db.database import SessionLocal
from app.models.models import OpportunityAssessment
from app.services.opportunity_intelligence import generate_engagement_pathway

db = SessionLocal()

opp = db.query(OpportunityAssessment).filter(OpportunityAssessment.title == "Green Climate Fund Programmes").first()
print("opp.stakeholders_json (raw, as stored on the OpportunityAssessment row):")
print(json.dumps(json.loads(opp.stakeholders_json), indent=2))

print()
print("=== generate_engagement_pathway source ===")
print(inspect.getsource(generate_engagement_pathway))

db.close()
