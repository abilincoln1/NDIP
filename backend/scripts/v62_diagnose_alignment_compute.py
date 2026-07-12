"""
NDIP V6.2 -- Inspect compute_and_store_opportunity_alignment() directly,
the confirmed root cause of the dossier's 40-60 second per-call cost.

Run: docker exec agora-backend-1 python scripts/v62_diagnose_alignment_compute.py
"""
import sys
sys.path.insert(0, '/app')
import inspect

from app.services.opportunity_intelligence import compute_and_store_opportunity_alignment
print(inspect.getsource(compute_and_store_opportunity_alignment))
