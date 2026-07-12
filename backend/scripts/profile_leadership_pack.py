"""
Profile leadership_pack() section by section to find the real bottleneck
behind the 229-second cache-miss time observed live.

Run: docker exec agora-backend-1 python scripts/profile_leadership_pack.py
"""
import sys
sys.path.insert(0, '/app')
import time

from app.db.database import SessionLocal

db = SessionLocal()
days = 14

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
print(f"  PROFILING leadership_pack() internals, days={days}")
print("=" * 70)

from app.analytics.strategic_narratives import get_narrative_analysis
from app.analytics.engine import compute_all_metrics
from app.services.narrative_intelligence import generate_situation_room
from app.services.source_quality import get_source_quality_report, get_data_quality_report
from app.services.risk_opportunity import detect_all_risks, detect_all_opportunities

narratives = timed("get_narrative_analysis", lambda: get_narrative_analysis(db, days))
metrics = timed("compute_all_metrics", lambda: compute_all_metrics(db, max(days, 30)))
situation = timed("generate_situation_room", lambda: generate_situation_room(db, days))
source_quality = timed("get_source_quality_report", lambda: get_source_quality_report(db, days))
data_quality = timed("get_data_quality_report", lambda: get_data_quality_report(db))
risks = timed("detect_all_risks", lambda: detect_all_risks(db, days))
opportunities = timed("detect_all_opportunities", lambda: detect_all_opportunities(db, days))

from app.services.interpretation_engine import generate_differentiated_assessment, generate_comparative_intelligence, generate_narrative_competition_analysis, generate_outlook_engine
assessments = timed("generate_differentiated_assessment x10", lambda: [generate_differentiated_assessment(n) for n in narratives[:10]])
comparisons = timed("generate_comparative_intelligence", lambda: generate_comparative_intelligence(narratives))
competition = timed("generate_narrative_competition_analysis", lambda: generate_narrative_competition_analysis(narratives))
outlook = timed("generate_outlook_engine", lambda: generate_outlook_engine(narratives, days, risks, opportunities))

from app.services.watchlist import generate_watchlist
timed("generate_watchlist", lambda: generate_watchlist(db, days))

from app.services.gnei import generate_gnei_intelligence
timed("generate_gnei_intelligence", lambda: generate_gnei_intelligence(db, days))

from app.services.strategic_importance import score_all_narratives, generate_trigger_attribution
timed("score_all_narratives", lambda: score_all_narratives(narratives))
timed("generate_trigger_attribution", lambda: generate_trigger_attribution(narratives, db, days))

from app.services.recommendation_tracker import get_decision_support_performance_summary
timed("get_decision_support_performance_summary", lambda: get_decision_support_performance_summary(db))

from app.services.intelligence_learning import run_intelligence_learning_cycle
timed("run_intelligence_learning_cycle", lambda: run_intelligence_learning_cycle(db))

from app.services.opportunity_intelligence import get_top_opportunities, get_opportunity_pipeline_summary
from app.services.stakeholder_registry import get_top_stakeholders
timed("get_top_opportunities", lambda: get_top_opportunities(db, limit=5))
timed("get_top_stakeholders", lambda: get_top_stakeholders(db, limit=8, days=min(days, 30)))
timed("get_opportunity_pipeline_summary", lambda: get_opportunity_pipeline_summary(db))

from app.services.stakeholder_influence import get_top_influence_stakeholders, get_emerging_stakeholders
timed("get_top_influence_stakeholders", lambda: get_top_influence_stakeholders(db, limit=8, days=min(days, 30)))
timed("get_emerging_stakeholders", lambda: get_emerging_stakeholders(db, limit=5, days=min(days, 30)))

db.close()
print("=" * 70)
print("  PROFILING COMPLETE")
print("=" * 70)
