"""
NDIP V6.1.1 Phase D pre-check -- confirm current state of tracked
opportunities and their stakeholder linkage before extending anything,
per the mandatory "verify, don't assume" discipline.

Run: docker exec agora-backend-1 python scripts/v611_phase_d_precheck.py
"""
import sys
sys.path.insert(0, '/app')
import json

from app.db.database import SessionLocal
from app.models.models import OpportunityAssessment, StakeholderRegistry

db = SessionLocal()

opportunities = db.query(OpportunityAssessment).all()
print(f"Total tracked OpportunityAssessment rows: {len(opportunities)}")
print()

for opp in opportunities:
    print(f"--- #{opp.id}: {opp.title} ({opp.category}) ---")
    if opp.stakeholders_json:
        stakeholders = json.loads(opp.stakeholders_json)
        print(f"  Currently linked stakeholders ({len(stakeholders)}):")
        for s in stakeholders:
            print(f"    - {s.get('name')} (id={s.get('stakeholder_id')}, mentions={s.get('mention_count')})")
    else:
        print("  No stakeholders_json set.")
    print()

# Check: do any of the new Phase A office-holder rows have ANY mention-based
# detection signal yet? (They were just seeded -- likely 0, since discourse
# detection runs against existing aliases_json, and these are brand new rows
# with names that may not appear verbatim in recent discourse.)
print("=" * 70)
print("Checking whether any new Phase A office-holder rows have been detected in discourse yet:")
from app.services.stakeholder_registry import compute_stakeholder_mentions
mentions = compute_stakeholder_mentions(db, 30)

office_holder_names = [
    "Minister of Power", "Minister of Environment", "Managing Director, Rural Electrification Agency",
    "Chairman, Nigerian Electricity Regulatory Commission", "Director-General, National Council on Climate Change",
]
stakeholder_lookup = {s.name: s.id for s in db.query(StakeholderRegistry).all()}
for name in office_holder_names:
    sid = stakeholder_lookup.get(name)
    if sid is None:
        print(f"  {name}: NOT FOUND IN REGISTRY")
        continue
    data = mentions.get(sid, {"mention_count": 0, "source_count": 0})
    print(f"  {name}: {data['mention_count']} mentions, {data['source_count']} sources (last 30 days)")

db.close()
