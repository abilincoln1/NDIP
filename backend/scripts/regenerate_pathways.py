"""
Force-regenerate engagement pathways for both real opportunities, since
get_current_pathway() correctly returns an already-existing "current"
pathway rather than regenerating it -- meaning the pathway-ordering fix
in generate_engagement_pathway() cannot take effect until the stale,
pre-fix pathway rows (created by the first activation run, before the
fix existed) are superseded by a fresh call to generate_engagement_pathway
directly (not get_current_pathway, which would just return the stale one
again).

Run: docker exec agora-backend-1 python scripts/regenerate_pathways.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.models import OpportunityAssessment
from app.services.opportunity_intelligence import generate_engagement_pathway, generate_execution_plan

db = SessionLocal()
try:
    opportunities = db.query(OpportunityAssessment).all()
    for opp in opportunities:
        print(f"--- Regenerating pathway for #{opp.id}: {opp.title} ---")
        pathway = generate_engagement_pathway(db, opp.id)
        for step in pathway["steps"]:
            print(f"  {step['step_number']}. {step['description']}")
        print()

    print("=" * 70)
    print("  Re-running full execution plans with regenerated pathways")
    print("=" * 70)
    for opp in opportunities:
        plan = generate_execution_plan(db, opp.id)
        print(f"\n--- Opportunity #{opp.id}: {opp.title} ---")
        print("  Who matters? (ranked):")
        for s in plan["required_stakeholders"]:
            print(f"    - {s['name']} ({s['classification']}, alignment={s['alignment_score']})")
        print("  Engagement Sequence (first two steps):")
        for step in plan["recommended_engagement_sequence"][:2]:
            print(f"    {step['step_number']}. {step['description']}")
finally:
    db.close()
