-- ============================================================
-- NDIP on Orion Platform Kernel
-- Phase D5A — Stage 6: Donations & Communications Engine
-- d5a_s6_donations_communications.sql
-- ============================================================
-- Orion Kernel capability — domain-agnostic record primitives
-- Donations: structured financial contribution records
-- Communications: structured organisational correspondence records
--
-- EXPLICITLY NOT IMPLEMENTED:
--   payment processing, payment gateways, card processing,
--   messaging delivery, email sending, SMS, WhatsApp,
--   bulk messaging, campaigns, donor profiling, political targeting
--
-- ward_sponsorships: UNTOUCHED
-- platform_projects: UNTOUCHED
-- S1-S5 tables: UNTOUCHED
--
-- Archive convention: is_archived=TRUE (no HTTP DELETE)
-- Currency: FLOAT (consistent with existing budget_naira pattern)
-- Idempotent: safe to re-run
-- ============================================================

BEGIN;

-- Confirm ward_sponsorships is untouched (stop if missing)
DO $$
DECLARE v INT;
BEGIN
    SELECT COUNT(*) INTO v FROM ward_sponsorships;
    RAISE NOTICE 'ward_sponsorships: % rows (CONFIRMED UNTOUCHED)', v;
END $$;

-- ------------------------------------------------------------
-- 1. DONATIONS TABLE
-- Structured financial contribution records — NOT payment processing
-- tenant_id nullable = independent project donations
-- donor_identity_id nullable = anonymous/external donors
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS donations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Tenant ownership — nullable for independent project donations
    tenant_id               UUID REFERENCES tenants(id),

    -- Donor — all nullable to support anonymous/external donors
    donor_identity_id       UUID REFERENCES platform_identities(id),
    donor_organisation_id   UUID REFERENCES organisations(id),
    donor_external_name     TEXT,           -- for donors not on platform

    -- Project linkage — nullable
    project_id              UUID REFERENCES projects(id),

    -- Contribution classification
    donation_type           TEXT NOT NULL CHECK (donation_type IN (
                                'donation', 'sponsorship', 'grant',
                                'in_kind', 'pledge', 'subscription', 'other'
                            )),

    -- Financial fields
    -- amount nullable for in-kind contributions
    amount                  FLOAT,
    currency                TEXT NOT NULL DEFAULT 'GBP',

    -- Opaque external reference only — NOT payment credentials
    -- Never store card numbers, bank credentials, CVVs
    payment_reference       TEXT,

    -- Temporal
    donation_date           DATE NOT NULL,

    -- Lifecycle status
    status                  TEXT NOT NULL DEFAULT 'recorded' CHECK (status IN (
                                'recorded', 'submitted', 'verified',
                                'rejected', 'archived'
                            )),

    -- Notes
    notes                   TEXT,

    -- Verification stubs — full S7 engine deferred
    -- These fields mirror S4/S5 pattern for S7 compatibility
    verified_by             UUID REFERENCES platform_identities(id),
    verified_at             TIMESTAMPTZ,
    verification_notes      TEXT,

    -- Provenance
    recorded_by             UUID NOT NULL REFERENCES platform_identities(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_archived             BOOL NOT NULL DEFAULT FALSE,

    -- Financial record access is separate from project visibility
    -- At least one donor identifier or external name is expected
    -- (soft constraint — enforced at API layer)
    CONSTRAINT ck_donation_has_donor CHECK (
        donor_identity_id IS NOT NULL
        OR donor_organisation_id IS NOT NULL
        OR donor_external_name IS NOT NULL
    )
);

-- Indexes
CREATE INDEX IF NOT EXISTS ix_donations_tenant_id          ON donations(tenant_id);
CREATE INDEX IF NOT EXISTS ix_donations_donor_identity     ON donations(donor_identity_id);
CREATE INDEX IF NOT EXISTS ix_donations_donor_org          ON donations(donor_organisation_id);
CREATE INDEX IF NOT EXISTS ix_donations_project_id         ON donations(project_id);
CREATE INDEX IF NOT EXISTS ix_donations_status             ON donations(status);
CREATE INDEX IF NOT EXISTS ix_donations_date               ON donations(donation_date);
CREATE INDEX IF NOT EXISTS ix_donations_recorded_by        ON donations(recorded_by);
-- Partial index for independent project donations
CREATE INDEX IF NOT EXISTS ix_donations_independent
    ON donations(id) WHERE tenant_id IS NULL;

-- RLS — FINANCIAL VISIBILITY IS SEPARATE FROM PROJECT VISIBILITY
-- Tenant-owned donations: visible only to matching tenant
-- Independent project donations: NOT automatically visible to project participants
-- Default: private to recording tenant or platform admin
ALTER TABLE donations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON donations;
CREATE POLICY tenant_isolation ON donations
    USING (
        -- Tenant-owned: match tenant context
        (tenant_id IS NOT NULL AND
         tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::uuid)
        OR
        -- Platform admin bypass (null tenant context = platform admin)
        NULLIF(current_setting('app.current_tenant_id', TRUE), '') IS NULL
        -- NOTE: Independent project donations (tenant_id IS NULL) are NOT
        -- automatically visible to project participants. Financial visibility
        -- requires explicit tenant membership. API layer enforces this.
    );

DO $$ BEGIN RAISE NOTICE 'donations table created with RLS (financial visibility restricted)'; END $$;

-- ------------------------------------------------------------
-- 2. COMMUNICATIONS TABLE
-- Structured organisational correspondence records — NOT a messaging platform
-- Records that a communication occurred, with provenance
-- Does NOT send, deliver, or queue messages
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS communications (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Tenant context — nullable for independent project communications
    tenant_id               UUID REFERENCES tenants(id),

    -- Participants
    sender_identity_id      UUID NOT NULL REFERENCES platform_identities(id),
    recipient_identity_id   UUID REFERENCES platform_identities(id),    -- nullable = external recipient
    recipient_external      TEXT,                                        -- external recipient name/reference

    -- Organisational context
    organisation_id         UUID REFERENCES organisations(id),

    -- Project linkage — nullable
    project_id              UUID REFERENCES projects(id),

    -- Classification
    communication_type      TEXT NOT NULL CHECK (communication_type IN (
                                'email', 'letter', 'meeting_minutes',
                                'phone_call', 'report', 'memo',
                                'correspondence', 'other'
                            )),

    -- Content metadata (NOT the message itself — record-only)
    subject                 TEXT NOT NULL,
    reference               TEXT,           -- external reference number/ID

    -- Temporal
    communication_date      DATE NOT NULL,

    -- Lifecycle
    status                  TEXT NOT NULL DEFAULT 'draft' CHECK (status IN (
                                'draft', 'sent', 'received',
                                'acknowledged', 'archived'
                            )),

    -- Notes / summary
    notes                   TEXT,

    -- Provenance
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_archived             BOOL NOT NULL DEFAULT FALSE
);

-- Indexes
CREATE INDEX IF NOT EXISTS ix_comms_tenant_id          ON communications(tenant_id);
CREATE INDEX IF NOT EXISTS ix_comms_sender             ON communications(sender_identity_id);
CREATE INDEX IF NOT EXISTS ix_comms_recipient          ON communications(recipient_identity_id);
CREATE INDEX IF NOT EXISTS ix_comms_organisation_id    ON communications(organisation_id);
CREATE INDEX IF NOT EXISTS ix_comms_project_id         ON communications(project_id);
CREATE INDEX IF NOT EXISTS ix_comms_status             ON communications(status);
CREATE INDEX IF NOT EXISTS ix_comms_date               ON communications(communication_date);

-- RLS — tenant isolation
ALTER TABLE communications ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON communications;
CREATE POLICY tenant_isolation ON communications
    USING (
        -- Tenant-owned communications
        (tenant_id IS NOT NULL AND
         tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::uuid)
        OR
        -- Sender can always see their own communications regardless of tenant
        sender_identity_id = NULLIF(current_setting('app.current_identity_id', TRUE), '')::uuid
        OR
        -- Recipient (if platform identity) can see communications addressed to them
        recipient_identity_id = NULLIF(current_setting('app.current_identity_id', TRUE), '')::uuid
        OR
        -- Platform admin
        NULLIF(current_setting('app.current_tenant_id', TRUE), '') IS NULL
    );

DO $$ BEGIN RAISE NOTICE 'communications table created with RLS'; END $$;

-- ------------------------------------------------------------
-- 3. Update platform_config
-- ------------------------------------------------------------
INSERT INTO platform_config (key, value)
VALUES ('platform_version', '"D5A-S6"')
ON CONFLICT (key) DO UPDATE SET value = '"D5A-S6"', updated_at = now();

-- ------------------------------------------------------------
-- 4. Verification
-- ------------------------------------------------------------
DO $$
DECLARE
    v_donations         INT;
    v_comms             INT;
    v_ws                INT;
    v_ws_cols           INT;
    v_don_rls           INT;
    v_com_rls           INT;
BEGIN
    SELECT COUNT(*) INTO v_donations   FROM donations;
    SELECT COUNT(*) INTO v_comms       FROM communications;
    SELECT COUNT(*) INTO v_ws          FROM ward_sponsorships;
    SELECT COUNT(*) INTO v_ws_cols FROM information_schema.columns
        WHERE table_name = 'ward_sponsorships';
    SELECT COUNT(*) INTO v_don_rls FROM pg_policies
        WHERE tablename = 'donations' AND policyname = 'tenant_isolation';
    SELECT COUNT(*) INTO v_com_rls FROM pg_policies
        WHERE tablename = 'communications' AND policyname = 'tenant_isolation';

    RAISE NOTICE '=== D5A-S6 DONATIONS & COMMUNICATIONS — VERIFICATION ===';
    RAISE NOTICE 'donations table:           created (% rows)', v_donations;
    RAISE NOTICE 'communications table:      created (% rows)', v_comms;
    RAISE NOTICE 'ward_sponsorships:         % rows, % columns (UNTOUCHED)', v_ws, v_ws_cols;
    RAISE NOTICE 'donations RLS policy:      % (1=present)', v_don_rls;
    RAISE NOTICE 'communications RLS policy: % (1=present)', v_com_rls;
    RAISE NOTICE 'platform_version:          D5A-S6';

    IF v_don_rls = 0 THEN
        RAISE EXCEPTION 'donations RLS policy not created';
    END IF;
    IF v_com_rls = 0 THEN
        RAISE EXCEPTION 'communications RLS policy not created';
    END IF;
    IF v_ws != 9 THEN
        RAISE EXCEPTION 'ward_sponsorships row count changed — expected 9, got %', v_ws;
    END IF;

    RAISE NOTICE '=== D5A-S6 COMPLETE ===';
END $$;

COMMIT;

-- ============================================================
-- D5A-S6 complete.
-- New tables: donations, communications
-- RLS: tenant_isolation on both tables
-- Financial visibility: donations NOT visible to project participants
-- Archive convention: is_archived=TRUE (no HTTP DELETE)
-- ward_sponsorships: UNTOUCHED (9 rows confirmed)
-- Payment processing: NOT IMPLEMENTED
-- Messaging delivery: NOT IMPLEMENTED
-- platform_version: D5A-S6
-- ============================================================
