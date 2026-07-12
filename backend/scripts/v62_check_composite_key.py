"""Check the real key name for composite index in compute_stakeholder_influence()."""
import sys; sys.path.insert(0, '/app')
from app.db.database import SessionLocal
from app.services.stakeholder_influence import compute_stakeholder_influence
db = SessionLocal()
result = compute_stakeholder_influence(db, 18, days=30)
print("Keys returned by compute_stakeholder_influence():")
for k, v in result.items():
    print(f"  {k}: {v}")
db.close()
