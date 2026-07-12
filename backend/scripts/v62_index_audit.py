"""
NDIP V6.2 Phase A -- Complete Index Audit across all 8 named tables plus
additional tables identified from the live schema listing.

Run: docker exec agora-backend-1 python scripts/v62_index_audit.py
"""
import sys
sys.path.insert(0, '/app')

from sqlalchemy import text
from app.db.database import SessionLocal

db = SessionLocal()

tables = [
    "normalised_posts",
    "stakeholder_registry",
    "stakeholder_relationships",
    "recommendation_records",
    "opportunity_assessments",
    "opportunity_alignment_scores",
    "named_entities",
    "stakeholder_engagements",
    "stakeholder_influence_profiles",
    "stakeholder_momentum_snapshots",
    "narrative_trends",
]

for table in tables:
    print(f"\n{'='*70}")
    print(f"  TABLE: {table}")
    print(f"{'='*70}")

    # Row count
    try:
        result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
        count = result.scalar()
        print(f"  Row count: {count:,}")
    except Exception as e:
        print(f"  Row count: FAILED ({e})")
        db.rollback()
        continue

    # Existing indexes
    result = db.execute(text("""
        SELECT indexname, indexdef,
               pg_size_pretty(pg_relation_size(indexrelid)) as index_size
        FROM pg_indexes
        JOIN pg_class ON pg_class.relname = pg_indexes.indexname
        WHERE tablename = :table
        ORDER BY indexname
    """), {"table": table})
    indexes = list(result)
    print(f"  Existing indexes ({len(indexes)}):")
    for idx in indexes:
        print(f"    {idx[0]} ({idx[2]}): {idx[1]}")

    # Table size
    try:
        result = db.execute(text(f"SELECT pg_size_pretty(pg_total_relation_size('{table}'))"))
        size = result.scalar()
        print(f"  Total table size: {size}")
    except Exception:
        pass

db.close()
print(f"\n{'='*70}")
print("  INDEX AUDIT COMPLETE")
print(f"{'='*70}")
