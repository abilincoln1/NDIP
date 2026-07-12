"""
Fix source platform names in normalised_posts.
Extracts real platform from query_tag prefix (e.g. "punch_nigeria:query" -> "punch_nigeria")
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import SessionLocal
from app.models.models import NormalisedPost
from sqlalchemy import text

db = SessionLocal()

# Update source_platform from query_tag prefix for RSS sources
result = db.execute(text("""
    UPDATE normalised_posts
    SET source_platform = SPLIT_PART(query_tag, ':', 1)
    WHERE query_tag LIKE '%:%'
    AND source_platform = 'news'
    AND SPLIT_PART(query_tag, ':', 1) NOT IN ('http', 'https', '')
    AND LENGTH(SPLIT_PART(query_tag, ':', 1)) > 2
"""))
db.commit()
print(f"Updated {result.rowcount} records with correct source platform names")

# Show platform distribution
rows = db.execute(text("""
    SELECT source_platform, COUNT(*) as cnt
    FROM normalised_posts
    GROUP BY source_platform
    ORDER BY cnt DESC
    LIMIT 20
""")).fetchall()

print("\nSource platform distribution:")
for row in rows:
    print(f"  {row[0]}: {row[1]}")

db.close()
print("\nDone")
