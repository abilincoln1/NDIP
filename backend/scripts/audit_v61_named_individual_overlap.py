"""
NDIP V6.1 (Strategic Stakeholder Intelligence) Pre-Build Audit --
checking overlap against V6.2's just-completed schema work, before
extending anything further.

Run: docker exec agora-backend-1 python scripts/audit_v61_named_individual_overlap.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.models import StakeholderRegistry, StakeholderType, StakeholderCategory

db = SessionLocal()

print("=" * 70)
print("  SECTION 1 -- Does StakeholderType already cover named-person roles?")
print("=" * 70)
for t in StakeholderType:
    print(f"  {t.value}")

print()
print("=" * 70)
print("  SECTION 2 -- Current StakeholderRegistry columns (confirm what V6.2 added)")
print("=" * 70)
for c in StakeholderRegistry.__table__.columns:
    print(f"  {c.name:30s} {c.type}  nullable={c.nullable}")

print()
print("=" * 70)
print("  SECTION 3 -- Any existing rows already typed as individual-like?")
print("=" * 70)
rows = db.query(StakeholderRegistry).filter(StakeholderRegistry.stakeholder_type.isnot(None)).all()
print(f"  Rows with stakeholder_type set: {len(rows)}")
for r in rows[:10]:
    print(f"    {r.name}: {r.stakeholder_type}")

print()
print("=" * 70)
print("  SECTION 4 -- Existing StakeholderCategory.POLITICAL rows (closest existing overlap)")
print("=" * 70)
political = db.query(StakeholderRegistry).filter(StakeholderRegistry.category == StakeholderCategory.POLITICAL).all()
for r in political:
    print(f"  {r.name} | category={r.category} | sector={r.sector} | role_description={r.role_description}")

db.close()
print()
print("=" * 70)
print("  AUDIT COMPLETE")
print("=" * 70)
