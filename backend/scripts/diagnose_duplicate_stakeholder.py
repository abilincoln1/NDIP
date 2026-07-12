"""
Diagnostic: trace why step 3's "secondary stakeholder" duplicated the
lead stakeholder for Opportunity #2 (Green Climate Fund Programmes) after
the alignment-ranking fix.

Run: docker exec agora-backend-1 python scripts/diagnose_duplicate_stakeholder.py
"""
import sys
sys.path.insert(0, '/app')
import json

from app.db.database import SessionLocal
from app.models.models import OpportunityAssessment, OpportunityAlignmentScore

db = SessionLocal()

opp = db.query(OpportunityAssessment).filter(OpportunityAssessment.title == "Green Climate Fund Programmes").first()
print("opp.stakeholders_json (raw):")
stakeholders = json.loads(opp.stakeholders_json)
print(json.dumps(stakeholders, indent=2))

print("\nOpportunityAlignmentScore rows for this opportunity, ordered by score desc:")
alignment_rows = db.query(OpportunityAlignmentScore).filter(
    OpportunityAlignmentScore.opportunity_id == opp.id
).order_by(OpportunityAlignmentScore.alignment_score.desc()).all()
for row in alignment_rows:
    print(f"  id={row.id} stakeholder_id={row.stakeholder_id} score={row.alignment_score} computed_at={row.computed_at}")

print(f"\nTotal alignment rows for this opportunity (across ALL past activation runs, not deduped): {len(alignment_rows)}")

db.close()
