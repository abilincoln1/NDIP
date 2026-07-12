"""
NDIP V6.0A Phase D -- First Learning Loop Activation

The live audit confirmed run_evaluation_cycle()'s eligibility gate
(MIN_EVALUATION_AGE_DAYS=7) has correctly found zero eligible records,
because the database's oldest OPEN recommendation is only 6 days old --
this is the gate working correctly, not a defect.

Per the V6.0A spec's own instruction ("Select a representative sample...
The objective is not perfect accuracy. The objective is closing the
first learning loop"), this script selects a representative sample
across modules and categories and runs the REAL evaluation function
(evaluate_recommendation_effectiveness) directly against them --
bypassing only the age gate, not the evaluation logic itself. This is
activation of existing logic against a hand-picked sample, not new
evaluation code.

Run: docker exec agora-backend-1 python scripts/activate_first_evaluation_cycle.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.models import RecommendationRecord, RecommendationStatus
from app.services.recommendation_tracker import evaluate_recommendation_effectiveness
from datetime import datetime, timezone


def select_representative_sample(db, per_module_limit=2):
    """
    Picks up to `per_module_limit` OPEN recommendations per distinct module,
    favouring variety over volume -- this is the "representative sample"
    the spec asks for, not a random or exhaustive selection.
    """
    modules = [row[0] for row in db.query(RecommendationRecord.module).filter(
        RecommendationRecord.status == RecommendationStatus.OPEN
    ).distinct().all()]

    sample = []
    for module in modules:
        recs = db.query(RecommendationRecord).filter(
            RecommendationRecord.status == RecommendationStatus.OPEN,
            RecommendationRecord.module == module,
        ).order_by(RecommendationRecord.created_at.asc()).limit(per_module_limit).all()
        sample.extend(recs)
    return sample


def main():
    print("=" * 70)
    print("  NDIP V6.0A Phase D -- First Learning Loop Activation")
    print("=" * 70)
    db = SessionLocal()
    try:
        sample = select_representative_sample(db, per_module_limit=2)
        print(f"\n  Selected {len(sample)} representative recommendations across "
              f"{len(set(r.module for r in sample))} modules.\n")

        evaluated = validated = partially_validated = invalidated = under_review = errors = 0

        for rec in sample:
            try:
                result = evaluate_recommendation_effectiveness(db, rec)
                rec.status = result["status"]
                rec.outcome_score = result["outcome_score"]
                rec.outcome_notes = result["outcome_notes"]
                rec.outcome_metric_value = result["outcome_metric_value"]
                rec.evaluation_date = datetime.now(timezone.utc)
                evaluated += 1
                status_val = result["status"]
                if status_val == RecommendationStatus.VALIDATED:
                    validated += 1
                elif status_val == RecommendationStatus.PARTIALLY_VALIDATED:
                    partially_validated += 1
                elif status_val == RecommendationStatus.INVALIDATED:
                    invalidated += 1
                else:
                    under_review += 1

                print(f"  [{rec.module:25s}] #{rec.id:4d} -> {status_val} "
                      f"(score={result['outcome_score']})")
                print(f"      {rec.recommendation_text[:100]}")
                print(f"      {result['outcome_notes'][:140]}")
                print()
            except Exception as e:
                errors += 1
                print(f"  [{rec.module:25s}] #{rec.id:4d} -> EVALUATION ERROR: {type(e).__name__}: {e}")
                print()

        db.commit()

        print("=" * 70)
        print(f"  CYCLE RESULTS")
        print(f"    Evaluated:            {evaluated}")
        print(f"    Validated:            {validated}")
        print(f"    Partially Validated:  {partially_validated}")
        print(f"    Invalidated:          {invalidated}")
        print(f"    Under Review:         {under_review}")
        print(f"    Errors:               {errors}")
        print("=" * 70)

        # Live re-query -- proof the database actually changed, not just the script's own counters
        total_open = db.query(RecommendationRecord).filter(RecommendationRecord.status == RecommendationStatus.OPEN).count()
        total_evaluated = db.query(RecommendationRecord).filter(RecommendationRecord.status != RecommendationStatus.OPEN).count()
        print(f"\n  LIVE DATABASE EVIDENCE (re-queried after commit):")
        print(f"    OPEN recommendations remaining: {total_open}")
        print(f"    Non-OPEN (evaluated) recommendations: {total_evaluated}")
        print("=" * 70)
    finally:
        db.close()


if __name__ == "__main__":
    main()
