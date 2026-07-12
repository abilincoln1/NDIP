"""
NDIP V6.2 Phase A -- Complete Index Audit, fixed SQL using correct
PostgreSQL system catalogs.

Run: docker exec agora-backend-1 python scripts/v62_index_audit_v2.py
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
    "stakeholder_watchlist",
]

for table in tables:
    print(f"\n{'='*70}")
    print(f"  TABLE: {table}")
    print(f"{'='*70}")

    try:
        count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        print(f"  Row count: {count:,}")
    except Exception as e:
        print(f"  Row count: FAILED ({e})")
        db.rollback()
        continue

    try:
        size = db.execute(text(
            f"SELECT pg_size_pretty(pg_total_relation_size('{table}'))"
        )).scalar()
        print(f"  Total size (table + indexes): {size}")
    except Exception:
        pass

    try:
        result = db.execute(text("""
            SELECT
                i.relname AS index_name,
                pg_size_pretty(pg_relation_size(i.oid)) AS index_size,
                ix.indisunique AS is_unique,
                ix.indisprimary AS is_primary,
                pg_get_indexdef(i.oid) AS index_def
            FROM pg_class t
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            WHERE t.relname = :table
            ORDER BY i.relname
        """), {"table": table})
        indexes = list(result)
        print(f"  Indexes ({len(indexes)}):")
        for idx in indexes:
            flags = []
            if idx[2]: flags.append("UNIQUE")
            if idx[3]: flags.append("PK")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            print(f"    {idx[0]} ({idx[1]}){flag_str}: {idx[4]}")
    except Exception as e:
        print(f"  Index query FAILED: {e}")
        db.rollback()

db.close()
print(f"\n{'='*70}")
print("  INDEX AUDIT COMPLETE")
print(f"{'='*70}")
