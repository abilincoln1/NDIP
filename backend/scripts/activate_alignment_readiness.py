"""
NDIP V6.0A Phase B/C -- Activate Opportunity Alignment & Readiness Engines

Runs compute_and_store_opportunity_alignment() and
compute_and_store_readiness() against every currently-tracked
OpportunityAssessment in the live database, since the audit confirmed
both have existed as code but never actually written a row.

This is activation, not new architecture -- it calls existing functions
built and unit-tested earlier; this script's only job is to actually
invoke them against real production data and print live evidence of
what was created.

Run: docker exec agora-backend-1 python scripts/activate_alignment_readiness.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.models import OpportunityAssessment, OpportunityAlignmentScore, OpportunityReadinessAssessment
from app.services.opportunity_intelligence import compute_and_store_opportunity_alignment, compute_and_store_readiness


def main():
    print("=" * 70)
    print("  NDIP V6.0A Phase B/C -- Alignment & Readiness Activation")
    print("=" * 70)
    db = SessionLocal()
    try:
        opportunities = db.query(OpportunityAssessment).all()
        print(f"\n  Found {len(opportunities)} tracked OpportunityAssessment rows to activate against.\n")

        if not opportunities:
            print("  No opportunities exist yet -- nothing to activate. Run opportunity")
            print("  detection first (generate_opportunity_assessments) before this script.")
            return

        for opp in opportunities:
            print(f"  --- Opportunity #{opp.id}: {opp.title} ({opp.category}) ---")

            before_align = db.query(OpportunityAlignmentScore).filter(OpportunityAlignmentScore.opportunity_id == opp.id).count()
            alignment_results = compute_and_store_opportunity_alignment(db, opp.id)
            after_align = db.query(OpportunityAlignmentScore).filter(OpportunityAlignmentScore.opportunity_id == opp.id).count()
            print(f"    Alignment: {before_align} rows before -> {after_align} rows after this run")
            for r in alignment_results:
                print(f"      {r['stakeholder_name']:45s} alignment={r['alignment_score']:6.1f}  {r['classification']}")

            before_ready = db.query(OpportunityReadinessAssessment).filter(OpportunityReadinessAssessment.opportunity_id == opp.id).count()
            readiness = compute_and_store_readiness(db, opp.id)
            after_ready = db.query(OpportunityReadinessAssessment).filter(OpportunityReadinessAssessment.opportunity_id == opp.id).count()
            print(f"    Readiness: {before_ready} rows before -> {after_ready} rows after this run")
            print(f"      readiness_score={readiness['readiness_score']:.1f}  label={readiness['readiness_label']}")
            print(f"      stakeholder_readiness={readiness['stakeholder_readiness']:.1f}  "
                  f"policy_environment={readiness['policy_environment']:.1f}  "
                  f"funding_environment={readiness['funding_environment']:.1f}")
            print()

        # Final live tallies -- the actual proof, queried fresh after all activity above
        total_alignment = db.query(OpportunityAlignmentScore).count()
        total_readiness = db.query(OpportunityReadinessAssessment).count()
        print("=" * 70)
        print(f"  LIVE DATABASE EVIDENCE (queried after activation):")
        print(f"    OpportunityAlignmentScore total rows:      {total_alignment}")
        print(f"    OpportunityReadinessAssessment total rows: {total_readiness}")
        print("=" * 70)
    finally:
        db.close()


if __name__ == "__main__":
    main()
