"""
Diagnostic: "Minister of Works" appeared linked to Transport Projects but
was never in this session's Phase A seed list -- confirm where this row
actually came from before reporting it as a Phase A/D result.

Run: docker exec agora-backend-1 python scripts/v611_check_minister_of_works.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.models import StakeholderRegistry

db = SessionLocal()
row = db.query(StakeholderRegistry).filter(StakeholderRegistry.name == "Minister of Works").first()
if row:
    print(f"id={row.id}")
    print(f"name={row.name}")
    print(f"category={row.category}")
    print(f"stakeholder_type={row.stakeholder_type}")
    print(f"sector={row.sector}")
    print(f"role_description={row.role_description}")
    print(f"aliases_json={row.aliases_json}")
    print(f"created_at={row.created_at}")
else:
    print("No row found with this exact name.")

db.close()
