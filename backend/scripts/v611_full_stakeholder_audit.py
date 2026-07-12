"""
Full, honest audit of every StakeholderRegistry row with stakeholder_type
set, showing creation date, to understand the real timeline across
sessions before writing any completion report claims.

Run: docker exec agora-backend-1 python scripts/v611_full_stakeholder_audit.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.models import StakeholderRegistry

db = SessionLocal()
rows = db.query(StakeholderRegistry).filter(
    StakeholderRegistry.stakeholder_type.isnot(None)
).order_by(StakeholderRegistry.created_at.asc()).all()

print(f"Total StakeholderRegistry rows with stakeholder_type set: {len(rows)}")
print()
for r in rows:
    print(f"  id={r.id:4d}  {str(r.created_at)[:19]}  {r.stakeholder_type.value:25s}  {r.name}")

db.close()
