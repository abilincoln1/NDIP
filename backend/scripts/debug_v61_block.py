"""
Diagnostic: reproduce the V6.0 block followed immediately by the V6.1 block,
exactly as leadership_pack.py runs them in sequence, to test whether the
V6.0 stakeholder registry call (which writes StakeholderProfile rows) is
somehow affecting the V6.1 stakeholder influence call that runs right after it.

Run: docker exec agora-backend-1 python scripts/debug_v61_block.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal

db = SessionLocal()
days = 7

print("--- V6.0 block (as in leadership_pack.py) ---")
try:
    from app.services.opportunity_intelligence import get_top_opportunities, get_opportunity_pipeline_summary
    from app.services.stakeholder_registry import get_top_stakeholders

    strategic_opportunities = get_top_opportunities(db, limit=5)
    print("strategic_opportunities:", len(strategic_opportunities))
    key_stakeholders = get_top_stakeholders(db, limit=8, days=min(days, 30))
    print("key_stakeholders:", len(key_stakeholders))
    engagement_priorities = [
        s for s in key_stakeholders if s.get("monitoring_priority") in ("High", "Critical")
    ][:5]
    print("engagement_priorities:", len(engagement_priorities))
    opportunity_pipeline = get_opportunity_pipeline_summary(db)
    print("opportunity_pipeline:", opportunity_pipeline)
except Exception as e:
    print("V6.0 BLOCK FAILED:", type(e).__name__, e)
    import traceback
    traceback.print_exc()

print("\n--- V6.1 block (as in leadership_pack.py), same session, right after ---")
try:
    from app.services.stakeholder_influence import get_top_influence_stakeholders, get_emerging_stakeholders
    stakeholder_influence_summary = get_top_influence_stakeholders(db, limit=8, days=min(days, 30))
    print("stakeholder_influence_summary:", len(stakeholder_influence_summary))
    emerging_stakeholders = get_emerging_stakeholders(db, limit=5, days=min(days, 30))
    print("emerging_stakeholders:", len(emerging_stakeholders))
except Exception as e:
    print("V6.1 BLOCK FAILED:", type(e).__name__, e)
    import traceback
    traceback.print_exc()

db.close()
