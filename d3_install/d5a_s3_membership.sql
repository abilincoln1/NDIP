-- ============================================================
-- NDIP on Orion Platform Kernel
-- Phase D5A — Stage 3: Membership Engine
-- d5a_s3_membership.sql
-- ============================================================
-- Safe to re-run (idempotent)
-- Additive only — no existing tables modified
-- Depends on: D5A-S1, D5A-S2 complete
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 1. MEMBERSHIPS
-- Links platform_identities to tenants/organisations with roles
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS memberships (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id         UUID NOT NULL REFERENCES platform_identities(id),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    organisation_id     UUID REFERENCES organisations(id),
    membership_number   TEXT,
    membership_type     TEXT NOT NULL DEFAULT 'standard' CHECK (membership_type IN (
                            'founding','standard','associate','honorary','student','volunteer')),
    status              TEXT NOT NULL DEFAULT 'invited' CHECK (status IN (
                            'invited','active','suspended','resigned','expelled','deceased')),
    joined_date         DATE,
    invited_by          UUID REFERENCES platform_identities(id),
    verified_by         UUID REFERENCES platform_identities(id),
    verification_date   DATE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ux_memberships_identity_tenant UNIQUE (identity_id, tenant_id, organisation_id)
);

CREATE INDEX IF NOT EXISTS ix_memberships_identity_id    ON memberships(identity_id);
CREATE INDEX IF NOT EXISTS ix_memberships_tenant_id      ON memberships(tenant_id);
CREATE INDEX IF NOT EXISTS ix_memberships_org_id         ON memberships(organisation_id);
CREATE INDEX IF NOT EXISTS ix_memberships_status         ON memberships(status);
CREATE INDEX IF NOT EXISTS ix_memberships_number         ON memberships(membership_number);

-- RLS
ALTER TABLE memberships ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON memberships;
CREATE POLICY tenant_isolation ON memberships
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::uuid);

DO $$ BEGIN
    RAISE NOTICE 'memberships table created with RLS';
END $$;

-- ------------------------------------------------------------
-- 2. MEMBERSHIP ROLES
-- Assigns kernel_roles to memberships
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS membership_roles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    membership_id   UUID NOT NULL REFERENCES memberships(id) ON DELETE CASCADE,
    role_id         UUID NOT NULL REFERENCES kernel_roles(id),
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    granted_by      UUID REFERENCES platform_identities(id),
    expires_at      TIMESTAMPTZ,
    CONSTRAINT ux_membership_role UNIQUE (membership_id, role_id)
);

CREATE INDEX IF NOT EXISTS ix_membership_roles_membership ON membership_roles(membership_id);
CREATE INDEX IF NOT EXISTS ix_membership_roles_role       ON membership_roles(role_id);

DO $$ BEGIN
    RAISE NOTICE 'membership_roles table created';
END $$;

-- ------------------------------------------------------------
-- 3. SEED — RTIFN TEST ACCOUNTS AS ACTIVE MEMBERSHIPS
-- Maps all 7 v2 test accounts to v3 memberships
-- Uses same UUIDs as v2 members table
-- ------------------------------------------------------------

-- Get IDs we need
DO $$
DECLARE
    v_tenant_id     UUID := '10000000-0000-0000-0000-000000000001';
    v_org_id        UUID := 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';
    v_superadmin_id UUID := 'b0000001-0000-0000-0000-000000000001';

    v_role_super_admin      UUID;
    v_role_nat_director     UUID;
    v_role_chapter_admin    UUID;
    v_role_verifier         UUID;
    v_role_analyst          UUID;
    v_role_verified_member  UUID;
    v_role_standard_member  UUID;

    v_membership_id UUID;

    -- Test account identity UUIDs (from v2 members)
    accounts UUID[] := ARRAY[
        'b0000001-0000-0000-0000-000000000001'::UUID,
        'b0000002-0000-0000-0000-000000000002'::UUID,
        'b0000003-0000-0000-0000-000000000003'::UUID,
        'b0000004-0000-0000-0000-000000000004'::UUID,
        'b0000005-0000-0000-0000-000000000005'::UUID,
        'b0000006-0000-0000-0000-000000000006'::UUID,
        'b0000007-0000-0000-0000-000000000007'::UUID
    ];
    account_roles TEXT[] := ARRAY[
        'super_admin',
        'national_director',
        'chapter_admin',
        'verifier',
        'intelligence_analyst',
        'verified_member',
        'standard_member'
    ];
    account_numbers TEXT[] := ARRAY[
        'NDIP-2026-000001',
        'NDIP-2026-000002',
        'NDIP-2026-000003',
        'NDIP-2026-000004',
        'NDIP-2026-000005',
        'NDIP-2026-000006',
        'NDIP-2026-000007'
    ];

BEGIN
    -- Get role IDs
    SELECT id INTO v_role_super_admin     FROM kernel_roles WHERE name = 'super_admin'          AND tenant_id = v_tenant_id;
    SELECT id INTO v_role_nat_director    FROM kernel_roles WHERE name = 'national_director'     AND tenant_id = v_tenant_id;
    SELECT id INTO v_role_chapter_admin   FROM kernel_roles WHERE name = 'chapter_admin'         AND tenant_id = v_tenant_id;
    SELECT id INTO v_role_verifier        FROM kernel_roles WHERE name = 'verifier'              AND tenant_id = v_tenant_id;
    SELECT id INTO v_role_analyst         FROM kernel_roles WHERE name = 'intelligence_analyst'  AND tenant_id = v_tenant_id;
    SELECT id INTO v_role_verified_member FROM kernel_roles WHERE name = 'verified_member'       AND tenant_id = v_tenant_id;
    SELECT id INTO v_role_standard_member FROM kernel_roles WHERE name = 'standard_member'       AND tenant_id = v_tenant_id;

    -- Ensure all 7 test accounts exist as platform_identities
    -- (superadmin was seeded in test_v3_auth.py; seed the rest now)
    FOR i IN 1..7 LOOP
        -- Insert platform identity if not exists (copy from v2 members)
        INSERT INTO platform_identities (id, email, full_name, phone, identity_status)
        SELECT
            m.id,
            m.email,
            m.full_name,
            m.phone,
            'active'
        FROM members m
        WHERE m.id = accounts[i]
        ON CONFLICT (id) DO NOTHING;

        -- Insert auth record if not exists
        INSERT INTO platform_identity_auth (identity_id, password_hash)
        SELECT m.id, m.hashed_password
        FROM members m
        WHERE m.id = accounts[i]
        ON CONFLICT (identity_id) DO NOTHING;

        -- Create or update membership
        INSERT INTO memberships (
            identity_id, tenant_id, organisation_id,
            membership_number, membership_type, status,
            joined_date, verified_by, verification_date
        )
        VALUES (
            accounts[i], v_tenant_id, v_org_id,
            account_numbers[i], 'standard', 'active',
            CURRENT_DATE, v_superadmin_id, CURRENT_DATE
        )
        ON CONFLICT (identity_id, tenant_id, organisation_id) DO UPDATE
            SET status = 'active',
                membership_number = EXCLUDED.membership_number
        RETURNING id INTO v_membership_id;

        -- Assign role
        INSERT INTO membership_roles (membership_id, role_id, granted_by)
        SELECT
            v_membership_id,
            CASE account_roles[i]
                WHEN 'super_admin'         THEN v_role_super_admin
                WHEN 'national_director'   THEN v_role_nat_director
                WHEN 'chapter_admin'       THEN v_role_chapter_admin
                WHEN 'verifier'            THEN v_role_verifier
                WHEN 'intelligence_analyst'THEN v_role_analyst
                WHEN 'verified_member'     THEN v_role_verified_member
                WHEN 'standard_member'     THEN v_role_standard_member
            END,
            v_superadmin_id
        WHERE v_membership_id IS NOT NULL
        ON CONFLICT (membership_id, role_id) DO NOTHING;

        RAISE NOTICE 'Seeded membership: % → % (%)', account_numbers[i], account_roles[i], accounts[i];
    END LOOP;

END $$;

-- ------------------------------------------------------------
-- 4. SEED — BIRMINGHAM COHORT AS INVITED MEMBERSHIPS
-- Maps cohort members (000101-000110) to RTIFN invited memberships
-- ------------------------------------------------------------
DO $$
DECLARE
    v_tenant_id UUID := '10000000-0000-0000-0000-000000000001';
    v_org_id    UUID := 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';
    v_role_id   UUID;
    v_membership_id UUID;
    r RECORD;
BEGIN
    SELECT id INTO v_role_id FROM kernel_roles
    WHERE name = 'standard_member' AND tenant_id = v_tenant_id;

    FOR r IN
        SELECT id, email, full_name, phone, membership_number, hashed_password
        FROM members
        WHERE membership_number BETWEEN 'NDIP-2026-000101' AND 'NDIP-2026-000110'
        AND is_active = FALSE
        ORDER BY membership_number
    LOOP
        -- Create platform identity for cohort member
        INSERT INTO platform_identities (id, email, full_name, phone, identity_status)
        VALUES (r.id, r.email, r.full_name, r.phone, 'active')
        ON CONFLICT (id) DO NOTHING;

        -- Auth record (INVITED members cannot login — placeholder hash prevents access)
        INSERT INTO platform_identity_auth (identity_id, password_hash)
        VALUES (r.id, r.hashed_password)
        ON CONFLICT (identity_id) DO NOTHING;

        -- Create invited membership
        INSERT INTO memberships (
            identity_id, tenant_id, organisation_id,
            membership_number, membership_type, status
        )
        VALUES (
            r.id, v_tenant_id, v_org_id,
            r.membership_number, 'founding', 'invited'
        )
        ON CONFLICT (identity_id, tenant_id, organisation_id) DO UPDATE
            SET status = 'invited',
                membership_type = 'founding',
                membership_number = EXCLUDED.membership_number
        RETURNING id INTO v_membership_id;

        -- Assign standard_member role (pending activation)
        INSERT INTO membership_roles (membership_id, role_id)
        SELECT v_membership_id, v_role_id
        WHERE v_membership_id IS NOT NULL
        ON CONFLICT (membership_id, role_id) DO NOTHING;

        RAISE NOTICE 'Seeded cohort membership: % (invited)', r.membership_number;
    END LOOP;

END $$;

-- ------------------------------------------------------------
-- 5. UPDATE platform_config
-- ------------------------------------------------------------
INSERT INTO platform_config (key, value)
VALUES ('platform_version', '"D5A-S3"')
ON CONFLICT (key) DO UPDATE SET value = '"D5A-S3"', updated_at = now();

-- ------------------------------------------------------------
-- 6. VERIFICATION — D5A-S3 Complete Check
-- ------------------------------------------------------------
DO $$
DECLARE
    v_memberships       INT;
    v_active            INT;
    v_invited           INT;
    v_membership_roles  INT;
    v_superadmin_role   TEXT;
BEGIN
    SELECT COUNT(*) INTO v_memberships      FROM memberships;
    SELECT COUNT(*) INTO v_active           FROM memberships WHERE status = 'active';
    SELECT COUNT(*) INTO v_invited          FROM memberships WHERE status = 'invited';
    SELECT COUNT(*) INTO v_membership_roles FROM membership_roles;

    -- Check superadmin has correct role
    SELECT kr.name INTO v_superadmin_role
    FROM memberships m
    JOIN membership_roles mr ON mr.membership_id = m.id
    JOIN kernel_roles kr ON kr.id = mr.role_id
    WHERE m.membership_number = 'NDIP-2026-000001'
    LIMIT 1;

    RAISE NOTICE '=== D5A-S3 MEMBERSHIP ENGINE — VERIFICATION ===';
    RAISE NOTICE 'memberships total:    % (expect 17)', v_memberships;
    RAISE NOTICE 'memberships active:   % (expect 7)',  v_active;
    RAISE NOTICE 'memberships invited:  % (expect 10)', v_invited;
    RAISE NOTICE 'membership_roles:     % (expect 17)', v_membership_roles;
    RAISE NOTICE 'superadmin role:      %',             v_superadmin_role;
    RAISE NOTICE '=== D5A-S3 COMPLETE ===';

    IF v_memberships < 17 THEN
        RAISE EXCEPTION 'memberships count too low — expected at least 17';
    END IF;
    IF v_active < 7 THEN
        RAISE EXCEPTION 'active memberships too low — expected 7';
    END IF;
    IF v_superadmin_role IS NULL THEN
        RAISE EXCEPTION 'superadmin role not assigned — membership seeding failed';
    END IF;
END $$;

COMMIT;

-- ============================================================
-- D5A-S3 complete.
-- New tables: memberships, membership_roles
-- Seeded: 7 active RTIFN test account memberships
--         10 invited Birmingham cohort memberships
-- RLS applied to: memberships
-- Next: write /api/v3/memberships/ and /api/v3/orgs/ routes
-- ============================================================
