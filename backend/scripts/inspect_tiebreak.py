"""
Diagnostic: confirm how compute_and_store_opportunity_alignment orders
its return value when stakeholders are tied on alignment_score, so the
pathway function's tie-break can be made consistent with it.

Run: docker exec agora-backend-1 python scripts/inspect_tiebreak.py
"""
import sys
sys.path.insert(0, '/app')
import inspect
from app.services.opportunity_intelligence import compute_and_store_opportunity_alignment

src = inspect.getsource(compute_and_store_opportunity_alignment)
print(src)
