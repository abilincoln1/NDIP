"""
NDIP V6.2 -- now that the per-stakeholder scaling bug is fixed, profile
generate_opportunity_dossier()'s remaining ~4.2s flat cost to see what's
left to optimize.

Run: docker exec agora-backend-1 python scripts/v62_profile_dossier_internals.py
"""
import sys
sys.path.insert(0, '/app')
import time

from app.db.database import SessionLocal
db = SessionLocal()


def timed(label, fn):
    start = time.time()
    try:
        result = fn()
        elapsed = time.time() - start
        print(f"  {elapsed:7.3f}s  {label}")
        return result
    except Exception as e:
        elapsed = time.time() - start
        print(f"  {elapsed:7.3f}s  {label}  -- FAILED: {type(e).__name__}: {e}")
        return None


print("=" * 70)
print("  Profiling generate_opportunity_dossier internals (opp #4, 0 stakeholders)")
print("=" * 70)

from app.services.opportunity_intelligence import (
    compute_and_store_opportunity_alignment, compute_opportunity_readiness, get_current_pathway,
)

timed("compute_and_store_opportunity_alignment", lambda: compute_and_store_opportunity_alignment(db, 4))
timed("compute_opportunity_readiness", lambda: compute_opportunity_readiness(db, 4))
timed("get_current_pathway", lambda: get_current_pathway(db, 4))

db.close()
print()
print("=" * 70)
print("  PROFILING COMPLETE")
print("=" * 70)
