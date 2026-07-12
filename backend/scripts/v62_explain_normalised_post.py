"""
NDIP V6.2 -- EXPLAIN ANALYZE specifically for the two NormalisedPost
scans that are the core of get_narrative_analysis(), the most expensive
remaining operation at ~3.4s per call.

Run: docker exec agora-backend-1 python scripts/v62_explain_normalised_post.py
"""
import sys
sys.path.insert(0, '/app')

from sqlalchemy import text
from app.db.database import SessionLocal
from datetime import datetime, timezone, timedelta

db = SessionLocal()
now = datetime.now(timezone.utc)
days = 30
since = now - timedelta(days=days)
prev_since = since - timedelta(days=days)


def explain(label, sql, params=None):
    print(f"\n{'='*70}")
    print(f"  QUERY: {label}")
    print(f"{'='*70}")
    try:
        result = db.execute(text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {sql}"), params or {})
        for row in result:
            print(row[0])
    except Exception as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        db.rollback()


# First: confirm real table name
result = db.execute(text("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name
"""))
print("Real table names in public schema:")
for row in result:
    print(f"  {row[0]}")

explain("NormalisedPost -- current period full scan (narrative analysis core)",
    """SELECT published_at, source_platform, narrative_category, sentiment_score, text
       FROM normalised_posts
       WHERE published_at >= :since
         AND nlp_processed = true
         AND text IS NOT NULL""",
    {"since": since})

explain("NormalisedPost -- previous period scan (momentum)",
    """SELECT published_at, source_platform, narrative_category, sentiment_score, text
       FROM normalised_posts
       WHERE published_at >= :prev_since
         AND published_at < :since
         AND nlp_processed = true
         AND text IS NOT NULL""",
    {"since": since, "prev_since": prev_since})

explain("NormalisedPost -- count by table (size check)",
    "SELECT COUNT(*) FROM normalised_posts")

db.close()
print("\nDone.")
