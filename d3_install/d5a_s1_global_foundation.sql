-- ============================================================
-- NDIP on Orion Platform Kernel
-- Phase D5A — Stage 1: Global Foundation
-- d5a_s1_global_foundation.sql
-- ============================================================
-- Safe to re-run (idempotent)
-- Additive only — no existing tables modified except ng_wards
-- (nullable code column added)
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 1. COUNTRIES (ISO 3166-1)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS countries (
    id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name    TEXT NOT NULL,
    iso_code CHAR(2) NOT NULL,
    region  TEXT,
    CONSTRAINT ux_countries_iso UNIQUE (iso_code),
    CONSTRAINT ux_countries_name UNIQUE (name)
);

INSERT INTO countries (name, iso_code, region) VALUES
('Afghanistan','AF','Asia'),('Albania','AL','Europe'),('Algeria','DZ','Africa'),
('Andorra','AD','Europe'),('Angola','AO','Africa'),('Antigua and Barbuda','AG','Americas'),
('Argentina','AR','Americas'),('Armenia','AM','Asia'),('Australia','AU','Oceania'),
('Austria','AT','Europe'),('Azerbaijan','AZ','Asia'),('Bahamas','BS','Americas'),
('Bahrain','BH','Asia'),('Bangladesh','BD','Asia'),('Barbados','BB','Americas'),
('Belarus','BY','Europe'),('Belgium','BE','Europe'),('Belize','BZ','Americas'),
('Benin','BJ','Africa'),('Bhutan','BT','Asia'),('Bolivia','BO','Americas'),
('Bosnia and Herzegovina','BA','Europe'),('Botswana','BW','Africa'),('Brazil','BR','Americas'),
('Brunei','BN','Asia'),('Bulgaria','BG','Europe'),('Burkina Faso','BF','Africa'),
('Burundi','BI','Africa'),('Cabo Verde','CV','Africa'),('Cambodia','KH','Asia'),
('Cameroon','CM','Africa'),('Canada','CA','Americas'),('Central African Republic','CF','Africa'),
('Chad','TD','Africa'),('Chile','CL','Americas'),('China','CN','Asia'),
('Colombia','CO','Americas'),('Comoros','KM','Africa'),('Congo','CG','Africa'),
('Costa Rica','CR','Americas'),('Croatia','HR','Europe'),('Cuba','CU','Americas'),
('Cyprus','CY','Europe'),('Czech Republic','CZ','Europe'),('Denmark','DK','Europe'),
('Djibouti','DJ','Africa'),('Dominica','DM','Americas'),('Dominican Republic','DO','Americas'),
('Ecuador','EC','Americas'),('Egypt','EG','Africa'),('El Salvador','SV','Americas'),
('Equatorial Guinea','GQ','Africa'),('Eritrea','ER','Africa'),('Estonia','EE','Europe'),
('Eswatini','SZ','Africa'),('Ethiopia','ET','Africa'),('Fiji','FJ','Oceania'),
('Finland','FI','Europe'),('France','FR','Europe'),('Gabon','GA','Africa'),
('Gambia','GM','Africa'),('Georgia','GE','Asia'),('Germany','DE','Europe'),
('Ghana','GH','Africa'),('Greece','GR','Europe'),('Grenada','GD','Americas'),
('Guatemala','GT','Americas'),('Guinea','GN','Africa'),('Guinea-Bissau','GW','Africa'),
('Guyana','GY','Americas'),('Haiti','HT','Americas'),('Honduras','HN','Americas'),
('Hungary','HU','Europe'),('Iceland','IS','Europe'),('India','IN','Asia'),
('Indonesia','ID','Asia'),('Iran','IR','Asia'),('Iraq','IQ','Asia'),
('Ireland','IE','Europe'),('Israel','IL','Asia'),('Italy','IT','Europe'),
('Jamaica','JM','Americas'),('Japan','JP','Asia'),('Jordan','JO','Asia'),
('Kazakhstan','KZ','Asia'),('Kenya','KE','Africa'),('Kiribati','KI','Oceania'),
('Kuwait','KW','Asia'),('Kyrgyzstan','KG','Asia'),('Laos','LA','Asia'),
('Latvia','LV','Europe'),('Lebanon','LB','Asia'),('Lesotho','LS','Africa'),
('Liberia','LR','Africa'),('Libya','LY','Africa'),('Liechtenstein','LI','Europe'),
('Lithuania','LT','Europe'),('Luxembourg','LU','Europe'),('Madagascar','MG','Africa'),
('Malawi','MW','Africa'),('Malaysia','MY','Asia'),('Maldives','MV','Asia'),
('Mali','ML','Africa'),('Malta','MT','Europe'),('Marshall Islands','MH','Oceania'),
('Mauritania','MR','Africa'),('Mauritius','MU','Africa'),('Mexico','MX','Americas'),
('Micronesia','FM','Oceania'),('Moldova','MD','Europe'),('Monaco','MC','Europe'),
('Mongolia','MN','Asia'),('Montenegro','ME','Europe'),('Morocco','MA','Africa'),
('Mozambique','MZ','Africa'),('Myanmar','MM','Asia'),('Namibia','NA','Africa'),
('Nauru','NR','Oceania'),('Nepal','NP','Asia'),('Netherlands','NL','Europe'),
('New Zealand','NZ','Oceania'),('Nicaragua','NI','Americas'),('Niger','NE','Africa'),
('Nigeria','NG','Africa'),('North Korea','KP','Asia'),('North Macedonia','MK','Europe'),
('Norway','NO','Europe'),('Oman','OM','Asia'),('Pakistan','PK','Asia'),
('Palau','PW','Oceania'),('Panama','PA','Americas'),('Papua New Guinea','PG','Oceania'),
('Paraguay','PY','Americas'),('Peru','PE','Americas'),('Philippines','PH','Asia'),
('Poland','PL','Europe'),('Portugal','PT','Europe'),('Qatar','QA','Asia'),
('Romania','RO','Europe'),('Russia','RU','Europe'),('Rwanda','RW','Africa'),
('Saint Kitts and Nevis','KN','Americas'),('Saint Lucia','LC','Americas'),
('Saint Vincent and the Grenadines','VC','Americas'),('Samoa','WS','Oceania'),
('San Marino','SM','Europe'),('Sao Tome and Principe','ST','Africa'),
('Saudi Arabia','SA','Asia'),('Senegal','SN','Africa'),('Serbia','RS','Europe'),
('Seychelles','SC','Africa'),('Sierra Leone','SL','Africa'),('Singapore','SG','Asia'),
('Slovakia','SK','Europe'),('Slovenia','SI','Europe'),('Solomon Islands','SB','Oceania'),
('Somalia','SO','Africa'),('South Africa','ZA','Africa'),('South Korea','KR','Asia'),
('South Sudan','SS','Africa'),('Spain','ES','Europe'),('Sri Lanka','LK','Asia'),
('Sudan','SD','Africa'),('Suriname','SR','Americas'),('Sweden','SE','Europe'),
('Switzerland','CH','Europe'),('Syria','SY','Asia'),('Taiwan','TW','Asia'),
('Tajikistan','TJ','Asia'),('Tanzania','TZ','Africa'),('Thailand','TH','Asia'),
('Timor-Leste','TL','Asia'),('Togo','TG','Africa'),('Tonga','TO','Oceania'),
('Trinidad and Tobago','TT','Americas'),('Tunisia','TN','Africa'),('Turkey','TR','Asia'),
('Turkmenistan','TM','Asia'),('Tuvalu','TV','Oceania'),('Uganda','UG','Africa'),
('Ukraine','UA','Europe'),('United Arab Emirates','AE','Asia'),
('United Kingdom','GB','Europe'),('United States','US','Americas'),
('Uruguay','UY','Americas'),('Uzbekistan','UZ','Asia'),('Vanuatu','VU','Oceania'),
('Vatican City','VA','Europe'),('Venezuela','VE','Americas'),('Vietnam','VN','Asia'),
('Yemen','YE','Asia'),('Zambia','ZM','Africa'),('Zimbabwe','ZW','Africa')
ON CONFLICT (iso_code) DO NOTHING;

DO $$ BEGIN
    RAISE NOTICE 'countries: % rows present', (SELECT COUNT(*) FROM countries);
END $$;

-- ------------------------------------------------------------
-- 2. SDG GOALS (17 UN Sustainable Development Goals)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sdg_goals (
    id          INT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT,
    colour_hex  TEXT
);

INSERT INTO sdg_goals (id, title, colour_hex) VALUES
(1,  'No Poverty',                        '#E5243B'),
(2,  'Zero Hunger',                       '#DDA63A'),
(3,  'Good Health and Well-being',        '#4C9F38'),
(4,  'Quality Education',                 '#C5192D'),
(5,  'Gender Equality',                   '#FF3A21'),
(6,  'Clean Water and Sanitation',        '#26BDE2'),
(7,  'Affordable and Clean Energy',       '#FCC30B'),
(8,  'Decent Work and Economic Growth',   '#A21942'),
(9,  'Industry, Innovation and Infrastructure','#FD6925'),
(10, 'Reduced Inequalities',              '#DD1367'),
(11, 'Sustainable Cities and Communities','#FD9D24'),
(12, 'Responsible Consumption and Production','#BF8B2E'),
(13, 'Climate Action',                    '#3F7E44'),
(14, 'Life Below Water',                  '#0A97D9'),
(15, 'Life on Land',                      '#56C02B'),
(16, 'Peace, Justice and Strong Institutions','#00689D'),
(17, 'Partnerships for the Goals',        '#19486A')
ON CONFLICT (id) DO NOTHING;

DO $$ BEGIN
    RAISE NOTICE 'sdg_goals: % rows present', (SELECT COUNT(*) FROM sdg_goals);
END $$;

-- ------------------------------------------------------------
-- 3. SKILLS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skills (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    category    TEXT,
    description TEXT,
    CONSTRAINT ux_skills_name UNIQUE (name)
);

INSERT INTO skills (name, category) VALUES
('Public Speaking','Communication'),('Community Outreach','Engagement'),
('Canvassing','Political'),('Grant Writing','Fundraising'),
('Project Management','Management'),('Data Analysis','Technical'),
('Research','Academic'),('Mentoring','Leadership'),
('Event Organisation','Operations'),('Social Media','Digital'),
('Policy Analysis','Government'),('Legal Drafting','Legal'),
('Financial Management','Finance'),('Software Development','Technical'),
('Graphic Design','Creative'),('Translation','Communication'),
('Ward Mobilisation','Political'),('Stakeholder Engagement','Engagement'),
('Volunteer Coordination','Operations'),('Media Relations','Communications')
ON CONFLICT (name) DO NOTHING;

DO $$ BEGIN
    RAISE NOTICE 'skills: % rows present', (SELECT COUNT(*) FROM skills);
END $$;

-- ------------------------------------------------------------
-- 4. COMPETENCIES
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS competencies (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    framework   TEXT,
    description TEXT,
    CONSTRAINT ux_competencies_name UNIQUE (name)
);

INSERT INTO competencies (name, framework) VALUES
('Leadership','Core'),('Community Engagement','Core'),
('Strategic Thinking','Core'),('Communication','Core'),
('Problem Solving','Core'),('Team Collaboration','Core'),
('Digital Literacy','Technical'),('Political Awareness','Domain'),
('Cultural Competence','Domain'),('Research & Analysis','Academic'),
('Financial Literacy','Domain'),('Advocacy','Domain')
ON CONFLICT (name) DO NOTHING;

DO $$ BEGIN
    RAISE NOTICE 'competencies: % rows present', (SELECT COUNT(*) FROM competencies);
END $$;

-- ------------------------------------------------------------
-- 5. ACTIVITY TYPES (15 platform-defined types)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_types (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    description         TEXT,
    icon                TEXT,
    requires_evidence   BOOL NOT NULL DEFAULT FALSE,
    requires_location   BOOL NOT NULL DEFAULT FALSE,
    detail_schema       JSONB,
    CONSTRAINT ux_activity_types_name UNIQUE (name)
);

INSERT INTO activity_types (name, description, requires_evidence, requires_location) VALUES
('outreach',              'Community outreach activity',                     FALSE, TRUE),
('volunteering',          'Volunteer work for organisation or community',     FALSE, TRUE),
('meeting',               'Formal or informal meeting',                       FALSE, FALSE),
('stakeholder_engagement','Engagement with a stakeholder or official',        TRUE,  FALSE),
('government_engagement', 'Engagement with a government body or official',    TRUE,  FALSE),
('ward_visit',            'Ward visit and voter registration support',        TRUE,  TRUE),
('community_activity',    'Community event or activity',                      FALSE, TRUE),
('media_activity',        'Media appearance, interview or publication',       FALSE, FALSE),
('campaign',              'Campaign activity — canvassing, leafleting etc.',  FALSE, TRUE),
('project_work',          'Work on a specific project',                       FALSE, FALSE),
('mentoring',             'Mentoring session with an individual',             FALSE, FALSE),
('training',              'Training delivered or received',                   FALSE, FALSE),
('donation',              'Donation made or facilitated',                     TRUE,  FALSE),
('communication',         'Formal communication sent or received',            FALSE, FALSE),
('research',              'Research activity or publication',                 FALSE, FALSE)
ON CONFLICT (name) DO NOTHING;

DO $$ BEGIN
    RAISE NOTICE 'activity_types: % rows present', (SELECT COUNT(*) FROM activity_types);
END $$;

-- ------------------------------------------------------------
-- 6. INDUSTRY CLASSIFICATIONS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS industry_classifications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    parent_id   UUID REFERENCES industry_classifications(id),
    code        TEXT,
    CONSTRAINT ux_industry_name UNIQUE (name)
);

INSERT INTO industry_classifications (name, code) VALUES
('Agriculture','AGR'),('Energy','ENE'),('Renewable Energy','ENE-R'),
('Technology','TECH'),('Education','EDU'),('Healthcare','HLT'),
('Finance','FIN'),('Infrastructure','INF'),('Transport','TRN'),
('Political','POL'),('Civic','CIV'),('Community Development','COM'),
('Environment','ENV'),('Media','MED'),('Legal','LEG'),
('Research','RES'),('Humanitarian','HUM'),('Faith','FAI'),
('Sports','SPT'),('Arts and Culture','ART')
ON CONFLICT (name) DO NOTHING;

DO $$ BEGIN
    RAISE NOTICE 'industry_classifications: % rows present', (SELECT COUNT(*) FROM industry_classifications);
END $$;

-- ------------------------------------------------------------
-- 7. WORKFLOW DEFINITIONS
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workflow_definitions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    allowed_transitions JSONB NOT NULL,
    is_system_default   BOOL NOT NULL DEFAULT FALSE,
    CONSTRAINT ux_workflow_name UNIQUE (name)
);

INSERT INTO workflow_definitions (name, is_system_default, allowed_transitions) VALUES
('Standard Verification Workflow', TRUE, '{
    "Draft":       ["Submitted"],
    "Submitted":   ["Under Review"],
    "Under Review":["Verified", "Rejected"],
    "Rejected":    ["Submitted", "Archived"],
    "Verified":    ["Archived"],
    "Archived":    []
}'::jsonb)
ON CONFLICT (name) DO NOTHING;

DO $$ BEGIN
    RAISE NOTICE 'workflow_definitions: % rows present', (SELECT COUNT(*) FROM workflow_definitions);
END $$;

-- ------------------------------------------------------------
-- 8. PLATFORM CONFIG
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS platform_config (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key         TEXT NOT NULL,
    value       JSONB NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ux_platform_config_key UNIQUE (key)
);

INSERT INTO platform_config (key, value) VALUES
('platform_name',           '"NDIP on Orion Platform Kernel"'),
('platform_version',        '"D5A-S1"'),
('default_workflow',        '"Standard Verification Workflow"'),
('max_file_size_photo_mb',  '10'),
('max_file_size_doc_mb',    '25'),
('max_file_size_video_mb',  '100'),
('impact_verified_multiplier', '2.0'),
('opportunity_min_confidence', '0.6'),
('network_rebuild_hour_utc', '2'),
('knowledge_rebuild_hour_utc','3')
ON CONFLICT (key) DO NOTHING;

DO $$ BEGIN
    RAISE NOTICE 'platform_config: % rows present', (SELECT COUNT(*) FROM platform_config);
END $$;

-- ------------------------------------------------------------
-- 9. EXTEND ng_wards — add nullable code column
-- ------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ng_wards' AND column_name = 'code'
    ) THEN
        ALTER TABLE ng_wards ADD COLUMN code TEXT;
        RAISE NOTICE 'ng_wards.code column added';
    ELSE
        RAISE NOTICE 'ng_wards.code column already exists — skipped';
    END IF;
END $$;

-- ------------------------------------------------------------
-- 10. VERIFICATION — D5A-S1 Complete Check
-- ------------------------------------------------------------
DO $$
DECLARE
    v_countries         INT;
    v_sdg               INT;
    v_skills            INT;
    v_competencies      INT;
    v_activity_types    INT;
    v_industries        INT;
    v_workflows         INT;
    v_config            INT;
    v_ng_wards_code     BOOL;
BEGIN
    SELECT COUNT(*) INTO v_countries       FROM countries;
    SELECT COUNT(*) INTO v_sdg             FROM sdg_goals;
    SELECT COUNT(*) INTO v_skills          FROM skills;
    SELECT COUNT(*) INTO v_competencies    FROM competencies;
    SELECT COUNT(*) INTO v_activity_types  FROM activity_types;
    SELECT COUNT(*) INTO v_industries      FROM industry_classifications;
    SELECT COUNT(*) INTO v_workflows       FROM workflow_definitions;
    SELECT COUNT(*) INTO v_config          FROM platform_config;
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ng_wards' AND column_name = 'code'
    ) INTO v_ng_wards_code;

    RAISE NOTICE '=== D5A-S1 GLOBAL FOUNDATION — VERIFICATION ===';
    RAISE NOTICE 'countries:                % (expect 196)', v_countries;
    RAISE NOTICE 'sdg_goals:                % (expect 17)',  v_sdg;
    RAISE NOTICE 'skills:                   % (expect 20)',  v_skills;
    RAISE NOTICE 'competencies:             % (expect 12)',  v_competencies;
    RAISE NOTICE 'activity_types:           % (expect 15)',  v_activity_types;
    RAISE NOTICE 'industry_classifications: % (expect 20)',  v_industries;
    RAISE NOTICE 'workflow_definitions:     % (expect 1)',   v_workflows;
    RAISE NOTICE 'platform_config:          % (expect 10)',  v_config;
    RAISE NOTICE 'ng_wards.code column:     %',              v_ng_wards_code;
    RAISE NOTICE '=== D5A-S1 COMPLETE ===';

    IF v_countries < 190 THEN
        RAISE EXCEPTION 'countries count too low — migration may have failed';
    END IF;
    IF v_sdg <> 17 THEN
        RAISE EXCEPTION 'sdg_goals count incorrect — expected 17';
    END IF;
    IF v_activity_types < 15 THEN
        RAISE EXCEPTION 'activity_types count too low — migration may have failed';
    END IF;
    IF NOT v_ng_wards_code THEN
        RAISE EXCEPTION 'ng_wards.code column missing — migration failed';
    END IF;
END $$;

COMMIT;

-- ============================================================
-- D5A-S1 complete. No existing tables were modified except
-- ng_wards (nullable code column added).
-- All v2 routes remain unaffected.
-- Next: D5A-S2 — Tenant & Identity Layer
-- ============================================================
