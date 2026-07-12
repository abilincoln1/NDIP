"""
NDIP V6.2 -- EXPLAIN ANALYZE for normalised_posts with real column names.

Run: docker exec agora-backend-1 python scripts/v62_explain_normalised_post_v2.py
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

# First get real columns
print("normalised_posts columns:")
result = db.execute(text("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'normalised_posts'
    ORDER BY ordinal_position
"""))
cols = list(result)
for row in cols:
    print(f"  {row[0]}: {row[1]}")

print("\nnormalised_posts indexes:")
result = db.execute(text("""
    SELECT indexname, indexdef
    FROM pg_indexes
    WHERE tablename = 'normalised_posts'
"""))
for row in result:
    print(f"  {row[0]}: {row[1]}")

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

# Use minimal columns matching the real ORM query
explain("NormalisedPost -- current 30d scan (what get_narrative_analysis actually runs)",
    """SELECT id, text, published_at, source_platform
       FROM normalised_posts
       WHERE published_at >= :since
         AND nlp_processed = true
         AND text IS NOT NULL""",
    {"since": since})

explain("NormalisedPost -- previous 30d scan (momentum calculation)",
    """SELECT id, text, published_at, source_platform
       FROM normalised_posts
       WHERE published_at >= :prev_since
         AND published_at < :since
         AND nlp_processed = true
         AND text IS NOT NULL""",
    {"since": since, "prev_since": prev_since})

db.close()
print("\nDone.")
