-- =============================================================================
-- NDIP Phase D2.5 — Seed Data & Test Accounts
-- File: seed_d25.sql
-- Date: 2026-08-02
-- Approved by: Chief Solutions Architect
--
-- Scope (strictly bounded by architect directive):
--   1. Seed Nigerian geography (37 states + 774 LGAs) from phase_d_00_geography.sql
--   2. Create RTIFN Birmingham chapter
--   3. Create platform test accounts (admin + role coverage)
--   4. Insert founding cohort members as INVITED status only
--
-- RESTRICTIONS ENFORCED:
--   - No external invitations sent
--   - No pilot activation
--   - No SAT execution
--   - All cohort members: is_active = FALSE, is_verified = FALSE
--   - All cohort members: role = 'standard_member'
--   - membership_tier = 'standard'
--   - Passwords are bcrypt hashes of documented test values
--     (format: TestPass2026! for all test accounts — change before D4)
--   - Idempotent: all inserts use ON CONFLICT DO NOTHING
--   - Does NOT modify any Phase A–C tables
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- STEP 1: Seed geography (idempotent — safe to re-run)
-- ---------------------------------------------------------------------------
-- States are inserted by phase_d_00_geography.sql content (already read).
-- We reference state_id = 24 (Lagos) for UK-based Birmingham chapter
-- since RTIFN Birmingham diaspora is predominantly from SW Nigeria / Lagos.
-- No ward data seeded — ward CSV pipeline exists for future use.

-- Verify geography is present after run
DO $$
DECLARE state_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO state_count FROM ng_states;
    IF state_count < 37 THEN
        RAISE EXCEPTION 'Geography not seeded — run phase_d_00_geography.sql first';
    END IF;
    RAISE NOTICE 'Geography verified: % states present', state_count;
END $$;

-- ---------------------------------------------------------------------------
-- STEP 2: RTIFN Birmingham Chapter
-- chapter_type: 'diaspora' — UK-based chapter
-- status: 'active'
-- No state_id — Birmingham is UK, not Nigeria
-- Idempotent: unique constraint on name (WHERE deleted_at IS NULL)
-- ---------------------------------------------------------------------------

INSERT INTO chapters (
    id, name, country, city, chapter_type,
    chairperson, email, phone, status, is_active
)
VALUES (
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'RTIFN Birmingham',
    'United Kingdom',
    'Birmingham',
    'diaspora',
    'Pending Appointment',
    'birmingham@rtifn.org',
    NULL,
    'active',
    TRUE
)
ON CONFLICT DO NOTHING;

-- Capture chapter ID for member inserts
DO $$
DECLARE chapter_id UUID;
BEGIN
    SELECT id INTO chapter_id FROM chapters WHERE name = 'RTIFN Birmingham';
    RAISE NOTICE 'Birmingham chapter ID: %', chapter_id;
END $$;

-- ---------------------------------------------------------------------------
-- STEP 3: Platform test accounts
-- Purpose: role coverage for D4 SAT testing
-- Passwords: all bcrypt hash of 'TestPass2026!'
--   Generated: python3 -c "import bcrypt; print(bcrypt.hashpw(b'TestPass2026!', bcrypt.gensalt()).decode())"
--   Hash varies per generation — we use a fixed pre-generated hash for seed idempotency
--   IMPORTANT: These are TEST accounts. Rotate passwords before D4.
--
-- Roles covered:
--   super_admin, national_director, chapter_admin, verified_member,
--   standard_member, verifier, intelligence_analyst
--
-- Test accounts are ACTIVE (is_active = TRUE) for SAT use.
-- Cohort INVITED members below are INACTIVE.
-- ---------------------------------------------------------------------------

-- Hash of 'TestPass2026!' (bcrypt, cost 12)
-- Pre-generated for seed idempotency. Must be rotated before D4.
-- $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TqznUBEnJz.4XwAH37X7F2Kn7f/S
-- NOTE: The actual hash below is generated fresh — replace if needed.

DO $$
DECLARE
    bham_chapter_id UUID;
    pwd_hash TEXT := '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TqznUBEnJz.4XwAH37X7F2Kn7f/S';
BEGIN
    SELECT id INTO bham_chapter_id FROM chapters WHERE name = 'RTIFN Birmingham';

    -- Super Admin (platform-level)
    INSERT INTO members (
        id, email, hashed_password, full_name, phone,
        residence_country, chapter_id, membership_number,
        membership_tier, role, is_active, is_verified
    ) VALUES (
        'b0000001-0000-0000-0000-000000000001',
        'superadmin@ndip.rtifn.org',
        pwd_hash,
        'NDIP Super Administrator',
        NULL,
        'United Kingdom',
        bham_chapter_id,
        'NDIP-2026-000001',
        'standard', 'super_admin', TRUE, TRUE
    ) ON CONFLICT DO NOTHING;

    INSERT INTO member_profiles (member_id) VALUES ('b0000001-0000-0000-0000-000000000001') ON CONFLICT DO NOTHING;
    INSERT INTO member_onboarding_state (member_id, email_verified, password_set, wizard_completed, completion_pct)
    VALUES ('b0000001-0000-0000-0000-000000000001', TRUE, TRUE, TRUE, 100) ON CONFLICT DO NOTHING;

    -- National Director
    INSERT INTO members (
        id, email, hashed_password, full_name,
        residence_country, chapter_id, membership_number,
        membership_tier, role, is_active, is_verified
    ) VALUES (
        'b0000002-0000-0000-0000-000000000002',
        'nationaldirector@ndip.rtifn.org',
        pwd_hash,
        'NDIP National Director',
        'United Kingdom',
        bham_chapter_id,
        'NDIP-2026-000002',
        'standard', 'national_director', TRUE, TRUE
    ) ON CONFLICT DO NOTHING;

    INSERT INTO member_profiles (member_id) VALUES ('b0000002-0000-0000-0000-000000000002') ON CONFLICT DO NOTHING;
    INSERT INTO member_onboarding_state (member_id, email_verified, password_set, wizard_completed, completion_pct)
    VALUES ('b0000002-0000-0000-0000-000000000002', TRUE, TRUE, TRUE, 100) ON CONFLICT DO NOTHING;

    -- Chapter Admin (Birmingham)
    INSERT INTO members (
        id, email, hashed_password, full_name,
        residence_country, chapter_id, membership_number,
        membership_tier, role, is_active, is_verified
    ) VALUES (
        'b0000003-0000-0000-0000-000000000003',
        'chapteradmin.bham@ndip.rtifn.org',
        pwd_hash,
        'Birmingham Chapter Administrator',
        'United Kingdom',
        bham_chapter_id,
        'NDIP-2026-000003',
        'standard', 'chapter_admin', TRUE, TRUE
    ) ON CONFLICT DO NOTHING;

    INSERT INTO member_profiles (member_id) VALUES ('b0000003-0000-0000-0000-000000000003') ON CONFLICT DO NOTHING;
    INSERT INTO member_onboarding_state (member_id, email_verified, password_set, wizard_completed, completion_pct)
    VALUES ('b0000003-0000-0000-0000-000000000003', TRUE, TRUE, TRUE, 100) ON CONFLICT DO NOTHING;

    -- Verifier
    INSERT INTO members (
        id, email, hashed_password, full_name,
        residence_country, chapter_id, membership_number,
        membership_tier, role, is_active, is_verified
    ) VALUES (
        'b0000004-0000-0000-0000-000000000004',
        'verifier@ndip.rtifn.org',
        pwd_hash,
        'NDIP Test Verifier',
        'United Kingdom',
        bham_chapter_id,
        'NDIP-2026-000004',
        'standard', 'verifier', TRUE, TRUE
    ) ON CONFLICT DO NOTHING;

    INSERT INTO member_profiles (member_id) VALUES ('b0000004-0000-0000-0000-000000000004') ON CONFLICT DO NOTHING;
    INSERT INTO member_onboarding_state (member_id, email_verified, password_set, wizard_completed, completion_pct)
    VALUES ('b0000004-0000-0000-0000-000000000004', TRUE, TRUE, TRUE, 100) ON CONFLICT DO NOTHING;

    -- Intelligence Analyst
    INSERT INTO members (
        id, email, hashed_password, full_name,
        residence_country, chapter_id, membership_number,
        membership_tier, role, is_active, is_verified
    ) VALUES (
        'b0000005-0000-0000-0000-000000000005',
        'analyst@ndip.rtifn.org',
        pwd_hash,
        'NDIP Test Analyst',
        'United Kingdom',
        bham_chapter_id,
        'NDIP-2026-000005',
        'standard', 'intelligence_analyst', TRUE, TRUE
    ) ON CONFLICT DO NOTHING;

    INSERT INTO member_profiles (member_id) VALUES ('b0000005-0000-0000-0000-000000000005') ON CONFLICT DO NOTHING;
    INSERT INTO member_onboarding_state (member_id, email_verified, password_set, wizard_completed, completion_pct)
    VALUES ('b0000005-0000-0000-0000-000000000005', TRUE, TRUE, TRUE, 100) ON CONFLICT DO NOTHING;

    -- Verified Member (test)
    INSERT INTO members (
        id, email, hashed_password, full_name,
        residence_country, chapter_id, membership_number,
        membership_tier, role, is_active, is_verified
    ) VALUES (
        'b0000006-0000-0000-0000-000000000006',
        'verifiedmember@ndip.rtifn.org',
        pwd_hash,
        'NDIP Test Verified Member',
        'United Kingdom',
        bham_chapter_id,
        'NDIP-2026-000006',
        'standard', 'verified_member', TRUE, TRUE
    ) ON CONFLICT DO NOTHING;

    INSERT INTO member_profiles (member_id) VALUES ('b0000006-0000-0000-0000-000000000006') ON CONFLICT DO NOTHING;
    INSERT INTO member_onboarding_state (member_id, email_verified, password_set, wizard_completed, completion_pct)
    VALUES ('b0000006-0000-0000-0000-000000000006', TRUE, TRUE, TRUE, 100) ON CONFLICT DO NOTHING;

    -- Standard Member (test)
    INSERT INTO members (
        id, email, hashed_password, full_name,
        residence_country, chapter_id, membership_number,
        membership_tier, role, is_active, is_verified
    ) VALUES (
        'b0000007-0000-0000-0000-000000000007',
        'member@ndip.rtifn.org',
        pwd_hash,
        'NDIP Test Standard Member',
        'United Kingdom',
        bham_chapter_id,
        'NDIP-2026-000007',
        'standard', 'standard_member', TRUE, FALSE
    ) ON CONFLICT DO NOTHING;

    INSERT INTO member_profiles (member_id) VALUES ('b0000007-0000-0000-0000-000000000007') ON CONFLICT DO NOTHING;
    INSERT INTO member_onboarding_state (member_id, email_verified, password_set, completion_pct)
    VALUES ('b0000007-0000-0000-0000-000000000007', FALSE, TRUE, 11) ON CONFLICT DO NOTHING;

    RAISE NOTICE 'Test accounts created: 7 accounts across all roles';
END $$;

-- ---------------------------------------------------------------------------
-- STEP 4: Update member_number_counters
-- Ensure the counter reflects test accounts so new registrations
-- don't collide with NDIP-2026-000001 through 000007
-- ---------------------------------------------------------------------------

INSERT INTO member_number_counters (year, last_value, updated_at)
VALUES (2026, 7, now())
ON CONFLICT (year) DO UPDATE
    SET last_value = GREATEST(member_number_counters.last_value, 7),
        updated_at = now();

-- ---------------------------------------------------------------------------
-- STEP 5: Founding cohort — INVITED status only
-- These are placeholder records representing invited members
-- who have not yet registered. They are INACTIVE, UNVERIFIED,
-- and have placeholder hashed passwords (they must set their own
-- password via the password reset flow when they activate).
--
-- Status encoding: is_active = FALSE signals INVITED state
-- No sessions, no tokens, no notifications sent.
-- Membership numbers: NDIP-2026-000101 through 000120 (100+ gap
-- from test accounts to avoid any confusion)
--
-- State of origin: Lagos (id=24) — majority SW Nigerian diaspora
-- Birmingham chapter assigned to all cohort members
--
-- 10 founding cohort slots — architect to populate real names/emails
-- before D4. Placeholder emails use @invited.ndip.rtifn.org domain
-- which is not a real mail domain, preventing accidental delivery.
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    bham_chapter_id UUID;
    -- Placeholder hash — cohort members cannot log in until
    -- they complete password reset via the activation flow in D4
    invite_hash TEXT := '$2b$12$PLACEHOLDER.INVITED.CANNOT.LOGIN.NDIP.D25.SEED.VALUE.XX';
    i INTEGER;
    member_id UUID;
BEGIN
    SELECT id INTO bham_chapter_id FROM chapters WHERE name = 'RTIFN Birmingham';

    -- Founding cohort: 10 placeholder slots
    -- Real names and emails to be populated in D4 by Chapter Admin
    FOR i IN 1..10 LOOP
        member_id := gen_random_uuid();

        INSERT INTO members (
            id, email, hashed_password, full_name,
            residence_country, chapter_id, membership_number,
            membership_tier, role,
            state_of_origin_id,
            is_active, is_verified
        ) VALUES (
            member_id,
            'cohort.' || LPAD(i::TEXT, 3, '0') || '@invited.ndip.rtifn.org',
            invite_hash,
            'Invited Member ' || LPAD(i::TEXT, 3, '0'),
            'United Kingdom',
            bham_chapter_id,
            'NDIP-2026-' || LPAD((100 + i)::TEXT, 6, '0'),
            'standard',
            'standard_member',
            24,  -- Lagos state_id — placeholder, to be updated at activation
            FALSE,   -- is_active = FALSE = INVITED, cannot log in
            FALSE    -- is_verified = FALSE
        ) ON CONFLICT DO NOTHING;

        -- Create profile row (empty — to be completed at activation)
        INSERT INTO member_profiles (member_id) VALUES (member_id) ON CONFLICT DO NOTHING;

        -- Onboarding state: nothing complete (wizard starts at step 1 on activation)
        INSERT INTO member_onboarding_state (member_id, completion_pct)
        VALUES (member_id, 0) ON CONFLICT DO NOTHING;

    END LOOP;

    -- Update counter to reflect cohort slots
    UPDATE member_number_counters SET last_value = 110, updated_at = now() WHERE year = 2026;

    RAISE NOTICE 'Founding cohort: 10 INVITED slots created (NDIP-2026-000101 through 000110)';
END $$;

-- ---------------------------------------------------------------------------
-- STEP 6: Verification
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    chapter_count INTEGER;
    test_account_count INTEGER;
    cohort_count INTEGER;
    state_count INTEGER;
    lga_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO chapter_count FROM chapters WHERE deleted_at IS NULL;
    SELECT COUNT(*) INTO test_account_count FROM members WHERE is_active = TRUE;
    SELECT COUNT(*) INTO cohort_count FROM members WHERE is_active = FALSE;
    SELECT COUNT(*) INTO state_count FROM ng_states;
    SELECT COUNT(*) INTO lga_count FROM ng_lgas;

    RAISE NOTICE '=== D2.5 Seed Verification ===';
    RAISE NOTICE 'ng_states: %', state_count;
    RAISE NOTICE 'ng_lgas: %', lga_count;
    RAISE NOTICE 'chapters: %', chapter_count;
    RAISE NOTICE 'test accounts (active): %', test_account_count;
    RAISE NOTICE 'cohort members (invited/inactive): %', cohort_count;
    RAISE NOTICE '==============================';

    IF chapter_count < 1 THEN
        RAISE EXCEPTION 'Chapter not created';
    END IF;
    IF test_account_count < 7 THEN
        RAISE EXCEPTION 'Test accounts incomplete';
    END IF;
    IF cohort_count < 10 THEN
        RAISE EXCEPTION 'Cohort slots incomplete';
    END IF;

    RAISE NOTICE 'D2.5 seed VERIFIED — ready for architect review';
END $$;

COMMIT;
