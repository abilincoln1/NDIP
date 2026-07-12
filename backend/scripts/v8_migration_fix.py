"""
NDIP V8 — Migration fix for schema-corrected items
Fixes the 3 failed migrations from the initial run.
"""
import sys
sys.path.insert(0, '/app')
from sqlalchemy import text
from app.db.database import engine

FIXES = [
    ("Deduplicate opportunity_alignment_scores (correct columns)", """
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'opportunity_alignment_scores') THEN
                DELETE FROM opportunity_alignment_scores a
                USING opportunity_alignment_scores b
                WHERE a.id < b.id
                  AND a.stakeholder_id = b.stakeholder_id
                  AND a.opportunity_id = b.opportunity_id;
            END IF;
        END $$;
    """),
    ("Add UNIQUE constraint on opportunity_alignment_scores (opportunity_id)", """
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'opportunity_alignment_scores')
            AND NOT EXISTS (SELECT FROM pg_constraint WHERE conname = 'uq_opp_alignment_stakeholder_opp') THEN
                ALTER TABLE opportunity_alignment_scores
                ADD CONSTRAINT uq_opp_alignment_stakeholder_opp
                UNIQUE (stakeholder_id, opportunity_id);
            END IF;
        END $$;
    """),
    ("Add performance index on normalised_posts (correct column: ingested_at exists there)", """
        CREATE INDEX IF NOT EXISTS idx_normalised_posts_ingested
            ON normalised_posts (ingested_at DESC)
            WHERE ingested_at IS NOT NULL;
    """),
    ("Add performance index on social_posts using fetched_at", """
        CREATE INDEX IF NOT EXISTS idx_social_posts_fetched
            ON social_posts (fetched_at DESC)
            WHERE fetched_at IS NOT NULL;
    """),
    ("Add narrative index on normalised_posts", """
        CREATE INDEX IF NOT EXISTS idx_normalised_posts_narrative
            ON normalised_posts (narrative_tags, ingested_at DESC)
            WHERE narrative_tags IS NOT NULL;
    """),
]

print("NDIP V8 — Migration Fix (schema-corrected)")
print("=" * 50)
with engine.connect() as conn:
    for name, sql in FIXES:
        try:
            conn.execute(text(sql))
            conn.commit()
            print(f"  ✓ {name}")
        except Exception as e:
            conn.rollback()
            msg = str(e)[:100]
            if "already exists" in msg:
                print(f"  ~ {name} (already applied)")
            else:
                print(f"  ✗ {name}: {msg}")
print("=" * 50)
print("Migration fix complete.")
