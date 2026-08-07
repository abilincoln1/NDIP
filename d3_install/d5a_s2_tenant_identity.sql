-- ============================================================
-- NDIP on Orion Platform Kernel
-- Phase D5A — Stage 2: Tenant & Identity Layer
-- d5a_s2_tenant_identity.sql
-- ============================================================
-- Safe to re-run (idempotent)
-- Additive only — no existing tables modified
-- Depends on: D5A-S1 complete
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 1. TENANTS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenants (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    slug                TEXT NOT NULL,
    tenant_type         TEXT NOT NULL CHECK (tenant_type IN (
                            'political','civic','academic','government',
                            'business','ngo','faith','independent')),
    status              TEXT NOT NULL DEFAULT 'active' CHECK (status IN (
                            'onboarding','active','suspended','offboarded')),
    primary_country_id  UUID REFERENCES countries(id),
    parent_tenant_id    UUID REFERENCES tenants(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ux_tenants_slug UNIQUE (slug)
);

CREATE INDEX IF NOT EXISTS ix_tenants_slug   ON tenants(slug);
CREATE INDEX IF NOT EXISTS ix_tenants_status ON tenants(status);
CREATE INDEX IF NOT EXISTS ix_tenants_type   ON tenants(tenant_type);

-- Seed RTIFN as founding tenant
INSERT INTO tenants (id, name, slug, tenant_type, status)
VALUES (
    '10000000-0000-0000-0000-000000000001',
    'RTIFN',
    'rtifn',
    'political',
    'active'
) ON CONFLICT (slug) DO NOTHING;

DO $$ BEGIN
    RAISE NOTICE 'tenants: % rows present', (SELECT COUNT(*) FROM tenants);
END $$;

-- ------------------------------------------------------------
-- 2. TENANT CONFIG
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenant_config (
    tenant_id               UUID PRIMARY KEY REFERENCES tenants(id),
    logo_url                TEXT,
    primary_colour          TEXT DEFAULT '#1a365d',
    secondary_colour        TEXT DEFAULT '#2d6a4f',
    accent_colour           TEXT DEFAULT '#e9c46a',
    platform_name_override  TEXT,
    powered_by_label        TEXT DEFAULT 'Powered by NDIP Platform',
    enabled_modules         JSONB NOT NULL DEFAULT '["identity","membership","activity","project","stakeholder","evidence","verification","timeline","geographic","intelligence","reporting"]'::jsonb,
    custom_terminology      JSONB NOT NULL DEFAULT '{}'::jsonb,
    dashboard_layout        JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO tenant_config (tenant_id, platform_name_override, powered_by_label, primary_colour)
VALUES (
    '10000000-0000-0000-0000-000000000001',
    'RTIFN Platform',
    'Powered by NDIP on Orion Platform Kernel',
    '#1a365d'
) ON CONFLICT (tenant_id) DO NOTHING;

DO $$ BEGIN
    RAISE NOTICE 'tenant_config: % rows present', (SELECT COUNT(*) FROM tenant_config);
END $$;

-- ------------------------------------------------------------
-- 3. ORGANISATIONS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS organisations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    name            TEXT NOT NULL,
    org_type        TEXT NOT NULL CHECK (org_type IN (
                        'chapter','branch','department','committee',
                        'initiative','hub','consortium','network')),
    parent_org_id   UUID REFERENCES organisations(id),
    country_id      UUID REFERENCES countries(id),
    state_id        INT REFERENCES ng_states(id),
    lga_id          INT REFERENCES ng_lgas(id),
    ward_id         INT REFERENCES ng_wards(id),
    address_text    TEXT,
    gps_lat         FLOAT,
    gps_lng         FLOAT,
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','inactive','archived')),
    founded_date    DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_organisations_tenant_id ON organisations(tenant_id);
CREATE INDEX IF NOT EXISTS ix_organisations_status    ON organisations(status);
CREATE INDEX IF NOT EXISTS ix_organisations_state_id  ON organisations(state_id);

-- Seed RTIFN Birmingham chapter — preserve existing chapter UUID
INSERT INTO organisations (id, tenant_id, name, org_type, status)
VALUES (
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    '10000000-0000-0000-0000-000000000001',
    'RTIFN Birmingham',
    'chapter',
    'active'
) ON CONFLICT (id) DO NOTHING;

DO $$ BEGIN
    RAISE NOTICE 'organisations: % rows present', (SELECT COUNT(*) FROM organisations);
END $$;

-- ------------------------------------------------------------
-- 4. PLATFORM IDENTITIES
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS platform_identities (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                   TEXT NOT NULL,
    phone                   TEXT,
    full_name               TEXT NOT NULL,
    date_of_birth           DATE,
    nationality_country_id  UUID REFERENCES countries(id),
    residence_country_id    UUID REFERENCES countries(id),
    profile_photo_url       TEXT,
    identity_status         TEXT NOT NULL DEFAULT 'active' CHECK (identity_status IN (
                                'active','suspended','deceased','merged')),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at            TIMESTAMPTZ,
    CONSTRAINT ux_platform_identities_email UNIQUE (email)
);

CREATE INDEX IF NOT EXISTS ix_platform_identities_email  ON platform_identities(email);
CREATE INDEX IF NOT EXISTS ix_platform_identities_status ON platform_identities(identity_status);

DO $$ BEGIN
    RAISE NOTICE 'platform_identities: % rows present', (SELECT COUNT(*) FROM platform_identities);
END $$;

-- ------------------------------------------------------------
-- 5. PLATFORM IDENTITY AUTH
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS platform_identity_auth (
    identity_id     UUID PRIMARY KEY REFERENCES platform_identities(id),
    password_hash   TEXT NOT NULL,
    mfa_enabled     BOOL NOT NULL DEFAULT FALSE,
    mfa_secret      TEXT,
    last_login_at   TIMESTAMPTZ,
    failed_attempts INT NOT NULL DEFAULT 0,
    locked_until    TIMESTAMPTZ
);

DO $$ BEGIN
    RAISE NOTICE 'platform_identity_auth: % rows present', (SELECT COUNT(*) FROM platform_identity_auth);
END $$;

-- ------------------------------------------------------------
-- 6. IDENTITY SKILLS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS identity_skills (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id         UUID NOT NULL REFERENCES platform_identities(id),
    skill_id            UUID NOT NULL REFERENCES skills(id),
    proficiency_level   TEXT CHECK (proficiency_level IN ('beginner','intermediate','advanced','expert')),
    verified            BOOL NOT NULL DEFAULT FALSE,
    CONSTRAINT ux_identity_skill UNIQUE (identity_id, skill_id)
);

CREATE INDEX IF NOT EXISTS ix_identity_skills_identity ON identity_skills(identity_id);
CREATE INDEX IF NOT EXISTS ix_identity_skills_skill    ON identity_skills(skill_id);

DO $$ BEGIN
    RAISE NOTICE 'identity_skills: % rows present', (SELECT COUNT(*) FROM identity_skills);
END $$;

-- ------------------------------------------------------------
-- 7. ROLES
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS kernel_roles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID REFERENCES tenants(id),
    name            TEXT NOT NULL,
    description     TEXT,
    permissions     JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_system_role  BOOL NOT NULL DEFAULT FALSE,
    CONSTRAINT ux_kernel_roles_tenant_name UNIQUE (tenant_id, name)
);

CREATE INDEX IF NOT EXISTS ix_kernel_roles_tenant_id ON kernel_roles(tenant_id);

-- Seed RTIFN role definitions
INSERT INTO kernel_roles (tenant_id, name, description, is_system_role, permissions) VALUES
(
    '10000000-0000-0000-0000-000000000001',
    'super_admin',
    'Full platform access',
    TRUE,
    '{"all": true}'::jsonb
),
(
    '10000000-0000-0000-0000-000000000001',
    'national_director',
    'National director — cross-chapter access',
    TRUE,
    '{"members": ["read","write"], "reports": ["read","write"], "audit": ["read"]}'::jsonb
),
(
    '10000000-0000-0000-0000-000000000001',
    'chapter_admin',
    'Chapter administrator',
    TRUE,
    '{"members": ["read","write","invite"], "activities": ["read","write"], "reports": ["read"]}'::jsonb
),
(
    '10000000-0000-0000-0000-000000000001',
    'verifier',
    'Verifies submitted records',
    TRUE,
    '{"verification": ["read","write"], "activities": ["read"], "members": ["read"]}'::jsonb
),
(
    '10000000-0000-0000-0000-000000000001',
    'intelligence_analyst',
    'Intelligence and analytics access',
    TRUE,
    '{"intelligence": ["read"], "reports": ["read"], "audit": ["read"]}'::jsonb
),
(
    '10000000-0000-0000-0000-000000000001',
    'verified_member',
    'Verified member — full member access',
    TRUE,
    '{"activities": ["read","write"], "projects": ["read","write"], "profile": ["read","write"]}'::jsonb
),
(
    '10000000-0000-0000-0000-000000000001',
    'standard_member',
    'Standard member',
    TRUE,
    '{"activities": ["read","write"], "profile": ["read","write"]}'::jsonb
)
ON CONFLICT (tenant_id, name) DO NOTHING;

DO $$ BEGIN
    RAISE NOTICE 'kernel_roles: % rows present', (SELECT COUNT(*) FROM kernel_roles);
END $$;

-- ------------------------------------------------------------
-- 8. PLATFORM ADMINS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS platform_admins (
    identity_id UUID PRIMARY KEY REFERENCES platform_identities(id),
    admin_level TEXT NOT NULL CHECK (admin_level IN ('support','admin','super_admin')),
    granted_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    granted_by  UUID REFERENCES platform_identities(id)
);

DO $$ BEGIN
    RAISE NOTICE 'platform_admins: % rows present', (SELECT COUNT(*) FROM platform_admins);
END $$;

-- ------------------------------------------------------------
-- 9. ROW LEVEL SECURITY
-- ------------------------------------------------------------

-- organisations: tenant isolation
ALTER TABLE organisations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON organisations;
CREATE POLICY tenant_isolation ON organisations
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::uuid);

-- kernel_roles: tenant isolation
ALTER TABLE kernel_roles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON kernel_roles;
CREATE POLICY tenant_isolation ON kernel_roles
    USING (tenant_id IS NULL OR tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::uuid);

-- Allow agora_user to bypass RLS for application queries
-- RLS is enforced at session level by setting app.current_tenant_id
-- platform_identities and auth tables are NOT RLS-gated (they are global)

DO $$ BEGIN
    RAISE NOTICE 'RLS policies applied to: organisations, kernel_roles';
END $$;

-- ------------------------------------------------------------
-- 10. UPDATE platform_config — record S2 complete
-- ------------------------------------------------------------
INSERT INTO platform_config (key, value)
VALUES ('platform_version', '"D5A-S2"')
ON CONFLICT (key) DO UPDATE SET value = '"D5A-S2"', updated_at = now();

-- ------------------------------------------------------------
-- 11. VERIFICATION — D5A-S2 Complete Check
-- ------------------------------------------------------------
DO $$
DECLARE
    v_tenants           INT;
    v_tenant_config     INT;
    v_organisations     INT;
    v_identities        INT;
    v_auth              INT;
    v_roles             INT;
    v_rtifn_id          UUID;
    v_birmingham_id     UUID;
BEGIN
    SELECT COUNT(*) INTO v_tenants        FROM tenants;
    SELECT COUNT(*) INTO v_tenant_config  FROM tenant_config;
    SELECT COUNT(*) INTO v_organisations  FROM organisations;
    SELECT COUNT(*) INTO v_identities     FROM platform_identities;
    SELECT COUNT(*) INTO v_auth           FROM platform_identity_auth;
    SELECT COUNT(*) INTO v_roles          FROM kernel_roles;
    SELECT id INTO v_rtifn_id             FROM tenants WHERE slug = 'rtifn';
    SELECT id INTO v_birmingham_id        FROM organisations WHERE id = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';

    RAISE NOTICE '=== D5A-S2 TENANT & IDENTITY LAYER — VERIFICATION ===';
    RAISE NOTICE 'tenants:              % (expect 1)',  v_tenants;
    RAISE NOTICE 'tenant_config:        % (expect 1)',  v_tenant_config;
    RAISE NOTICE 'organisations:        % (expect 1)',  v_organisations;
    RAISE NOTICE 'platform_identities:  % (expect 0)',  v_identities;
    RAISE NOTICE 'platform_identity_auth: % (expect 0)', v_auth;
    RAISE NOTICE 'kernel_roles:         % (expect 7)',  v_roles;
    RAISE NOTICE 'RTIFN tenant UUID:    %',             v_rtifn_id;
    RAISE NOTICE 'Birmingham org UUID:  %',             v_birmingham_id;
    RAISE NOTICE '=== D5A-S2 COMPLETE ===';

    IF v_rtifn_id IS NULL THEN
        RAISE EXCEPTION 'RTIFN tenant not found — migration failed';
    END IF;
    IF v_birmingham_id IS NULL THEN
        RAISE EXCEPTION 'Birmingham organisation not found — UUID not preserved';
    END IF;
    IF v_roles < 7 THEN
        RAISE EXCEPTION 'kernel_roles count too low — expected 7';
    END IF;
END $$;

COMMIT;

-- ============================================================
-- D5A-S2 complete.
-- New tables: tenants, tenant_config, organisations,
--             platform_identities, platform_identity_auth,
--             identity_skills, kernel_roles, platform_admins
-- RLS applied to: organisations, kernel_roles
-- RTIFN seeded as founding tenant (slug: rtifn)
-- Birmingham chapter UUID preserved
-- platform_identities is empty — v3 auth routes populate it
-- Next: write /api/v3/auth/ and /api/v3/tenants/ routes
-- ============================================================
