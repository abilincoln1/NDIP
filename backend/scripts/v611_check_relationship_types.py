"""
NDIP V6.1.1 Phase C pre-check -- does RelationshipType already cover the
spec's vocabulary (HOLDS_OFFICE, LEADS, OVERSEES, REPORTS_TO, PART_OF,
IMPLEMENTS, FUNDS, REGULATES, SUPERVISES, APPOINTS)?

Run: docker exec agora-backend-1 python scripts/v611_check_relationship_types.py
"""
import sys
sys.path.insert(0, '/app')
from app.models.models import RelationshipType

existing = {t.value for t in RelationshipType}
needed = ["HOLDS_OFFICE", "LEADS", "OVERSEES", "REPORTS_TO", "PART_OF",
          "IMPLEMENTS", "FUNDS", "REGULATES", "SUPERVISES", "APPOINTS"]

print("Existing RelationshipType values:", sorted(existing))
print()
print("Spec's needed values, with status:")
missing = []
for v in needed:
    status = "EXISTS" if v in existing else "MISSING"
    if v not in existing:
        missing.append(v)
    print(f"  {v:15s} {status}")

print()
print(f"Missing values requiring a code-level enum addition: {missing}")
