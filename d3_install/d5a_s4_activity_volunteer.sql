-- ============================================================
-- NDIP on Orion Platform Kernel
-- Phase D5A — Stage 4: Activity & Volunteer Engine
-- d5a_s4_activity_volunteer.sql
-- ============================================================
-- Orion Kernel capability — domain-agnostic activity infrastructure
-- Supports: RTIFN, civic orgs, universities, NGOs, businesses,
--           government programmes, independent projects
-- Safe to re-run (idempotent)
-- Additive only — no existing tables modified
-- Depends on: D5A-S1, S2, S3 complete + ng_wards populated
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 1. POPULATE activity_types.detail_schema
-- Machine-readable validation schema for each activity type
-- ------------------------------------------------------------
UPDATE activity_types SET detail_schema = '{
  "required": [],
  "optional": ["description", "participants", "outcome", "external_link"],
  "evidence_types": ["photo", "document", "video"],
  "location_required": true
}'::jsonb WHERE name = 'outreach';

UPDATE activity_types SET detail_schema = '{
  "required": [],
  "optional": ["volunteer_count", "hours", "skills_used", "organisation_supported", "outcome"],
  "evidence_types": ["photo", "document", "certificate"],
  "location_required": true
}'::jsonb WHERE name = 'volunteering';

UPDATE activity_types SET detail_schema = '{
  "required": [],
  "optional": ["meeting_type", "attendees", "agenda", "decisions", "follow_up"],
  "evidence_types": ["minutes", "photo", "document"],
  "location_required": false
}'::jsonb WHERE name = 'meeting';

UPDATE activity_types SET detail_schema = '{
  "required": ["stakeholder_name", "stakeholder_position"],
  "optional": ["organisation", "meeting_type", "outcome", "follow_up_date", "follow_up_required"],
  "evidence_types": ["photo", "document", "correspondence", "minutes"],
  "location_required": false
}'::jsonb WHERE name = 'stakeholder_engagement';

UPDATE activity_types SET detail_schema = '{
  "required": ["government_body", "contact_name"],
  "optional": ["contact_position", "meeting_type", "outcome", "reference_number", "follow_up"],
  "evidence_types": ["photo", "document", "correspondence", "minutes"],
  "location_required": false
}'::jsonb WHERE name = 'government_engagement';

UPDATE activity_types SET detail_schema = '{
  "required": [],
  "optional": ["ward_executive_name", "ward_executive_contact", "registration_reference",
               "registration_date", "participant_name", "engagement_notes"],
  "evidence_types": ["photo", "document", "certificate"],
  "location_required": true,
  "ward_required": true
}'::jsonb WHERE name = 'ward_visit';

UPDATE activity_types SET detail_schema = '{
  "required": [],
  "optional": ["event_name", "participant_count", "outcome", "community_name"],
  "evidence_types": ["photo", "document", "video"],
  "location_required": true
}'::jsonb WHERE name = 'community_activity';

UPDATE activity_types SET detail_schema = '{
  "required": ["media_outlet"],
  "optional": ["journalist_name", "topic", "link", "publication_date", "reach"],
  "evidence_types": ["document", "link", "photo"],
  "location_required": false
}'::jsonb WHERE name = 'media_activity';

UPDATE activity_types SET detail_schema = '{
  "required": [],
  "optional": ["campaign_type", "area_covered", "team_size", "materials_distributed", "contacts_made"],
  "evidence_types": ["photo", "document", "video"],
  "location_required": true
}'::jsonb WHERE name = 'campaign';

UPDATE activity_types SET detail_schema = '{
  "required": [],
  "optional": ["project_name", "milestone", "deliverable", "hours", "outcome"],
  "evidence_types": ["document", "photo", "report"],
  "location_required": false
}'::jsonb WHERE name = 'project_work';

UPDATE activity_types SET detail_schema = '{
  "required": ["mentee_identifier"],
  "optional": ["session_type", "topics_covered", "duration_hours", "outcome"],
  "evidence_types": ["document"],
  "location_required": false,
  "privacy_note": "Mentee identity stored as opaque identifier only"
}'::jsonb WHERE name = 'mentoring';

UPDATE activity_types SET detail_schema = '{
  "required": ["training_name"],
  "optional": ["provider", "topic", "duration_hours", "certification", "participant_count"],
  "evidence_types": ["certificate", "document", "photo"],
  "location_required": false
}'::jsonb WHERE name = 'training';

UPDATE activity_types SET detail_schema = '{
  "required": ["amount", "currency"],
  "optional": ["recipient_organisation", "campaign", "payment_reference", "gift_aid_eligible"],
  "evidence_types": ["document", "receipt"],
  "location_required": false
}'::jsonb WHERE name = 'donation';

UPDATE activity_types SET detail_schema = '{
  "required": ["channel", "subject"],
  "optional": ["recipient", "reference", "outcome"],
  "evidence_types": ["document", "correspondence"],
  "location_required": false
}'::jsonb WHERE name = 'communication';

UPDATE activity_types SET detail_schema = '{
  "required": [],
  "optional": ["research_type", "topic", "output", "publication_link", "institution"],
  "evidence_types": ["document", "report", "link"],
  "location_required": false
}'::jsonb WHERE name = 'research';

DO $$ BEGIN
    RAISE NOTICE 'activity_types.detail_schema populated for all 15 types';
END $$;

-- ------------------------------------------------------------
-- 2. ACTIVITIES TABLE
-- Orion Kernel capability — domain-agnostic
-- One table for all activity types via type discriminator
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activities (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    recorded_by             UUID NOT NULL REFERENCES platform_identities(id),
    organisation_id         UUID REFERENCES organisations(id),
    -- S5 project reference (FK added when projects table exists)
    -- project_id UUID REFERENCES projects(id)
    activity_type_id        UUID NOT NULL REFERENCES activity_types(id),
    title                   TEXT NOT NULL,
    description             TEXT,
    activity_date           DATE NOT NULL,
    activity_details        JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Geographic resolution (all nullable — activity may be non-geographic)
    location_country_id     UUID REFERENCES countries(id),
    location_state_id       INT REFERENCES ng_states(id),
    location_lga_id         INT REFERENCES ng_lgas(id),
    location_ward_id        INT REFERENCES ng_wards(id),
    gps_lat                 FLOAT,
    gps_lng                 FLOAT,
    location_text           TEXT,
    -- Verification lifecycle (driven by workflow_definitions)
    verification_status     TEXT NOT NULL DEFAULT 'Draft' CHECK (verification_status IN (
                                'Draft', 'Submitted', 'Under Review', 'Verified', 'Rejected', 'Archived'
                            )),
    verified_by             UUID REFERENCES platform_identities(id),
    verified_at             TIMESTAMPTZ,
    verification_notes      TEXT,
    rejection_reason        TEXT,
    -- Provenance
    submitted_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Soft deletion — never hard-delete activity records
    is_archived             BOOL NOT NULL DEFAULT FALSE
);

-- Indexes
CREATE INDEX IF NOT EXISTS ix_activities_tenant_id        ON activities(tenant_id);
CREATE INDEX IF NOT EXISTS ix_activities_recorded_by      ON activities(recorded_by);
CREATE INDEX IF NOT EXISTS ix_activities_organisation_id  ON activities(organisation_id);
CREATE INDEX IF NOT EXISTS ix_activities_activity_type_id ON activities(activity_type_id);
CREATE INDEX IF NOT EXISTS ix_activities_activity_date    ON activities(activity_date);
CREATE INDEX IF NOT EXISTS ix_activities_verification     ON activities(verification_status);
CREATE INDEX IF NOT EXISTS ix_activities_state_id         ON activities(location_state_id);
CREATE INDEX IF NOT EXISTS ix_activities_lga_id           ON activities(location_lga_id);
CREATE INDEX IF NOT EXISTS ix_activities_ward_id          ON activities(location_ward_id);

-- RLS
ALTER TABLE activities ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON activities;
CREATE POLICY tenant_isolation ON activities
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::uuid);

DO $$ BEGIN
    RAISE NOTICE 'activities table created with RLS';
END $$;

-- ------------------------------------------------------------
-- 3. VOLUNTEER RECORDS TABLE
-- Orion Kernel capability — domain-agnostic
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS volunteer_records (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    identity_id         UUID NOT NULL REFERENCES platform_identities(id),
    organisation_id     UUID REFERENCES organisations(id),
    -- Activity link (optional — volunteer work may be standalone)
    activity_id         UUID REFERENCES activities(id),
    -- S5 project reference (FK added when projects table exists)
    volunteer_type      TEXT NOT NULL CHECK (volunteer_type IN (
                            'canvassing', 'event_support', 'admin', 'training',
                            'outreach', 'mentoring', 'technical', 'fundraising',
                            'project_work', 'community', 'other'
                        )),
    description         TEXT,
    hours_contributed   FLOAT,
    volunteer_date      DATE NOT NULL,
    -- Geographic resolution
    location_country_id UUID REFERENCES countries(id),
    location_state_id   INT REFERENCES ng_states(id),
    location_lga_id     INT REFERENCES ng_lgas(id),
    location_ward_id    INT REFERENCES ng_wards(id),
    gps_lat             FLOAT,
    gps_lng             FLOAT,
    -- Skills used (JSONB array of skill_ids from global skills table)
    skills_used         JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- Verification lifecycle
    verification_status TEXT NOT NULL DEFAULT 'Draft' CHECK (verification_status IN (
                            'Draft', 'Submitted', 'Under Review', 'Verified', 'Rejected', 'Archived'
                        )),
    verified_by         UUID REFERENCES platform_identities(id),
    verified_at         TIMESTAMPTZ,
    verification_notes  TEXT,
    rejection_reason    TEXT,
    submitted_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_archived         BOOL NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_volunteer_tenant_id       ON volunteer_records(tenant_id);
CREATE INDEX IF NOT EXISTS ix_volunteer_identity_id     ON volunteer_records(identity_id);
CREATE INDEX IF NOT EXISTS ix_volunteer_organisation_id ON volunteer_records(organisation_id);
CREATE INDEX IF NOT EXISTS ix_volunteer_activity_id     ON volunteer_records(activity_id);
CREATE INDEX IF NOT EXISTS ix_volunteer_date            ON volunteer_records(volunteer_date);
CREATE INDEX IF NOT EXISTS ix_volunteer_verification    ON volunteer_records(verification_status);
CREATE INDEX IF NOT EXISTS ix_volunteer_state_id        ON volunteer_records(location_state_id);
CREATE INDEX IF NOT EXISTS ix_volunteer_ward_id         ON volunteer_records(location_ward_id);

ALTER TABLE volunteer_records ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON volunteer_records;
CREATE POLICY tenant_isolation ON volunteer_records
    USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', TRUE), '')::uuid);

DO $$ BEGIN
    RAISE NOTICE 'volunteer_records table created with RLS';
END $$;

-- ------------------------------------------------------------
-- 4. UPDATE platform_config
-- ------------------------------------------------------------
INSERT INTO platform_config (key, value)
VALUES ('platform_version', '"D5A-S4"')
ON CONFLICT (key) DO UPDATE SET value = '"D5A-S4"', updated_at = now();

-- ------------------------------------------------------------
-- 5. VERIFICATION
-- ------------------------------------------------------------
DO $$
DECLARE
    v_activities        INT;
    v_volunteer         INT;
    v_schemas_populated INT;
    v_wards             INT;
BEGIN
    SELECT COUNT(*) INTO v_activities  FROM activities;
    SELECT COUNT(*) INTO v_volunteer   FROM volunteer_records;
    SELECT COUNT(*) INTO v_schemas_populated
        FROM activity_types WHERE detail_schema IS NOT NULL;
    SELECT COUNT(*) INTO v_wards FROM ng_wards;

    RAISE NOTICE '=== D5A-S4 ACTIVITY & VOLUNTEER ENGINE — VERIFICATION ===';
    RAISE NOTICE 'activities table:              created (% rows)', v_activities;
    RAISE NOTICE 'volunteer_records table:       created (% rows)', v_volunteer;
    RAISE NOTICE 'activity_types with schema:    % of 15', v_schemas_populated;
    RAISE NOTICE 'ng_wards available:            %', v_wards;
    RAISE NOTICE 'platform_version:              D5A-S4';

    IF v_schemas_populated < 15 THEN
        RAISE EXCEPTION 'Not all activity_types have detail_schema populated';
    END IF;
    IF v_wards = 0 THEN
        RAISE EXCEPTION 'ng_wards is empty — T1 must complete before S4';
    END IF;

    RAISE NOTICE '=== D5A-S4 COMPLETE ===';
END $$;

COMMIT;

-- ============================================================
-- D5A-S4 complete.
-- New tables: activities, volunteer_records
-- Updated: activity_types.detail_schema (all 15 types)
-- RLS applied to: activities, volunteer_records
-- Geography: activities resolve to country/state/lga/ward
-- Verification: 6-state lifecycle on both tables
-- Next: Write /api/v3/activities/ and /api/v3/volunteer/ routes
-- ============================================================
