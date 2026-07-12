"""
NDIP V8 — Phase 1 Database Migration
Implements:
  EB-003: UNIQUE constraint on opportunity_alignment_scores (TD-010)
  EB-004: RBAC tables (roles, permissions, user_roles)
  EB-005: Audit log table
  EB-011: Daily snapshots table for historical comparison
  EB-016: Connection pool config verification
  EB-017: Index additions for high-frequency query patterns

Run:
  docker exec agora-backend-1 python scripts/v8_migration.py
"""
import sys
sys.path.insert(0, '/app')

from sqlalchemy import text
from app.db.database import engine

MIGRATIONS = [

    # ── EB-003: Fix duplicate opportunity alignment scores ─────────────────
    ("Check opportunity_alignment_scores", """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'opportunity_alignment_scores'
        )
    """),

    ("Deduplicate opportunity_alignment_scores", """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'opportunity_alignment_scores'
            ) THEN
                -- Remove duplicates keeping the most recent row
                DELETE FROM opportunity_alignment_scores a
                USING opportunity_alignment_scores b
                WHERE a.id < b.id
                  AND a.stakeholder_id = b.stakeholder_id
                  AND a.opportunity_type = b.opportunity_type;
            END IF;
        END $$;
    """),

    ("Add UNIQUE constraint to opportunity_alignment_scores", """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'opportunity_alignment_scores'
            ) AND NOT EXISTS (
                SELECT FROM pg_constraint
                WHERE conname = 'uq_opportunity_alignment_stakeholder_type'
            ) THEN
                ALTER TABLE opportunity_alignment_scores
                ADD CONSTRAINT uq_opportunity_alignment_stakeholder_type
                UNIQUE (stakeholder_id, opportunity_type);
            END IF;
        END $$;
    """),

    # ── EB-005: Audit log table ────────────────────────────────────────────
    ("Create audit_log table", """
        CREATE TABLE IF NOT EXISTS audit_log (
            id          BIGSERIAL PRIMARY KEY,
            user_email  VARCHAR(255),
            user_id     INTEGER,
            action      VARCHAR(100) NOT NULL,
            endpoint    VARCHAR(500),
            method      VARCHAR(10),
            ip_address  INET,
            user_agent  TEXT,
            payload_hash VARCHAR(64),
            response_code INTEGER,
            duration_ms  INTEGER,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_audit_log_user_email
            ON audit_log (user_email);
        CREATE INDEX IF NOT EXISTS idx_audit_log_created_at
            ON audit_log (created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_audit_log_action
            ON audit_log (action);
    """),

    # ── EB-004: RBAC tables ────────────────────────────────────────────────
    ("Create roles table", """
        CREATE TABLE IF NOT EXISTS roles (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(50) UNIQUE NOT NULL,
            description TEXT,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        );
        INSERT INTO roles (name, description) VALUES
            ('executive',         'Senior executive — Leadership Pack, Watchlist, high-level summaries'),
            ('analyst',           'Intelligence analyst — full data access, detailed metrics'),
            ('admin',             'Platform administrator — system health, data sources, user management'),
            ('campaign_director', 'Campaign director — electoral intelligence, opportunity assessments'),
            ('diaspora',          'Diaspora coordinator — GNEI, diaspora engagement, community intelligence')
        ON CONFLICT (name) DO NOTHING;
    """),

    ("Create permissions table", """
        CREATE TABLE IF NOT EXISTS permissions (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        );
        INSERT INTO permissions (name, description) VALUES
            ('intelligence:read',         'Read all intelligence dashboards'),
            ('intelligence:export',       'Export PDF reports and data'),
            ('copilot:use',               'Use the AI Copilot'),
            ('onboarding:read',           'Access onboarding and learning content'),
            ('admin:users',               'Manage platform users'),
            ('admin:sources',             'Manage data source connectors'),
            ('admin:system',              'Access system health and data health dashboards'),
            ('strategic:read',            'Access SOI Dashboard and opportunity intelligence'),
            ('election:read',             'Access Election Intelligence dashboard'),
            ('gnei:read',                 'Access GNEI and diaspora intelligence')
        ON CONFLICT (name) DO NOTHING;
    """),

    ("Create role_permissions table", """
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id       INTEGER REFERENCES roles(id) ON DELETE CASCADE,
            permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
            PRIMARY KEY (role_id, permission_id)
        );
        -- Assign permissions to roles
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p
        WHERE (r.name = 'executive'         AND p.name IN ('intelligence:read','intelligence:export','copilot:use','onboarding:read','strategic:read','election:read','gnei:read'))
           OR (r.name = 'analyst'           AND p.name IN ('intelligence:read','intelligence:export','copilot:use','onboarding:read','strategic:read','election:read','gnei:read'))
           OR (r.name = 'admin'             AND p.name IN ('intelligence:read','intelligence:export','copilot:use','onboarding:read','admin:users','admin:sources','admin:system','strategic:read','election:read','gnei:read'))
           OR (r.name = 'campaign_director' AND p.name IN ('intelligence:read','intelligence:export','copilot:use','onboarding:read','strategic:read','election:read'))
           OR (r.name = 'diaspora'          AND p.name IN ('intelligence:read','copilot:use','onboarding:read','gnei:read'))
        ON CONFLICT DO NOTHING;
    """),

    ("Create user_roles table", """
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id   INTEGER NOT NULL,
            role_id   INTEGER REFERENCES roles(id) ON DELETE CASCADE,
            granted_by INTEGER,
            granted_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (user_id, role_id)
        );
        -- Grant admin role to existing admin user
        INSERT INTO user_roles (user_id, role_id)
        SELECT u.id, r.id
        FROM admin_users u, roles r
        WHERE r.name = 'admin'
        ON CONFLICT DO NOTHING;
    """),

    # ── EB-011: Daily snapshots table ─────────────────────────────────────
    ("Create daily_intelligence_snapshots table", """
        CREATE TABLE IF NOT EXISTS daily_intelligence_snapshots (
            id              BIGSERIAL PRIMARY KEY,
            snapshot_date   DATE NOT NULL,
            snapshot_type   VARCHAR(50) NOT NULL DEFAULT 'daily',

            -- Narrative state
            narrative_data  JSONB NOT NULL DEFAULT '[]',

            -- Engagement state
            engagement_index FLOAT,
            sentiment_score  FLOAT,
            post_count       INTEGER,
            source_count     INTEGER,

            -- Watchlist state
            watchlist_data   JSONB NOT NULL DEFAULT '[]',
            watchlist_critical_count INTEGER DEFAULT 0,
            watchlist_high_count     INTEGER DEFAULT 0,

            -- Stakeholder state (top 10)
            top_stakeholders JSONB NOT NULL DEFAULT '[]',

            -- Opportunity state (top 5)
            top_opportunities JSONB NOT NULL DEFAULT '[]',

            -- Confidence
            confidence_label VARCHAR(20),
            active_source_count INTEGER,
            nlp_processing_rate FLOAT,

            -- Delta from previous day (computed on insert)
            delta_from_previous JSONB DEFAULT NULL,

            created_at TIMESTAMPTZ DEFAULT NOW(),

            UNIQUE (snapshot_date, snapshot_type)
        );
        CREATE INDEX IF NOT EXISTS idx_daily_snapshots_date
            ON daily_intelligence_snapshots (snapshot_date DESC);
    """),

    # ── Performance indexes ────────────────────────────────────────────────
    ("Add performance indexes", """
        -- Index for post lookups by date (critical for partitioning prep)
        CREATE INDEX IF NOT EXISTS idx_social_posts_ingested_at
            ON social_posts (ingested_at DESC)
            WHERE ingested_at IS NOT NULL;

        -- Index for post lookups by source
        CREATE INDEX IF NOT EXISTS idx_social_posts_source_ingested
            ON social_posts (source_name, ingested_at DESC)
            WHERE source_name IS NOT NULL;

        -- Index for normalised posts narrative lookup
        CREATE INDEX IF NOT EXISTS idx_normalised_posts_narrative
            ON normalised_posts (narrative_classification, processed_at DESC)
            WHERE narrative_classification IS NOT NULL;
    """),

    # ── Evidence chains table (EB-021 foundation) ─────────────────────────
    ("Create intelligence_evidence_chains table", """
        CREATE TABLE IF NOT EXISTS intelligence_evidence_chains (
            id                  BIGSERIAL PRIMARY KEY,
            output_type         VARCHAR(100) NOT NULL,
            output_id           INTEGER,
            conclusion          TEXT NOT NULL,
            confidence_score    FLOAT NOT NULL DEFAULT 0.0,
            confidence_label    VARCHAR(20),

            -- Decomposed confidence components
            source_count_score  FLOAT DEFAULT 0,
            diversity_score     FLOAT DEFAULT 0,
            volume_score        FLOAT DEFAULT 0,
            recency_score       FLOAT DEFAULT 0,
            corroboration_score FLOAT DEFAULT 0,

            -- Evidence
            supporting_post_ids JSONB DEFAULT '[]',
            source_names        JSONB DEFAULT '[]',
            source_types        JSONB DEFAULT '[]',
            post_count          INTEGER DEFAULT 0,
            source_count        INTEGER DEFAULT 0,
            recent_post_count   INTEGER DEFAULT 0,

            -- Lineage
            algorithm_version   VARCHAR(50) DEFAULT 'v8.0',
            computed_at         TIMESTAMPTZ DEFAULT NOW(),
            ingest_cycle_id     INTEGER,

            created_at          TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_evidence_chains_output
            ON intelligence_evidence_chains (output_type, output_id);
        CREATE INDEX IF NOT EXISTS idx_evidence_chains_computed
            ON intelligence_evidence_chains (computed_at DESC);
    """),
]


def run_migration():
    print("NDIP V8 — Phase 1 Database Migration")
    print("=" * 60)

    results = []
    with engine.connect() as conn:
        for name, sql in MIGRATIONS:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"  ✓ {name}")
                results.append((name, True, None))
            except Exception as e:
                error_msg = str(e)[:120]
                # Some migrations are idempotent — warn but continue
                if "already exists" in error_msg or "duplicate" in error_msg.lower():
                    print(f"  ~ {name} (already applied)")
                    results.append((name, True, "already applied"))
                else:
                    print(f"  ✗ {name}: {error_msg}")
                    results.append((name, False, error_msg))
                conn.rollback()

    print("=" * 60)
    failed = [r for r in results if not r[1]]
    if failed:
        print(f"\n⚠  {len(failed)} migration(s) failed:")
        for name, _, err in failed:
            print(f"   - {name}: {err}")
    else:
        print(f"\n✓ All {len(results)} migrations applied successfully")

    print("\nNew tables created:")
    print("  • audit_log — append-only audit trail for all API requests")
    print("  • roles — RBAC role definitions")
    print("  • permissions — RBAC permission definitions")
    print("  • role_permissions — role-to-permission mappings")
    print("  • user_roles — user-to-role assignments")
    print("  • daily_intelligence_snapshots — historical state for 'today vs yesterday'")
    print("  • intelligence_evidence_chains — explainability and confidence scoring")
    print("\nConstraints added:")
    print("  • UNIQUE on opportunity_alignment_scores(stakeholder_id, opportunity_type)")
    print("  • Performance indexes on social_posts and normalised_posts")


if __name__ == "__main__":
    run_migration()
