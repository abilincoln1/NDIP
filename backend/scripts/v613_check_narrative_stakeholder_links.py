"""
Pre-check: which narratives have ANY genuinely sensible stakeholder
mapping available right now, given real registry data -- so the
responsible_stakeholders lookup added to Decision Support is grounded in
real, defensible associations rather than guessed at.

Run: docker exec agora-backend-1 python scripts/v613_check_narrative_stakeholder_links.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.models import StakeholderRegistry

db = SessionLocal()

# Real sector values currently in the registry (confirmed from the V6.1.1 backfill precheck)
sectors = db.query(StakeholderRegistry.sector).distinct().all()
print("Real sector values in registry:")
for (s,) in sectors:
    print(f"  {s}")

db.close()
