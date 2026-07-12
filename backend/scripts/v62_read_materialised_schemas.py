"""
NDIP V6.2 -- Read the real schemas of the three materialised tables and
the real ingest pipeline entry point before designing any changes.

Run: docker exec agora-backend-1 python scripts/v62_read_materialised_schemas.py
"""
import sys
sys.path.insert(0, '/app')

from sqlalchemy import text
from app.db.database import SessionLocal

db = SessionLocal()

for table in ["narrative_trends", "stakeholder_influence_profiles", "stakeholder_momentum_snapshots"]:
    print(f"\n{'='*70}")
    print(f"  SCHEMA: {table}")
    print(f"{'='*70}")
    result = db.execute(text("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = :table
        ORDER BY ordinal_position
    """), {"table": table})
    for row in result:
        nullable = "" if row[2] == "YES" else " NOT NULL"
        default = f" DEFAULT {row[3]}" if row[3] else ""
        print(f"  {row[0]}: {row[1]}{nullable}{default}")

db.close()
