"""
NDIP V6.2 -- Inspect compute_opportunity_alignment() (singular, per-
stakeholder), called in a loop by compute_and_store_opportunity_alignment.

Run: docker exec agora-backend-1 python scripts/v62_diagnose_single_alignment.py
"""
import sys
sys.path.insert(0, '/app')
import inspect

from app.services.opportunity_intelligence import compute_opportunity_alignment
print(inspect.getsource(compute_opportunity_alignment))
