"""
Pre-check before backfilling stakeholder_type on the 45 pre-existing
institutional StakeholderRegistry rows: list every row currently lacking
stakeholder_type, with its existing category/sector, so the backfill
mapping is built from real data rather than assumption.

Run: docker exec agora-backend-1 python scripts/v611_backfill_precheck.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.models import StakeholderRegistry

db = SessionLocal()
rows = db.query(StakeholderRegistry).filter(
    StakeholderRegistry.stakeholder_type.is_(None)
).order_by(StakeholderRegistry.category, StakeholderRegistry.name).all()

print(f"Total rows lacking stakeholder_type: {len(rows)}\n")
for r in rows:
    print(f"  id={r.id:4d}  category={str(r.category):30s}  sector={str(r.sector):20s}  name={r.name}")

db.close()
