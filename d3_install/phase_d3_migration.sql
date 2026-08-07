-- =============================================================================
-- NDIP Phase D.3 — Platform Readiness Migration
-- File: migrations/phase_d3_migration.sql
-- Author: Chief Engineering AI
-- Date: 2026-08-02
-- Constraints:
--   - DO NOT modify any Phase A–C tables
--   - DO NOT modify members, member_profiles, member_sessions, member_number_counters
--   - DO NOT modify ng_states, ng_lgas, ng_wards, ng_polling_units, chapters
--   - UUID primary keys throughout
--   - JSONB via standard column type (not CAST in DDL)
--   - All score/weight columns: FLOAT not DECIMAL
--   - Soft-delete via deleted_at on all entity tables
--   - Idempotent: all statements use IF NOT EXISTS / DO $$ guards
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 0. EXTENSIONS (required for gen_random_uuid() if not already enabled)
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- 1. AUDIT LOG
-- The AuditLogMiddleware (app/api/middleware/audit.py) is already live but
-- writes to a table that does not exist. This table is the highest-priority
-- item in D3.1 — without it every API request silently swallows an exception.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL PRIMARY KEY,
    user_email      VARCHAR(255),
    user_id         VARCHAR(100),
    action          VARCHAR(200) NOT NULL,
    endpoint        VARCHAR(500) NOT NULL,
    method          VARCHAR(10)  NOT NULL,
    ip_address      INET,
    user_agent      VARCHAR(500),
    payload_hash    VARCHAR(64),
    response_code   INTEGER,
    duration_ms     INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_audit_log_created_at    ON audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_audit_log_user_email    ON audit_log (user_email) WHERE user_email IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_audit_log_user_id       ON audit_log (user_id)    WHERE user_id    IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_audit_log_endpoint      ON audit_log (endpoint);
CREATE INDEX IF NOT EXISTS ix_audit_log_response_code ON audit_log (response_code) WHERE response_code >= 400;

-- ---------------------------------------------------------------------------
-- 2. EMAIL VERIFICATION TOKENS
-- Supports D3.3: email verification flow. Separate table keeps the members
-- table clean — tokens are ephemeral and high-write.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id   UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255) NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_evt_member_id  ON email_verification_tokens (member_id);
CREATE INDEX IF NOT EXISTS ix_evt_expires_at ON email_verification_tokens (expires_at);

-- ---------------------------------------------------------------------------
-- 3. PASSWORD RESET TOKENS
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id   UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255) NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ,
    ip_address  INET,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_prt_member_id  ON password_reset_tokens (member_id);
CREATE INDEX IF NOT EXISTS ix_prt_expires_at ON password_reset_tokens (expires_at);

-- ---------------------------------------------------------------------------
-- 4. LOGIN ATTEMPT LOG (account lockout / throttling support)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS login_attempts (
    id          BIGSERIAL PRIMARY KEY,
    email       VARCHAR(255) NOT NULL,
    ip_address  INET,
    success     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_login_attempts_email      ON login_attempts (email, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_login_attempts_ip         ON login_attempts (ip_address, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_login_attempts_created_at ON login_attempts (created_at DESC);

-- ---------------------------------------------------------------------------
-- 5. NOTIFICATIONS
-- Provider-abstracted notification delivery log.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id       UUID REFERENCES members(id) ON DELETE CASCADE,
    event_type      VARCHAR(100) NOT NULL,  -- invitation, verification, sponsorship, password_reset, etc.
    channel         VARCHAR(30)  NOT NULL,  -- email, whatsapp, sms, push
    recipient       VARCHAR(255) NOT NULL,  -- email address, phone number, or push token
    subject         VARCHAR(500),
    body_preview    TEXT,
    status          VARCHAR(30)  NOT NULL DEFAULT 'pending', -- pending, sent, failed, bounced
    provider        VARCHAR(50),            -- smtp, sendgrid, twilio, firebase, etc.
    provider_ref    VARCHAR(255),           -- provider message ID for tracking
    error_message   TEXT,
    retry_count     INTEGER NOT NULL DEFAULT 0,
    sent_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT notifications_status_check
        CHECK (status IN ('pending','sent','failed','bounced','cancelled')),
    CONSTRAINT notifications_channel_check
        CHECK (channel IN ('email','whatsapp','sms','push'))
);

CREATE INDEX IF NOT EXISTS ix_notifications_member_id   ON notifications (member_id) WHERE member_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_notifications_status      ON notifications (status, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_notifications_event_type  ON notifications (event_type);
CREATE INDEX IF NOT EXISTS ix_notifications_created_at  ON notifications (created_at DESC);

-- ---------------------------------------------------------------------------
-- 6. MEDIA ASSETS (Cloud Storage metadata — D3.5)
-- Metadata store for GCS-backed files. The actual files live in GCS;
-- this table stores the metadata needed to generate signed URLs and
-- enforce access control.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS media_assets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    uploaded_by     UUID REFERENCES members(id) ON DELETE SET NULL,
    entity_type     VARCHAR(100) NOT NULL,  -- member_profile, project, verification, report, etc.
    entity_id       UUID,
    asset_type      VARCHAR(50)  NOT NULL,  -- image, video, pdf, document, evidence
    original_name   VARCHAR(500) NOT NULL,
    gcs_bucket      VARCHAR(255) NOT NULL,
    gcs_key         VARCHAR(1000) NOT NULL,
    mime_type       VARCHAR(200) NOT NULL,
    size_bytes      BIGINT       NOT NULL,
    width_px        INTEGER,                -- for images/videos
    height_px       INTEGER,                -- for images/videos
    duration_sec    FLOAT,                  -- for videos
    is_public       BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT media_assets_asset_type_check
        CHECK (asset_type IN ('image','video','pdf','document','evidence','other'))
);

CREATE INDEX IF NOT EXISTS ix_media_assets_uploaded_by  ON media_assets (uploaded_by) WHERE uploaded_by IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_media_assets_entity       ON media_assets (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS ix_media_assets_created_at   ON media_assets (created_at DESC);

-- ---------------------------------------------------------------------------
-- 7. ENGAGEMENT REPORTS (D3.2 /api/v2/reports)
-- NERS: Nigerian Engagement Reporting System. Members file structured
-- reports of diaspora engagement activities.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS engagement_reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id       UUID NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
    chapter_id      UUID REFERENCES chapters(id) ON DELETE SET NULL,
    report_type     VARCHAR(100) NOT NULL,   -- community_event, fundraiser, advocacy, cultural, educational, outreach
    title           VARCHAR(500) NOT NULL,
    description     TEXT         NOT NULL,
    event_date      DATE         NOT NULL,
    location        VARCHAR(500),
    country         VARCHAR(100),
    attendees_count INTEGER      NOT NULL DEFAULT 0,
    outcome_summary TEXT,
    media_urls      JSONB        NOT NULL DEFAULT '[]',
    tags            JSONB        NOT NULL DEFAULT '[]',
    impact_score    FLOAT,
    status          VARCHAR(30)  NOT NULL DEFAULT 'draft',  -- draft, submitted, under_review, approved, rejected
    reviewed_by     UUID REFERENCES members(id) ON DELETE SET NULL,
    reviewed_at     TIMESTAMPTZ,
    reviewer_notes  TEXT,
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT er_status_check
        CHECK (status IN ('draft','submitted','under_review','approved','rejected')),
    CONSTRAINT er_attendees_check
        CHECK (attendees_count >= 0)
);

CREATE INDEX IF NOT EXISTS ix_er_member_id    ON engagement_reports (member_id);
CREATE INDEX IF NOT EXISTS ix_er_chapter_id   ON engagement_reports (chapter_id) WHERE chapter_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_er_status       ON engagement_reports (status);
CREATE INDEX IF NOT EXISTS ix_er_event_date   ON engagement_reports (event_date DESC);
CREATE INDEX IF NOT EXISTS ix_er_created_at   ON engagement_reports (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_er_live         ON engagement_reports (id) WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- 8. WARD SPONSORSHIPS (D3.2 /api/v2/sponsorships)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ward_sponsorships (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sponsor_member_id   UUID NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
    ward_id             INTEGER NOT NULL REFERENCES ng_wards(id),
    sponsorship_type    VARCHAR(100) NOT NULL,  -- infrastructure, education, health, agriculture, youth, women
    title               VARCHAR(500) NOT NULL,
    description         TEXT,
    budget_naira        FLOAT,
    start_date          DATE,
    end_date            DATE,
    status              VARCHAR(30) NOT NULL DEFAULT 'proposed',
    beneficiaries_count INTEGER     NOT NULL DEFAULT 0,
    impact_narrative    TEXT,
    evidence_urls       JSONB       NOT NULL DEFAULT '[]',
    verified_by         UUID REFERENCES members(id) ON DELETE SET NULL,
    verified_at         TIMESTAMPTZ,
    deleted_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ws_status_check
        CHECK (status IN ('proposed','active','completed','cancelled','suspended')),
    CONSTRAINT ws_budget_check
        CHECK (budget_naira IS NULL OR budget_naira >= 0),
    CONSTRAINT ws_dates_check
        CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS ix_ws_sponsor       ON ward_sponsorships (sponsor_member_id);
CREATE INDEX IF NOT EXISTS ix_ws_ward_id       ON ward_sponsorships (ward_id);
CREATE INDEX IF NOT EXISTS ix_ws_status        ON ward_sponsorships (status);
CREATE INDEX IF NOT EXISTS ix_ws_created_at    ON ward_sponsorships (created_at DESC);

-- ---------------------------------------------------------------------------
-- 9. WARD EXECUTIVES (D3.2 /api/v2/ward-executives)
-- CRM for diaspora members who hold or have held ward-level leadership roles.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ward_executives (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id       UUID NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
    ward_id         INTEGER NOT NULL REFERENCES ng_wards(id),
    position        VARCHAR(200) NOT NULL,   -- Ward Council Chair, Secretary, Treasurer, etc.
    party_affiliation VARCHAR(100),
    term_start      DATE,
    term_end        DATE,
    is_current      BOOLEAN NOT NULL DEFAULT TRUE,
    biography       TEXT,
    contact_email   VARCHAR(255),
    contact_phone   VARCHAR(50),
    verification_status VARCHAR(30) NOT NULL DEFAULT 'unverified',
    verified_by     UUID REFERENCES members(id) ON DELETE SET NULL,
    verified_at     TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT we_verification_check
        CHECK (verification_status IN ('unverified','pending','verified','rejected'))
);

CREATE INDEX IF NOT EXISTS ix_we_member_id ON ward_executives (member_id);
CREATE INDEX IF NOT EXISTS ix_we_ward_id   ON ward_executives (ward_id);
CREATE INDEX IF NOT EXISTS ix_we_current   ON ward_executives (is_current) WHERE is_current = TRUE;
CREATE UNIQUE INDEX IF NOT EXISTS ux_we_member_ward_live
    ON ward_executives (member_id, ward_id)
    WHERE deleted_at IS NULL AND is_current = TRUE;

-- ---------------------------------------------------------------------------
-- 10. PLATFORM PROJECTS (D3.2 /api/v2/projects)
-- Cross-chapter project tracking with stakeholder roles.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS platform_projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_by      UUID NOT NULL REFERENCES members(id) ON DELETE RESTRICT,
    chapter_id      UUID REFERENCES chapters(id) ON DELETE SET NULL,
    title           VARCHAR(500) NOT NULL,
    description     TEXT         NOT NULL,
    project_type    VARCHAR(100) NOT NULL,  -- development, advocacy, cultural, educational, fundraising, health
    sector          VARCHAR(100),
    state_id        INTEGER REFERENCES ng_states(id),
    lga_id          INTEGER REFERENCES ng_lgas(id),
    ward_id         INTEGER REFERENCES ng_wards(id),
    budget_naira    FLOAT,
    start_date      DATE,
    end_date        DATE,
    status          VARCHAR(30) NOT NULL DEFAULT 'draft',
    impact_score    FLOAT,
    tags            JSONB       NOT NULL DEFAULT '[]',
    media_urls      JSONB       NOT NULL DEFAULT '[]',
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pp_status_check
        CHECK (status IN ('draft','active','on_hold','completed','cancelled')),
    CONSTRAINT pp_budget_check
        CHECK (budget_naira IS NULL OR budget_naira >= 0),
    CONSTRAINT pp_dates_check
        CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS ix_pp_created_by  ON platform_projects (created_by);
CREATE INDEX IF NOT EXISTS ix_pp_chapter_id  ON platform_projects (chapter_id) WHERE chapter_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_pp_status      ON platform_projects (status);
CREATE INDEX IF NOT EXISTS ix_pp_state_id    ON platform_projects (state_id) WHERE state_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_pp_created_at  ON platform_projects (created_at DESC);

-- ---------------------------------------------------------------------------
-- 11. PROJECT STAKEHOLDERS (many-to-many with roles)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS project_stakeholders (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID NOT NULL REFERENCES platform_projects(id) ON DELETE CASCADE,
    member_id   UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    role        VARCHAR(100) NOT NULL,  -- owner, sponsor, funder, implementer, advisor, observer
    joined_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ps_role_check
        CHECK (role IN ('owner','sponsor','funder','implementer','advisor','observer','verifier'))
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_ps_project_member ON project_stakeholders (project_id, member_id);
CREATE INDEX IF NOT EXISTS ix_ps_member_id ON project_stakeholders (member_id);

-- ---------------------------------------------------------------------------
-- 12. VERIFICATION SUBMISSIONS (D3.2 /api/v2/verification)
-- Member identity and credential verification queue.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS verification_submissions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id       UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    submission_type VARCHAR(100) NOT NULL,  -- identity, credential, ward_executive, residence, employment
    documents       JSONB        NOT NULL DEFAULT '[]',  -- array of media_asset IDs / URLs
    notes           TEXT,
    status          VARCHAR(30)  NOT NULL DEFAULT 'pending',
    assigned_to     UUID REFERENCES members(id) ON DELETE SET NULL,  -- verifier role
    reviewed_by     UUID REFERENCES members(id) ON DELETE SET NULL,
    reviewed_at     TIMESTAMPTZ,
    rejection_reason TEXT,
    expires_at      TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT vs_status_check
        CHECK (status IN ('pending','assigned','under_review','approved','rejected','expired'))
);

CREATE INDEX IF NOT EXISTS ix_vs_member_id   ON verification_submissions (member_id);
CREATE INDEX IF NOT EXISTS ix_vs_status      ON verification_submissions (status);
CREATE INDEX IF NOT EXISTS ix_vs_assigned_to ON verification_submissions (assigned_to) WHERE assigned_to IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_vs_created_at  ON verification_submissions (created_at DESC);

-- ---------------------------------------------------------------------------
-- 13. DIASPORA IMPACT INDEX (D3.2 /api/v2/impact)
-- Per-member impact scores. Rebuilt nightly by the scheduler.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS diaspora_impact_scores (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id           UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    score_date          DATE NOT NULL DEFAULT CURRENT_DATE,
    total_score         FLOAT NOT NULL DEFAULT 0,
    reports_score       FLOAT NOT NULL DEFAULT 0,  -- contribution from engagement reports
    sponsorship_score   FLOAT NOT NULL DEFAULT 0,  -- contribution from ward sponsorships
    projects_score      FLOAT NOT NULL DEFAULT 0,  -- contribution from project participation
    verification_bonus  FLOAT NOT NULL DEFAULT 0,  -- bonus for verified status
    chapter_rank        INTEGER,                   -- rank within chapter (1 = highest)
    national_rank       INTEGER,                   -- rank nationally
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT dis_score_check CHECK (total_score >= 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_dis_member_date ON diaspora_impact_scores (member_id, score_date);
CREATE INDEX IF NOT EXISTS ix_dis_score_date   ON diaspora_impact_scores (score_date DESC);
CREATE INDEX IF NOT EXISTS ix_dis_total_score  ON diaspora_impact_scores (total_score DESC);
CREATE INDEX IF NOT EXISTS ix_dis_chapter_rank ON diaspora_impact_scores (chapter_rank) WHERE chapter_rank IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 14. INTELLIGENCE GRAPH NODES (D3.2 /api/v2/intelligence)
-- Lightweight adjacency model for the cross-entity intelligence graph.
-- Nodes can be members, projects, wards, chapters, or external entities.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS intelligence_nodes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type   VARCHAR(50)  NOT NULL,   -- member, project, ward, chapter, external_entity
    entity_id   UUID,                   -- FK to the underlying entity (nullable for external)
    label       VARCHAR(500) NOT NULL,
    attributes  JSONB        NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT in_node_type_check
        CHECK (node_type IN ('member','project','ward','chapter','external_entity','organisation'))
);

CREATE INDEX IF NOT EXISTS ix_in_node_type  ON intelligence_nodes (node_type);
CREATE INDEX IF NOT EXISTS ix_in_entity_id  ON intelligence_nodes (entity_id) WHERE entity_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS intelligence_edges (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node_id  UUID NOT NULL REFERENCES intelligence_nodes(id) ON DELETE CASCADE,
    target_node_id  UUID NOT NULL REFERENCES intelligence_nodes(id) ON DELETE CASCADE,
    relationship    VARCHAR(100) NOT NULL,  -- sponsors, implements, advises, represents, members_of
    weight          FLOAT        NOT NULL DEFAULT 1.0,
    attributes      JSONB        NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT ie_no_self_loop CHECK (source_node_id != target_node_id)
);

CREATE INDEX IF NOT EXISTS ix_ie_source ON intelligence_edges (source_node_id);
CREATE INDEX IF NOT EXISTS ix_ie_target ON intelligence_edges (target_node_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_ie_source_target_rel
    ON intelligence_edges (source_node_id, target_node_id, relationship);

-- ---------------------------------------------------------------------------
-- 15. MEMBER ONBOARDING STATE — Phase D.3 wizard
-- The existing user_onboarding_state table is the Phase A admin-user
-- learning system. This is a separate table for the member first-login
-- wizard (email verify → password → photo → profile → geography → chapter
-- → terms → dashboard). Keeping them separate preserves backward
-- compatibility with Phase A.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS member_onboarding_state (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id           UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    current_step        INTEGER     NOT NULL DEFAULT 1,  -- 1-10
    email_verified      BOOLEAN     NOT NULL DEFAULT FALSE,
    password_set        BOOLEAN     NOT NULL DEFAULT TRUE,  -- true at registration
    photo_uploaded      BOOLEAN     NOT NULL DEFAULT FALSE,
    profile_completed   BOOLEAN     NOT NULL DEFAULT FALSE,
    state_selected      BOOLEAN     NOT NULL DEFAULT FALSE,
    lga_selected        BOOLEAN     NOT NULL DEFAULT FALSE,
    ward_selected       BOOLEAN     NOT NULL DEFAULT FALSE,
    chapter_confirmed   BOOLEAN     NOT NULL DEFAULT FALSE,
    terms_accepted      BOOLEAN     NOT NULL DEFAULT FALSE,
    terms_accepted_at   TIMESTAMPTZ,
    wizard_completed    BOOLEAN     NOT NULL DEFAULT FALSE,
    wizard_completed_at TIMESTAMPTZ,
    completion_pct      INTEGER     NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT mos_step_check CHECK (current_step BETWEEN 1 AND 10),
    CONSTRAINT mos_pct_check  CHECK (completion_pct BETWEEN 0 AND 100)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_mos_member ON member_onboarding_state (member_id);

-- ---------------------------------------------------------------------------
-- 16. SCHEDULER JOB LOG (D3.6 observability)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scheduler_job_log (
    id          BIGSERIAL PRIMARY KEY,
    job_name    VARCHAR(200) NOT NULL,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    status      VARCHAR(20)  NOT NULL DEFAULT 'running',  -- running, success, failed
    records_processed INTEGER,
    error_message TEXT,
    CONSTRAINT sjl_status_check CHECK (status IN ('running','success','failed'))
);

CREATE INDEX IF NOT EXISTS ix_sjl_job_name   ON scheduler_job_log (job_name, started_at DESC);
CREATE INDEX IF NOT EXISTS ix_sjl_started_at ON scheduler_job_log (started_at DESC);
CREATE INDEX IF NOT EXISTS ix_sjl_status     ON scheduler_job_log (status);

-- ---------------------------------------------------------------------------
-- 17. HARDEN EXISTING PHASE D TABLES
-- Add missing indexes that benefit common query patterns.
-- All statements are IF NOT EXISTS — safe to re-run.
-- ---------------------------------------------------------------------------

-- member_profiles: missing index on updated_at for dashboard sorting
CREATE INDEX IF NOT EXISTS ix_member_profiles_member_id
    ON member_profiles (member_id);

-- member_sessions: compound index for active-session lookups
CREATE INDEX IF NOT EXISTS ix_member_sessions_active
    ON member_sessions (member_id, expires_at)
    WHERE revoked_at IS NULL;

-- chapters: missing compound status+country for chapter directory queries
CREATE INDEX IF NOT EXISTS ix_chapters_status_country
    ON chapters (status, country)
    WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- 18. BENCHMARK QUERY SUPPORT — EXPLAIN plan indexes
-- These cover the most common cross-table joins anticipated in D3.2 APIs.
-- ---------------------------------------------------------------------------

-- Leaderboard: top impact scores for a chapter
CREATE INDEX IF NOT EXISTS ix_dis_chapter_score
    ON diaspora_impact_scores (score_date DESC, total_score DESC)
    WHERE chapter_rank IS NOT NULL;

-- Notification delivery retry queue
CREATE INDEX IF NOT EXISTS ix_notifications_retry
    ON notifications (status, retry_count, created_at)
    WHERE status IN ('pending','failed');

-- Verification queue for verifiers
CREATE INDEX IF NOT EXISTS ix_vs_queue
    ON verification_submissions (status, created_at)
    WHERE status IN ('pending','assigned') AND deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- 19. VERIFY MIGRATION INTEGRITY
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    missing_tables TEXT[] := ARRAY[]::TEXT[];
    t TEXT;
    required_tables TEXT[] := ARRAY[
        'audit_log',
        'email_verification_tokens',
        'password_reset_tokens',
        'login_attempts',
        'notifications',
        'media_assets',
        'engagement_reports',
        'ward_sponsorships',
        'ward_executives',
        'platform_projects',
        'project_stakeholders',
        'verification_submissions',
        'diaspora_impact_scores',
        'intelligence_nodes',
        'intelligence_edges',
        'member_onboarding_state',
        'scheduler_job_log'
    ];
BEGIN
    FOREACH t IN ARRAY required_tables LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = t
        ) THEN
            missing_tables := array_append(missing_tables, t);
        END IF;
    END LOOP;

    IF array_length(missing_tables, 1) > 0 THEN
        RAISE EXCEPTION 'Migration incomplete — missing tables: %', array_to_string(missing_tables, ', ');
    ELSE
        RAISE NOTICE 'D3.1 migration verified — all 17 tables present';
    END IF;
END $$;
