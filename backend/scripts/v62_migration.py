"""
NDIP V6.2 -- Stakeholder Intelligence & Engagement System (SIES)
Schema Migration. Postgres-safe, idempotent, additive-only.

Per the approved execution-safe spec:
- No inspect(engine) or Base.metadata.create_all() used for DDL.
- All ALTER TABLE / CREATE TABLE wrapped in IF NOT EXISTS guards.
- No destructive operations.
- source_legacy_id included on stakeholder_engagements per the
  identity/idempotency rule, even though OutcomeChainLink is confirmed
  empty (0 rows) at migration time -- forward-looking insurance only,
  no backfill is run because there is nothing to backfill.

Run: docker exec agora-backend-1 python scripts/v62_migration.py
"""
import sys
sys.path.insert(0, '/app')

from app.db.database import engine
from sqlalchemy import text

MIGRATION_SQL = """
-- stakeholder_registry.stakeholder_type
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'stakeholder_registry' AND column_name = 'stakeholder_type'
    ) THEN
        ALTER TABLE stakeholder_registry ADD COLUMN stakeholder_type VARCHAR(40);
        CREATE INDEX IF NOT EXISTS ix_stakeholder_registry_type ON stakeholder_registry (stakeholder_type);
    END IF;
END $$;

-- stakeholder_relationships.strength
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'stakeholder_relationships' AND column_name = 'strength'
    ) THEN
        ALTER TABLE stakeholder_relationships ADD COLUMN strength FLOAT;
    END IF;
END $$;

-- stakeholder_relationships.confidence
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'stakeholder_relationships' AND column_name = 'confidence'
    ) THEN
        ALTER TABLE stakeholder_relationships ADD COLUMN confidence VARCHAR(10);
    END IF;
END $$;

-- stakeholder_engagements (new table)
CREATE TABLE IF NOT EXISTS stakeholder_engagements (
    id SERIAL PRIMARY KEY,
    stakeholder_id INTEGER REFERENCES stakeholder_registry(id),
    opportunity_id INTEGER REFERENCES opportunity_assessments(id),
    recommendation_id INTEGER REFERENCES recommendation_records(id),
    event_type VARCHAR(30) NOT NULL,
    event_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    description TEXT,
    recorded_by VARCHAR(150),
    source_legacy_id VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_engagement_stakeholder_event ON stakeholder_engagements (stakeholder_id, event_type);
CREATE INDEX IF NOT EXISTS ix_engagement_recommendation ON stakeholder_engagements (recommendation_id);
CREATE INDEX IF NOT EXISTS ix_engagement_legacy_id ON stakeholder_engagements (source_legacy_id);

-- Identity constraint per spec Section 3: prevents duplicate event
-- generation for the same legacy row + event type combination.
-- NULLs (live, non-legacy writes) do not conflict with each other or
-- with any other NULL under Postgres unique-constraint semantics --
-- this is the correct, intended behaviour for rows 1-2 of the adapter
-- table (live writes via the route), which always have
-- source_legacy_id = NULL.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_engagement_legacy_event'
    ) THEN
        ALTER TABLE stakeholder_engagements
        ADD CONSTRAINT uq_engagement_legacy_event UNIQUE (source_legacy_id, event_type);
    END IF;
END $$;

-- stakeholder_watchlist (new table)
CREATE TABLE IF NOT EXISTS stakeholder_watchlist (
    id SERIAL PRIMARY KEY,
    stakeholder_id INTEGER NOT NULL REFERENCES stakeholder_registry(id),
    event_type VARCHAR(30) NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    description TEXT,
    source VARCHAR(100)
);
"""


def main():
    print("=" * 70)
    print("  NDIP V6.2 MIGRATION -- Stakeholder Intelligence & Engagement System")
    print("=" * 70)

    # Pre-check, per spec Section 11 / validation requirements: re-verify
    # OutcomeChainLink is still empty immediately before migrating, not
    # trusted from an earlier check in this conversation.
    from app.db.database import SessionLocal
    from app.models.models import OutcomeChainLink
    db = SessionLocal()
    pre_count = db.query(OutcomeChainLink).count()
    db.close()
    print(f"\n  PRE-CHECK: OutcomeChainLink row count = {pre_count}")
    if pre_count != 0:
        print("  WARNING: OutcomeChainLink is non-empty. This migration's adapter")
        print("  layer assumes an empty legacy table and does NOT include a backfill")
        print("  step. Proceeding with schema changes only; do not enable the new")
        print("  write-redirect routes until a tested backfill is written.")
    else:
        print("  Confirmed empty -- no backfill required, proceeding.")

    print("\n  Applying migration SQL...")
    with engine.connect() as conn:
        conn.execute(text(MIGRATION_SQL))
        conn.commit()
    print("  Migration SQL applied successfully.")

    # Post-check: confirm everything exists, queried fresh from
    # information_schema, not assumed from the SQL having run without error.
    print("\n  POST-CHECK: verifying schema via live information_schema query...")
    with engine.connect() as conn:
        cols = conn.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'stakeholder_registry' AND column_name = 'stakeholder_type'"
        )).fetchall()
        print(f"  stakeholder_registry.stakeholder_type: {cols}")

        cols = conn.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'stakeholder_relationships' AND column_name IN ('strength', 'confidence')"
        )).fetchall()
        print(f"  stakeholder_relationships new columns: {cols}")

        tables = conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name IN ('stakeholder_engagements', 'stakeholder_watchlist')"
        )).fetchall()
        print(f"  New tables present: {tables}")

        constraint = conn.execute(text(
            "SELECT conname FROM pg_constraint WHERE conname = 'uq_engagement_legacy_event'"
        )).fetchall()
        print(f"  Unique constraint present: {constraint}")

    print("\n" + "=" * 70)
    print("  MIGRATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
