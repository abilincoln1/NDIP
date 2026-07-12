"""
Fix _get_narrative_analysis_from_materialised to read only the most
recent date_bucket rather than all rows from the last 25 hours.
Confirmed root cause: with 2 ingest runs, 22 rows exist (11 per run),
causing get_narrative_analysis to return 44 results and downstream
code (generate_watchlist) to slow significantly.

Run: docker exec agora-backend-1 python scripts/v62_fix_narrative_dedup.py
"""
PATH = "/app/app/analytics/strategic_narratives.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''        rows = db.query(NarrativeTrend).filter(
            NarrativeTrend.created_at >= cutoff
        ).order_by(NarrativeTrend.mention_count.desc()).all()
        if not rows:
            return None'''

new = '''        # Find the most recent date_bucket and read ONLY those rows,
        # not all rows from the last 25h (which accumulate across
        # multiple ingest runs and cause duplicate narrative entries).
        from sqlalchemy import func
        latest_bucket = db.query(func.max(NarrativeTrend.date_bucket)).filter(
            NarrativeTrend.created_at >= cutoff
        ).scalar()
        if not latest_bucket:
            return None
        rows = db.query(NarrativeTrend).filter(
            NarrativeTrend.date_bucket == latest_bucket
        ).order_by(NarrativeTrend.mention_count.desc()).all()
        if not rows:
            return None'''

count = content.count(old)
print(f"Anchor found {count} time(s).")
if count != 1:
    print("Aborting.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched: narrative read now uses latest date_bucket only.")
