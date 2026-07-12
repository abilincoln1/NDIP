"""
NDIP V6.2 Phase A -- Full Function-Level Profiling (Round 2)

Breaks down EVERY significant function across all 6 executive products,
including internal breakdowns of generate_watchlist and
get_top_influence_stakeholders -- the two largest remaining costs
identified but not yet internally profiled.

Run: docker exec agora-backend-1 python scripts/v62_phase_a_full_profile.py
"""
import sys
sys.path.insert(0, '/app')
import time

from app.db.database import SessionLocal
db = SessionLocal()
days = 30

timings = []


def timed(label, fn):
    start = time.time()
    try:
        result = fn()
        elapsed = time.time() - start
        timings.append((elapsed, label))
        print(f"  {elapsed:7.3f}s  {label}")
        return result
    except Exception as e:
        elapsed = time.time() - start
        timings.append((elapsed, f"{label} (FAILED)"))
        print(f"  {elapsed:7.3f}s  {label}  -- FAILED: {type(e).__name__}: {e}")
        return None


print("=" * 70)
print("  generate_watchlist -- internal breakdown")
print("=" * 70)
import inspect
from app.services.watchlist import generate_watchlist
print(inspect.getsource(generate_watchlist)[:2000])
print("...")

print()
print("=" * 70)
print("  get_top_influence_stakeholders -- internal breakdown")
print("=" * 70)
from app.services.stakeholder_influence import get_top_influence_stakeholders, _compute_momentum_scores_for_all, _relationship_strength_scores_for_all, _opportunity_relevance_scores_for_all, _narrative_impact_score_for_all
from app.services.stakeholder_registry import compute_stakeholder_mentions

timed("compute_stakeholder_mentions (all stakeholders)", lambda: compute_stakeholder_mentions(db, days))
timed("_compute_momentum_scores_for_all", lambda: _compute_momentum_scores_for_all(db, days))
timed("_relationship_strength_scores_for_all", lambda: _relationship_strength_scores_for_all(db))
timed("_opportunity_relevance_scores_for_all", lambda: _opportunity_relevance_scores_for_all(db))
timed("_narrative_impact_score_for_all", lambda: _narrative_impact_score_for_all(db, days))
timed("get_top_influence_stakeholders (full, all sub-calls combined)", lambda: get_top_influence_stakeholders(db, limit=50, days=days))

db.close()
print()
print("=" * 70)
print("  TOP COSTS THIS PROFILE RUN, SORTED")
print("=" * 70)
for elapsed, label in sorted(timings, reverse=True):
    print(f"  {elapsed:7.3f}s  {label}")
