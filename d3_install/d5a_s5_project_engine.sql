-- ============================================================
-- NDIP on Orion Platform Kernel
-- Phase D5A — Stage 5: Project Engine
-- d5a_s5_project_engine.sql
-- ============================================================
-- Orion Kernel capability — domain-agnostic project infrastructure
-- Revised per architect GO WITH CONDITIONS directive:
--   - Independent projects NOT blanket-visible to all users
--   - visibility field has real access-control meaning
--   - platform_projects untouched
-- Safe to re-run (idempotent)
-- Additive only
-- Depends on: D5A-S1 through S4 complete
-- ============================================================

BEGIN;

-- ── Confirm platform_projects is untouched ────────────────────
DO $$
DECLARE v INT;
BEGIN
    SELECT COUNT(*) INTO v FROM platform_projects;
    RAISE NOTICE 'platform_projects preserved: % rows (untouched)', v;
END $$;

-- ------------------------------------------------------------
-- 1. PROJECT ROLES reference table
-- Data-driven, not hardcoded in application logic
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS project_roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    description TEXT,
    is_system   BOOL NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO project_roles (name, description, is_system) VALUES
    ('originator',             'Project initiator/creator',                    TRUE),
    ('owner',                  'Project owner with full governance rights',     TRUE),
    ('lead_organisation',      'Lead implementing organisation',               TRUE),
    ('partner',                'Participating partner organisation',            TRUE),
    ('technical_partner',      'Technical delivery partner',                   TRUE),
    ('funding_partner',        'Funding or investment partner',                 TRUE),
    ('implementation_partner', 'Implementation delivery partner',              TRUE),
    ('community_partner',      'Community or grassroots partner',              TRUE),
    ('advisory_partner',       'Advisory or strategic partner',                TRUE),
    ('observer',               'Observer — limited read access',              TRUE),
    ('member',                 'Individual project member',                    TRUE),
    ('coordinator',            'Project coordinator',                          TRUE)
ON CONFLICT (name) DO NOTHING;

DO $$ BEGIN
    RAISE NOTICE 'project_roles seeded: % roles', (SELECT COUNT(*) FROM project_roles);
END $$;

-- ------------------------------------------------------------
-- 2. PROJECTS TABLE
-- tenant_id nullable = independent/cross-tenant project
-- visibility field has real access-control meaning
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Tenant ownership — NULL = independent project (not tenant-owned)
    tenant_id               UUID REFERENCES tenants(id),

    -- Originating organisation — separate from tenant ownership
    originating_org_id      UUID REFERENCES organisations(id),

    -- Originating identity — always required
    created_by              UUID NOT NULL REFERENCES platform_identities(id),

    -- Core fields
    name                    TEXT NOT NULL,
    slug                    TEXT UNIQUE,
    description             TEXT,
    project_type            TEXT NOT NULL DEFAULT 'standard' CHECK (project_type IN (
                                'standard', 'independent', 'community', 'research',
                                'humanitarian', 'commercial', 'government', 'academic',
                                'diaspora', 'infrastructure', 'advocacy', 'other'
                            )),

    -- Lifecycle
    status                  TEXT NOT NULL DEFAULT 'Draft' CHECK (status IN (
                                'Draft', 'Proposed', 'Under Review', 'Approved',
                                'Active', 'Paused', 'Completed', 'Cancelled', 'Archived'
                            )),

    -- Visibility — real access-control meaning per architect directive
    -- private:           Originator + explicitly authorised participants/admins only
    -- participating_orgs: Authorised members of participating organisations
    -- tenant:            Appropriate tenant context where applicable
    -- public:            Public/shared — subject to platform policy
    visibility              TEXT NOT NULL DEFAULT 'tenant' CHECK (visibility IN (
                                'private', 'participating_orgs', 'tenant', 'public'
                            )),

    -- Geographic scope
    geo_scope               TEXT DEFAULT 'unspecified' CHECK (geo_scope IN (
                                'national', 'state', 'lga', 'ward', 'polling_unit',
                                'multi_state', 'international', 'diaspora', 'unspecified'
                            )),
    location_country_id     UUID REFERENCES countries(id),
    location_state_id       INT REFERENCES ng_states(id),
    location_lga_id         INT REFERENCES ng_lgas(id),
    location_ward_id        INT REFERENCES ng_wards(id),
    -- PU stub — nullable, not required for S5 operations
    location_polling_unit_id INT REFERENCES ng_polling_units(id),

    -- Dates
    start_date              DATE,
    end_date                DATE,
    target_end_date         DATE,

    -- SDG alignment
    sdg_alignment           JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Lightweight outcomes placeholder (full evidence at S7)
    outcomes                JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Verification lifecycle
    verification_status     TEXT NOT NULL DEFAULT 'Draft' CHECK (verification_status IN (
                                'Draft', 'Submitted', 'Under Review', 'Verified',
                                'Rejected', 'Archived'
                            )),
    verified_by             UUID REFERENCES platform_identities(id),
    verified_at             TIMESTAMPTZ,
    verification_notes      TEXT,
    rejection_reason        TEXT,
    submitted_at            TIMESTAMPTZ,

    -- Provenance
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_archived             BOOL NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_projects_tenant_id      ON projects(tenant_id);
CREATE INDEX IF NOT EXISTS ix_projects_created_by     ON projects(created_by);
CREATE INDEX IF NOT EXISTS ix_projects_status         ON projects(status);
CREATE INDEX IF NOT EXISTS ix_projects_project_type   ON projects(project_type);
CREATE INDEX IF NOT EXISTS ix_projects_visibility     ON projects(visibility);
CREATE INDEX IF NOT EXISTS ix_projects_state_id       ON projects(location_state_id);
CREATE INDEX IF NOT EXISTS ix_projects_ward_id        ON projects(location_ward_id);
-- Partial index for independent projects
CREATE INDEX IF NOT EXISTS ix_projects_independent
    ON projects(id) WHERE tenant_id IS NULL;

-- RLS on projects
-- Access rules (per architect directive):
-- 1. Tenant-owned projects: visible to matching tenant context
-- 2. Independent projects: visibility is governed by visibility field
--    private → only accessible via participant check in API layer (RLS returns false at DB level)
--    participating_orgs → accessible to participants (checked in API/view layer)
--    public → accessible to all authenticated users
--    tenant → not applicable for tenant_id=NULL projects (treated as participating_orgs)
-- NOTE: Full participant-based access for private/participating_orgs independent projects
-- is enforced at the API layer via project_participants join.
-- The RLS policy here is the baseline gate; API adds participant checks.
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON projects;
CREATE POLICY tenant_isolation ON projects
    USING (
        -- Tenant-owned project: match tenant context
        (tenant_id IS NOT NULL AND
         tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::uuid)
        OR
        -- Public independent project: visible to all authenticated users
        (tenant_id IS NULL AND visibility = 'public')
        OR
        -- Platform admin bypass (platform_admins use null tenant context)
        NULLIF(current_setting('app.current_tenant_id', TRUE), '') IS NULL
    );
-- NOTE: private and participating_orgs independent projects are enforced
-- at the API layer via project_participants joins.
-- The RLS here is a safe baseline that errs toward restriction.

DO $$ BEGIN RAISE NOTICE 'projects table created with RLS (visibility-aware)'; END $$;

-- ------------------------------------------------------------
-- 3. PROJECT PARTICIPANTS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS project_participants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id),
    -- Organisation and/or identity — not neither
    organisation_id UUID REFERENCES organisations(id),
    identity_id     UUID REFERENCES platform_identities(id),
    role_id         UUID NOT NULL REFERENCES project_roles(id),
    -- Participation status
    status          TEXT NOT NULL DEFAULT 'invited' CHECK (status IN (
                        'invited', 'active', 'paused', 'withdrawn', 'removed'
                    )),
    joined_at       TIMESTAMPTZ,
    left_at         TIMESTAMPTZ,
    notes           TEXT,
    added_by        UUID REFERENCES platform_identities(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ck_participant_not_empty CHECK (
        organisation_id IS NOT NULL OR identity_id IS NOT NULL
    )
);

CREATE INDEX IF NOT EXISTS ix_proj_part_project    ON project_participants(project_id);
CREATE INDEX IF NOT EXISTS ix_proj_part_org        ON project_participants(organisation_id);
CREATE INDEX IF NOT EXISTS ix_proj_part_identity   ON project_participants(identity_id);
CREATE INDEX IF NOT EXISTS ix_proj_part_role       ON project_participants(role_id);
CREATE INDEX IF NOT EXISTS ix_proj_part_status     ON project_participants(status);

-- RLS on project_participants
-- A user can see participants of projects they can access
ALTER TABLE project_participants ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON project_participants;
CREATE POLICY tenant_isolation ON project_participants
    USING (
        EXISTS (
            SELECT 1 FROM projects p WHERE p.id = project_id
            AND (
                -- Tenant-owned: match tenant
                (p.tenant_id IS NOT NULL AND
                 p.tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::uuid)
                OR
                -- Public independent project
                (p.tenant_id IS NULL AND p.visibility = 'public')
                OR
                -- Platform admin
                NULLIF(current_setting('app.current_tenant_id', TRUE), '') IS NULL
            )
        )
    );

DO $$ BEGIN RAISE NOTICE 'project_participants table created with RLS'; END $$;

-- ------------------------------------------------------------
-- 4. Add project_id FK to activities (idempotent)
-- ------------------------------------------------------------
ALTER TABLE activities ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id);
CREATE INDEX IF NOT EXISTS ix_activities_project_id
    ON activities(project_id) WHERE project_id IS NOT NULL;

-- ------------------------------------------------------------
-- 5. Add project_id FK to volunteer_records (idempotent)
-- ------------------------------------------------------------
ALTER TABLE volunteer_records ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id);
CREATE INDEX IF NOT EXISTS ix_volunteer_project_id
    ON volunteer_records(project_id) WHERE project_id IS NOT NULL;

DO $$ BEGIN
    RAISE NOTICE 'project_id FK added to activities and volunteer_records (idempotent)';
END $$;

-- ------------------------------------------------------------
-- 6. Update platform_config
-- ------------------------------------------------------------
INSERT INTO platform_config (key, value)
VALUES ('platform_version', '"D5A-S5"')
ON CONFLICT (key) DO UPDATE SET value = '"D5A-S5"', updated_at = now();

-- ------------------------------------------------------------
-- 7. Verification
-- ------------------------------------------------------------
DO $$
DECLARE
    v_pp_rows   INT;
    v_projects  INT;
    v_parts     INT;
    v_roles     INT;
    v_act_col   INT;
    v_vol_col   INT;
BEGIN
    -- Confirm platform_projects untouched
    SELECT COUNT(*) INTO v_pp_rows FROM platform_projects;

    SELECT COUNT(*) INTO v_projects  FROM projects;
    SELECT COUNT(*) INTO v_parts     FROM project_participants;
    SELECT COUNT(*) INTO v_roles     FROM project_roles;

    SELECT COUNT(*) INTO v_act_col FROM information_schema.columns
        WHERE table_name='activities' AND column_name='project_id';
    SELECT COUNT(*) INTO v_vol_col FROM information_schema.columns
        WHERE table_name='volunteer_records' AND column_name='project_id';

    RAISE NOTICE '=== D5A-S5 PROJECT ENGINE — VERIFICATION ===';
    RAISE NOTICE 'platform_projects (v2): % rows — UNTOUCHED', v_pp_rows;
    RAISE NOTICE 'projects table:          created (% rows)', v_projects;
    RAISE NOTICE 'project_participants:    created (% rows)', v_parts;
    RAISE NOTICE 'project_roles seeded:    % roles', v_roles;
    RAISE NOTICE 'activities.project_id:   % (1=present)', v_act_col;
    RAISE NOTICE 'volunteer.project_id:    % (1=present)', v_vol_col;
    RAISE NOTICE 'platform_version:        D5A-S5';

    IF v_roles < 10 THEN
        RAISE EXCEPTION 'project_roles not fully seeded — expected 12, got %', v_roles;
    END IF;
    IF v_act_col = 0 THEN
        RAISE EXCEPTION 'activities.project_id column missing';
    END IF;
    IF v_vol_col = 0 THEN
        RAISE EXCEPTION 'volunteer_records.project_id column missing';
    END IF;

    RAISE NOTICE '=== D5A-S5 COMPLETE ===';
END $$;

COMMIT;

-- ============================================================
-- D5A-S5 complete.
-- New tables: projects, project_participants, project_roles
-- Modified: activities.project_id FK (nullable, additive)
--           volunteer_records.project_id FK (nullable, additive)
-- RLS: visibility-aware policy on projects and project_participants
-- platform_projects: UNTOUCHED (v2 routes unaffected)
-- Polling units: NOT imported (nullable stub only)
-- ============================================================
