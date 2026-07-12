"""
NDIP V6.2 -- Detailed profiling of the post-V6.1.x codebase to find
where the new 181-second Leadership Pack time is coming from.
Same approach as the earlier successful profiling session.

Run: docker exec agora-backend-1 python scripts/v62_perf_profile_detailed.py
"""
import sys
sys.path.insert(0, '/app')
import time

from app.db.database import SessionLocal
db = SessionLocal()
days = 30
user = {"email": "admin@agora.rtifn.org"}


def timed(label, fn):
    start = time.time()
    try:
        result = fn()
        elapsed = time.time() - start
        print(f"  {elapsed:7.2f}s  {label}")
        return result
    except Exception as e:
        elapsed = time.time() - start
        print(f"  {elapsed:7.2f}s  {label}  -- FAILED: {type(e).__name__}: {e}")
        return None


print("=" * 70)
print("  DETAILED LEADERSHIP PACK COMPONENT PROFILING")
print("=" * 70)

from app.analytics.strategic_narratives import get_narrative_analysis
narratives = timed("get_narrative_analysis", lambda: get_narrative_analysis(db, days))

from app.analytics.engine import compute_all_metrics
timed("compute_all_metrics", lambda: compute_all_metrics(db, max(days, 30)))

from app.services.narrative_intelligence import generate_situation_room
timed("generate_situation_room", lambda: generate_situation_room(db, days))

from app.services.risk_opportunity import detect_all_risks, detect_all_opportunities
risks = timed("detect_all_risks", lambda: detect_all_risks(db, days))
opps = timed("detect_all_opportunities", lambda: detect_all_opportunities(db, days))

from app.services.watchlist import generate_watchlist
timed("generate_watchlist", lambda: generate_watchlist(db, days))

from app.services.gnei import generate_gnei_intelligence
timed("generate_gnei_intelligence", lambda: generate_gnei_intelligence(db, days))

from app.services.recommendation_tracker import get_decision_support_performance_summary
timed("get_decision_support_performance_summary", lambda: get_decision_support_performance_summary(db))

from app.services.intelligence_learning import run_intelligence_learning_cycle
timed("run_intelligence_learning_cycle", lambda: run_intelligence_learning_cycle(db))

from app.services.opportunity_intelligence import get_top_opportunities, get_opportunity_pipeline_summary
top_opps = timed("get_top_opportunities", lambda: get_top_opportunities(db, limit=5))
timed("get_opportunity_pipeline_summary", lambda: get_opportunity_pipeline_summary(db))

from app.services.stakeholder_registry import get_top_stakeholders
timed("get_top_stakeholders", lambda: get_top_stakeholders(db, limit=8, days=min(days, 30)))

from app.services.stakeholder_influence import get_top_influence_stakeholders, get_emerging_stakeholders
influence_ranked = timed("get_top_influence_stakeholders", lambda: get_top_influence_stakeholders(db, limit=50, days=min(days, 30)))
timed("get_emerging_stakeholders (precomputed)", lambda: get_emerging_stakeholders(db, limit=5, days=min(days, 30), _precomputed_ranked=influence_ranked))

print()
print("  Now profiling the NEW V6.1.1-V6.1.5 additions:")
print()

from app.services.opportunity_dossier import generate_opportunity_dossier
if top_opps:
    for o in top_opps[:5]:
        opp_id = o.get("id") or o.get("opportunity_id")
        if opp_id:
            timed(f"generate_opportunity_dossier (opp #{opp_id})", lambda oid=opp_id: generate_opportunity_dossier(db, oid))

db.close()
print()
print("=" * 70)
print("  PROFILING COMPLETE")
print("=" * 70)
