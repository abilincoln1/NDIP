"""
NDIP V6.1.5 Phase D -- live verification that Decision Support now
delegates stakeholder resolution to the Executive Decision Engine, while
its orchestration (time_horizon, adaptive confidence, persistence)
continues working unchanged.

Run: docker exec agora-backend-1 python scripts/v615_verify_decision_support.py
"""
import sys
sys.path.insert(0, '/app')
import json

from app.db.database import SessionLocal
from app.models.models import RecommendationRecord
from app.services.decision_support import generate_decision_support

db = SessionLocal()

pre_count = db.query(RecommendationRecord).count()

result = generate_decision_support(db, 30)
all_actions = result["immediate_actions"] + result["near_term_actions"] + result["strategic_actions"] + result["monitoring_actions"]

post_count = db.query(RecommendationRecord).count()
db.close()

print(f"Total actions this run: {len(all_actions)}")
generated_by_ede = [a for a in all_actions if a.get("generated_by") == "Executive Decision Engine"]
print(f"Tagged generated_by='Executive Decision Engine': {len(generated_by_ede)}")
with_stakeholders = [a for a in all_actions if a.get("responsible_stakeholders")]
print(f"With non-empty responsible_stakeholders: {len(with_stakeholders)}")
print()
print(f"RecommendationRecord count BEFORE this run: {pre_count}")
print(f"RecommendationRecord count AFTER this run: {post_count}")
print(f"New records persisted (confirms record_recommendation() still works): {post_count - pre_count}")
print()
for a in with_stakeholders[:3]:
    print(json.dumps(a, indent=2, default=str))
    print()
