"""
NDIP V6.1.1 Phase D -- link the one office-holder row with real discourse
signal ("Minister of Power", 18 mentions) into the opportunity detection
pipeline, by re-running opportunity assessment generation so the
detection engine has a chance to pick this stakeholder up naturally
(rather than manually forcing a link that the real detection logic
wouldn't have found on its own).

Per the mandatory discipline: this does NOT assume success. It re-runs
the real detection function and then directly queries the result to
confirm, honestly, whether Minister of Power was actually picked up.

Run: docker exec agora-backend-1 python scripts/v611_phase_d_link_minister.py
"""
import sys
sys.path.insert(0, '/app')
import json

from app.db.database import SessionLocal
from app.models.models import OpportunityAssessment

db = SessionLocal()

try:
    from app.services.opportunity_intelligence import generate_opportunity_assessments
    print("Re-running generate_opportunity_assessments()...")
    result = generate_opportunity_assessments(db, days=30)
    print(f"Result: {result}")
except Exception as e:
    print(f"generate_opportunity_assessments() failed or doesn't match expected signature: {type(e).__name__}: {e}")
    print("Falling back to direct inspection of current state without re-running detection.")

print()
print("=" * 70)
print("Post-run check -- is 'Minister of Power' now linked to any opportunity?")
print("=" * 70)
opportunities = db.query(OpportunityAssessment).all()
found_anywhere = False
for opp in opportunities:
    if not opp.stakeholders_json:
        continue
    stakeholders = json.loads(opp.stakeholders_json)
    names = [s.get("name") for s in stakeholders]
    if "Minister of Power" in names:
        found_anywhere = True
        print(f"  FOUND in opportunity #{opp.id}: {opp.title}")
    else:
        print(f"  Not present in #{opp.id}: {opp.title} (current stakeholders: {names})")

if not found_anywhere:
    print()
    print("  HONEST FINDING: Minister of Power was NOT picked up by the real detection")
    print("  logic for any currently tracked opportunity, despite having real mention")
    print("  signal (18 mentions). This likely means the detection engine's per-opportunity")
    print("  stakeholder-matching threshold or category-relevance logic didn't surface it --")
    print("  worth investigating the actual matching criteria rather than assuming this")
    print("  is simply 'not enough data'.")

db.close()
