"""
Check whether the raw StakeholderType enum object in
priority_decision_makers actually causes a problem at the real API
boundary (FastAPI JSON serialization) or whether it's only an artifact
of calling the route function directly in Python (which returns the raw
dict, not the JSON-serialized response).

Run: docker exec agora-backend-1 python scripts/v611_check_enum_serialization.py
"""
import sys
sys.path.insert(0, '/app')
import json

from app.db.database import SessionLocal
from app.api.routes.leadership_pack import leadership_pack

db = SessionLocal()
result = leadership_pack(days=30, db=db, _={"email": "admin@agora.rtifn.org"})
db.close()

try:
    serialized = json.dumps(result["priority_decision_makers"], default=str)
    print("json.dumps with default=str succeeded:")
    print(serialized)
except Exception as e:
    print(f"json.dumps FAILED even with default=str: {type(e).__name__}: {e}")

print()
print("Testing WITHOUT default=str (this is what FastAPI's default JSON encoder effectively needs to handle):")
try:
    serialized2 = json.dumps(result["priority_decision_makers"])
    print(serialized2)
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")
