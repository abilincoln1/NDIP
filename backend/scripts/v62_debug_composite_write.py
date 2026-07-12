"""
Debug exactly what materialise_influence_profiles writes for stakeholder 18,
which we know should have composite_index = 75.1.
"""
import sys; sys.path.insert(0, '/app')
from app.db.database import SessionLocal
from app.services.stakeholder_influence import compute_stakeholder_influence
from app.models.models import StakeholderInfluenceProfile
from sqlalchemy import and_
from datetime import datetime, timezone, timedelta

db = SessionLocal()

# What does compute return?
scores = compute_stakeholder_influence(db, 18, days=30)
print(f"compute_stakeholder_influence(18) composite_index key: {scores.get('composite_index')}")
print(f"All score keys: {list(scores.keys())}")

# What does the existing row have?
today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
existing = db.query(StakeholderInfluenceProfile).filter(
    and_(
        StakeholderInfluenceProfile.stakeholder_id == 18,
        StakeholderInfluenceProfile.computed_at >= today_start,
    )
).first()
if existing:
    print(f"Existing row composite_index: {existing.composite_index}")
    # Try direct update
    existing.composite_index = scores.get("composite_index", 0.0)
    db.commit()
    db.refresh(existing)
    print(f"After direct update: {existing.composite_index}")
else:
    print("No existing row found for stakeholder 18 today")
db.close()
