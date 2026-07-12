"""
Diagnostic: inspect run_evaluation_cycle() before activating it, to
understand why 318 recommendations have sat OPEN with zero evaluations
-- most likely a minimum-age gate (e.g. recommendations must be 7+ days
old before evaluation), which would mean Phase D's job is simply to
confirm the gate works correctly on whichever recommendations are now
old enough, not to build new evaluation logic.

Run: docker exec agora-backend-1 python scripts/inspect_evaluation_cycle.py
"""
import sys
sys.path.insert(0, '/app')
import inspect

from app.db.database import SessionLocal
from app.models.models import RecommendationRecord
from datetime import datetime, timezone

db = SessionLocal()

from app.services.recommendation_tracker import run_evaluation_cycle
print("=== run_evaluation_cycle source (first 60 lines) ===")
src_lines = inspect.getsource(run_evaluation_cycle).split("\n")
print("\n".join(src_lines[:60]))

print("\n=== Recommendation age distribution ===")
now = datetime.now(timezone.utc)
recs = db.query(RecommendationRecord).filter(RecommendationRecord.status == "OPEN").all()
age_buckets = {"0-3 days": 0, "4-6 days": 0, "7-13 days": 0, "14+ days": 0}
for r in recs:
    age_days = (now - r.created_at).days if r.created_at else -1
    if age_days < 4:
        age_buckets["0-3 days"] += 1
    elif age_days < 7:
        age_buckets["4-6 days"] += 1
    elif age_days < 14:
        age_buckets["7-13 days"] += 1
    else:
        age_buckets["14+ days"] += 1
for bucket, count in age_buckets.items():
    print(f"  {bucket}: {count}")

print(f"\nTotal OPEN recommendations: {len(recs)}")
print(f"Recommendations with period_days set: {sum(1 for r in recs if r.period_days)}")

db.close()
