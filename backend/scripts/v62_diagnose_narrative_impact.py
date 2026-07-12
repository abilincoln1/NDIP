"""
NDIP V6.2 -- Inspect _narrative_impact_score_for_all and
compute_stakeholder_mentions sources, the two real cost drivers behind
get_top_influence_stakeholders' remaining 5.48s.

Run: docker exec agora-backend-1 python scripts/v62_diagnose_narrative_impact.py
"""
import sys
sys.path.insert(0, '/app')
import inspect

from app.services.stakeholder_influence import _narrative_impact_score_for_all
print("=" * 70)
print("  _narrative_impact_score_for_all source")
print("=" * 70)
print(inspect.getsource(_narrative_impact_score_for_all))

from app.services.stakeholder_registry import compute_stakeholder_mentions
print()
print("=" * 70)
print("  compute_stakeholder_mentions source")
print("=" * 70)
print(inspect.getsource(compute_stakeholder_mentions)[:1500])
