"""Add an entry-point print to confirm the function is even being called."""
path = '/app/app/services/decision_support.py'
c = open(path).read()

old = '''def _enrich_and_track_recommendations(db: Session, result: dict, days: int) -> None:
    """
    V5.6 Phase A + B: add explicit time_horizon/confidence fields to every
    recommendation (specificity requirement) and persist each one to the
    RecommendationRecord table for automated effectiveness evaluation.
    """
    try:
        from app.services.recommendation_tracker import record_recommendation
    except Exception:
        return  # tracker not available — degrade gracefully, decision support still works'''

new = '''def _enrich_and_track_recommendations(db: Session, result: dict, days: int) -> None:
    """
    V5.6 Phase A + B: add explicit time_horizon/confidence fields to every
    recommendation (specificity requirement) and persist each one to the
    RecommendationRecord table for automated effectiveness evaluation.
    """
    print("ENTERED _enrich_and_track_recommendations, buckets:", list(result.keys()))
    try:
        from app.services.recommendation_tracker import record_recommendation
        print("Tracker import succeeded inside function")
    except Exception as e:
        print("TRACKER IMPORT FAILED:", type(e).__name__, str(e))
        return  # tracker not available — degrade gracefully, decision support still works'''

if old in c:
    c = c.replace(old, new, 1)
    open(path, 'w').write(c)
    print('Patched successfully')
else:
    print('Pattern not found — checking for partial match')
    # try just the function signature
    if 'def _enrich_and_track_recommendations' in c:
        print('Function definition exists but exact text block did not match (whitespace?)')
    else:
        print('Function definition not found at all!')
