#!/usr/bin/env python3
"""
NDIP V5.8 — One-time migration: add the 'module' column to the existing
recommendation_records table.

Base.metadata.create_all() only creates tables that don't yet exist — it
never alters existing tables to add new columns. Since recommendation_records
was created in V5.6 (before the 'module' field existed), this explicit
ALTER TABLE is required for V5.8's RecommendationRecord.module field to work.

Run: docker exec agora-backend-1 python scripts/migrate_add_module_column.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import engine
from sqlalchemy import text, inspect


def main():
    print("=" * 60)
    print("  NDIP V5.8 — Migration: add 'module' column")
    print("=" * 60)

    inspector = inspect(engine)
    existing_columns = [c["name"] for c in inspector.get_columns("recommendation_records")]

    if "module" in existing_columns:
        print("\n  Column 'module' already exists — no migration needed.")
        return

    print(f"\n  Current columns: {existing_columns}")
    print("  Adding 'module' column (VARCHAR(50), default 'decision_support')...")

    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE recommendation_records "
            "ADD COLUMN module VARCHAR(50) DEFAULT 'decision_support'"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_recommendation_records_module "
            "ON recommendation_records (module)"
        ))
        conn.commit()

    # Verify
    inspector = inspect(engine)
    updated_columns = [c["name"] for c in inspector.get_columns("recommendation_records")]
    if "module" in updated_columns:
        print("\n  SUCCESS: 'module' column added and indexed.")

        # Backfill existing rows that have NULL module (shouldn't happen given the
        # DEFAULT, but Postgres only applies DEFAULT to new rows in some versions
        # for ALTER TABLE ADD COLUMN — verify and backfill defensively)
        from app.db.database import SessionLocal
        from app.models.models import RecommendationRecord
        db = SessionLocal()
        try:
            null_count = db.query(RecommendationRecord).filter(
                RecommendationRecord.module.is_(None)
            ).count()
            if null_count > 0:
                db.query(RecommendationRecord).filter(
                    RecommendationRecord.module.is_(None)
                ).update({"module": "decision_support"})
                db.commit()
                print(f"  Backfilled {null_count} existing row(s) with module='decision_support'")
            else:
                print("  No existing rows needed backfilling (DEFAULT applied correctly).")
        finally:
            db.close()
    else:
        print("\n  ERROR: column still not present after ALTER TABLE — investigate manually.")

    print("\n" + "=" * 60)
    print("  Migration complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
