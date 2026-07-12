"""
NDIP V6.2 -- diagnose the two remaining cost centers: why does
compute_and_store_opportunity_alignment cost ~4s even with ZERO
stakeholders, and what does compute_opportunity_readiness actually do.

Run: docker exec agora-backend-1 python scripts/v62_diagnose_remaining_cost.py
"""
import sys
sys.path.insert(0, '/app')
import inspect

from app.services.opportunity_intelligence import compute_opportunity_readiness
print("=" * 70)
print("  compute_opportunity_readiness source")
print("=" * 70)
print(inspect.getsource(compute_opportunity_readiness))
