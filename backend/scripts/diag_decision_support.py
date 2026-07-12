import sys; sys.path.insert(0,'/app')
from app.db.database import SessionLocal
from app.services.decision_support import generate_decision_support
import app.services.decision_support as ds_module

db = SessionLocal()

# Replace the tracking function with a version that doesn't swallow exceptions
def debug_enrich(db, result, days):
    from app.services.recommendation_tracker import record_recommendation
    horizon_map = {
        'immediate_actions': '7 days', 'near_term_actions': '30 days',
        'strategic_actions': '90 days', 'monitoring_actions': 'Ongoing'
    }
    for bucket, horizon in horizon_map.items():
        for action in result.get(bucket, []):
            print('--- Action ---')
            print('Keys:', list(action.keys()))
            print('Category:', action.get('category'))
            print('Priority:', action.get('priority'))
            try:
                rec = record_recommendation(
                    db,
                    narrative=action.get('narrative'),
                    recommendation_text=action.get('action', ''),
                    category=action.get('category', 'MONITOR'),
                    priority=action.get('priority', 'Medium'),
                    confidence='Medium',
                    time_horizon=horizon,
                    supporting_evidence=action.get('reasoning') or action.get('evidence', ''),
                    expected_outcome=action.get('expected_outcome'),
                    trigger_metric_name='share_of_voice',
                    trigger_metric_value=None,
                    period_days=days,
                )
                print('SUCCESS - Recorded ID:', rec.id)
            except Exception as e:
                print('FAILED WITH ERROR:', type(e).__name__, str(e))
                import traceback
                traceback.print_exc()

ds_module._enrich_and_track_recommendations = debug_enrich
result = generate_decision_support(db, 7)
print('\nDone. Total actions in result:', result.get('total_actions'))
db.close()
