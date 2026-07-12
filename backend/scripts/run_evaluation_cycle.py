#!/usr/bin/env python3
"""
NDIP V5.6 — Daily Recommendation Evaluation Cycle
Run: docker exec agora-backend-1 python scripts/run_evaluation_cycle.py
Should be scheduled to run daily alongside daily_ingest.py.

Evaluates all OPEN recommendations that are at least 7 days old against
current discourse data, updating their status (VALIDATED / PARTIALLY_VALIDATED /
INVALIDATED / UNDER_REVIEW) and computing outcome scores.
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.services.recommendation_tracker import run_evaluation_cycle, compute_decision_quality_metrics


def main():
    db = SessionLocal()
    try:
        print("=" * 60)
        print("  NDIP V5.6 — Recommendation Evaluation Cycle")
        print("=" * 60)

        result = run_evaluation_cycle(db)

        print(f"\n  Eligible for evaluation: {result['eligible_found']}")
        print(f"  Evaluated this cycle:    {result['evaluated_this_cycle']}")
        print(f"    Validated:             {result['validated']}")
        print(f"    Partially validated:   {result['partially_validated']}")
        print(f"    Invalidated:           {result['invalidated']}")
        print(f"    Under review:          {result['under_review']}")

        print("\n  Platform-wide decision quality metrics:")
        metrics = compute_decision_quality_metrics(db)
        print(f"    Recommendations generated:  {metrics['recommendations_generated']}")
        print(f"    Recommendations evaluated:  {metrics['recommendations_evaluated']}")
        print(f"    Average accuracy:           {metrics['average_accuracy']}%" if metrics['average_accuracy'] is not None else "    Average accuracy:           N/A (no evaluated recommendations yet)")
        print(f"    Forecast accuracy:          {metrics['forecast_accuracy']}%" if metrics['forecast_accuracy'] is not None else "    Forecast accuracy:          N/A")

        print("\n" + "=" * 60)
        print("  Evaluation cycle complete")
        print("=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    main()
