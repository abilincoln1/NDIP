"""
NDIP V6.2 -- Confirm the root cause of generate_opportunity_dossier()'s
slowness: does generate_execution_plan() call compute_stakeholder_mentions()
(or an equivalent post-table scan) fresh, with no caching, on every call?

Run: docker exec agora-backend-1 python scripts/v62_diagnose_dossier_slowness.py
"""
import sys
sys.path.insert(0, '/app')
import inspect

from app.services.opportunity_intelligence import generate_execution_plan
source = inspect.getsource(generate_execution_plan)
print("=" * 70)
print("  generate_execution_plan() source")
print("=" * 70)
print(source)
