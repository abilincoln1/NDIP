-- ============================================================================
-- Phase D.2 — Members Foundation
-- Additive migration. No ALTER, no DROP, no modification of existing tables.
-- Transactional, idempotent (safe to re-run).
--
-- Depends on (read-only FK references, not modified):
--   ng_states, ng_lgas   (Phase D.1 — Geography Foundation)
--   admin_users          (Phase A — pre-existing)
--
-- New tables:
--   chapters
--   members
--   member_profiles
--   member_sessions
--   member_number_counters   -- support table for atomic, per-year, gap-free
--                            -- membership-number generation (see
--                            -- PHASE_D2_IMPLEMENTATION.md, "Membership Number
--                            -- Generation" — disclosed addition beyond the
--                            -- four tables named in the D.2 directive).
--
-- UUID generation uses native PostgreSQL gen_random_uuid() (built into core
-- since PostgreSQL 13 — no CREATE EXTENSION required). Verified against a
-- disposable PostgreSQL 16.2 instance, matching the production postgres:16
-- image, before this migration was written.
-- ============================================================================

BEGIN;

-- ─── chapters ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS chapters (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    country         VARCHAR(100) NOT NULL,
    state_id        INTEGER REFERENCES ng_states(id),
    city            VARCHAR(150),
    chapter_type    VARCHAR(50) NOT NULL DEFAULT 'local',
    chairperson     VARCHAR(255),
    email           VARCHAR(255),
    phone           VARCHAR(50),
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

-- Unique among non-deleted chapters only, so a retired chapter's name can be
-- reused (consistent soft-delete-aware uniqueness pattern applied across
-- every table in this migration — see PHASE_D2_IMPLEMENTATION.md).
CREATE UNIQUE INDEX IF NOT EXISTS ux_chapters_name_live
    ON chapters (name) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_chapters_country   ON chapters (country);
CREATE INDEX IF NOT EXISTS ix_chapters_state_id  ON chapters (state_id);
CREATE INDEX IF NOT EXISTS ix_chapters_status    ON chapters (status);

-- ─── member_number_counters ─────────────────────────────────────────────────
-- One row per calendar year. Incremented under SELECT ... FOR UPDATE inside
-- the same transaction as member creation, guaranteeing sequential,
-- gap-free-under-commit, unique membership numbers even under concurrent
-- registration (see PHASE_D2_IMPLEMENTATION.md, "Membership Number
-- Generation").

CREATE TABLE IF NOT EXISTS member_number_counters (
    year        INTEGER PRIMARY KEY,
    last_value  INTEGER NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── members ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS members (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id           INTEGER REFERENCES admin_users(id) ON DELETE SET NULL,
    email                   VARCHAR(255) NOT NULL,
    hashed_password         VARCHAR(255) NOT NULL,
    full_name               VARCHAR(255) NOT NULL,
    phone                   VARCHAR(50),
    state_of_origin_id      INTEGER REFERENCES ng_states(id),
    lga_of_origin_id        INTEGER REFERENCES ng_lgas(id),
    residence_country       VARCHAR(100),
    chapter_id              UUID REFERENCES chapters(id),
    membership_number       VARCHAR(30) NOT NULL,
    membership_tier         VARCHAR(30) NOT NULL DEFAULT 'standard',
    role                    VARCHAR(30) NOT NULL DEFAULT 'standard_member',
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at              TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_members_email_live
    ON members (email) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_members_membership_number_live
    ON members (membership_number) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_members_chapter_id           ON members (chapter_id);
CREATE INDEX IF NOT EXISTS ix_members_state_of_origin_id    ON members (state_of_origin_id);
CREATE INDEX IF NOT EXISTS ix_members_lga_of_origin_id      ON members (lga_of_origin_id);
CREATE INDEX IF NOT EXISTS ix_members_is_active             ON members (is_active);
CREATE INDEX IF NOT EXISTS ix_members_admin_user_id         ON members (admin_user_id);

-- ─── member_profiles (one-to-one with members) ─────────────────────────────

CREATE TABLE IF NOT EXISTS member_profiles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id           UUID NOT NULL UNIQUE REFERENCES members(id) ON DELETE CASCADE,
    date_of_birth       DATE,
    gender              VARCHAR(30),
    occupation          VARCHAR(150),
    organisation        VARCHAR(200),
    biography           TEXT,
    skills              JSONB,
    interests           JSONB,
    languages           JSONB,
    profile_photo_url   VARCHAR(500),
    linkedin_url        VARCHAR(500),
    facebook_url        VARCHAR(500),
    twitter_url         VARCHAR(500),
    website             VARCHAR(500),
    last_login          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ
);

-- member_id UNIQUE constraint above already creates an index enforcing the
-- one-to-one relationship.

-- ─── member_sessions (refresh tokens / active sessions) ────────────────────

CREATE TABLE IF NOT EXISTS member_sessions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id               UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    refresh_token_hash      VARCHAR(255) NOT NULL,
    ip_address              VARCHAR(64),
    device                  VARCHAR(255),
    user_agent              VARCHAR(500),
    expires_at              TIMESTAMPTZ NOT NULL,
    revoked_at              TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_member_sessions_member_id   ON member_sessions (member_id);
CREATE INDEX IF NOT EXISTS ix_member_sessions_expires_at  ON member_sessions (expires_at);
CREATE INDEX IF NOT EXISTS ix_member_sessions_revoked_at  ON member_sessions (revoked_at);

-- ─── Seed: reference chapters ───────────────────────────────────────────────
-- The D.2 directive's API surface includes GET /chapter/{chapter_id}/members
-- and MemberService.assign_chapter(), but specifies no chapter-management
-- CRUD endpoint in this phase. A small set of reference chapters is seeded
-- so chapter assignment is exercisable end-to-end; full chapter
-- administration (create/edit/retire via API) is left for a future phase.
-- This is disclosed in PHASE_D2_IMPLEMENTATION.md and the compliance report.

INSERT INTO chapters (name, country, chapter_type, status, is_active)
VALUES
    ('Lagos Chapter',            'Nigeria', 'local',    'active', TRUE),
    ('Abuja (FCT) Chapter',      'Nigeria', 'local',    'active', TRUE),
    ('Diaspora - United States', 'United States', 'diaspora', 'active', TRUE),
    ('Diaspora - United Kingdom','United Kingdom', 'diaspora', 'active', TRUE)
ON CONFLICT DO NOTHING;

COMMIT;
