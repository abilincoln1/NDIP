"""
NDIP V6.1.4 Phase I/J -- live verification that Election Intelligence's
leadership_actions now originate from the Executive Decision Engine.

Run: docker exec agora-backend-1 python scripts/v614_verify_election_intelligence.py
"""
import sys
sys.path.insert(0, '/app')
import json

from app.db.database import SessionLocal
from app.services.election_intelligence import generate_full_election_intelligence

db = SessionLocal()
result = generate_full_election_intelligence(db, days=30)
db.close()

leadership_actions = result.get("election_implications", {}).get("leadership_actions", [])
print(f"Total leadership_actions: {len(leadership_actions)}")
generated_by_ede = [a for a in leadership_actions if a.get("generated_by") == "Executive Decision Engine"]
print(f"Tagged generated_by='Executive Decision Engine': {len(generated_by_ede)}")
print()
for a in leadership_actions:
    print(json.dumps(a, indent=2, default=str))
    print()
