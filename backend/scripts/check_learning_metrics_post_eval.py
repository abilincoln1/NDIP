"""
Post-Phase-D check: confirm the learning cycle's metrics actually moved
now that 16 real evaluations exist, versus the all-None state from the
original audit.

Run: docker exec agora-backend-1 python scripts/check_learning_metrics_post_eval.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.services.intelligence_learning import run_intelligence_learning_cycle

db = SessionLocal()
cycle = run_intelligence_learning_cycle(db)

print("platform_learning_score:", cycle.get("platform_learning_score"))
dq = cycle.get("decision_quality_metrics") or {}
print("recommendations_generated:", dq.get("recommendations_generated"))
print("recommendations_evaluated:", dq.get("recommendations_evaluated"))
print("validated_count:", dq.get("validated_count"))
print("partially_validated_count:", dq.get("partially_validated_count"))
print("invalidated_count:", dq.get("invalidated_count"))
print("under_review_count:", dq.get("under_review_count"))
print("average_accuracy:", dq.get("average_accuracy"))
print("evaluation_rate:", dq.get("evaluation_rate"))
print()
print("module_breakdown:")
for module, stats in (dq.get("module_breakdown") or {}).items():
    print(f"  {module}: generated={stats.get('generated')} evaluated={stats.get('evaluated')} accuracy={stats.get('accuracy')}")
print()
print("lessons_learned:")
for lesson in (cycle.get("lessons_learned") or []):
    print(" -", lesson.get("lesson") if isinstance(lesson, dict) else lesson)

db.close()
