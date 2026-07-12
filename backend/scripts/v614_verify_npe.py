"""
NDIP V6.1.4 Phase I/J -- live verification that National Pulse
Executive's recommended_actions now originate from the Executive
Decision Engine, with full enrichment.

Run: docker exec agora-backend-1 python scripts/v614_verify_npe.py
"""
import sys
sys.path.insert(0, '/app')
import json

from app.db.database import SessionLocal
from app.services.national_pulse_executive import generate_national_pulse_executive

db = SessionLocal()
result = generate_national_pulse_executive(db, days=30, pulse_score=71, pulse_label="Stable")
db.close()

actions = result.get("recommended_actions", [])
print(f"Total recommended_actions: {len(actions)}")
print()

generated_by_ede = [a for a in actions if a.get("generated_by") == "Executive Decision Engine"]
print(f"Actions tagged generated_by='Executive Decision Engine': {len(generated_by_ede)}")
print()

for a in actions:
    print(json.dumps(a, indent=2, default=str))
    print()
