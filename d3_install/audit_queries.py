"""
Read-only audit queries for D5A conformance report.
Paste output verbatim to Claude.
Run: docker exec ndip-backend-1 python3 /tmp/audit_queries.py
"""
import os, sys
sys.path.insert(0, '/app')
os.environ['DATABASE_URL'] = 'postgresql://agora_user:agora_pass@db:5432/agora_db'
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine('postgresql://agora_user:agora_pass@db:5432/agora_db')
db = sessionmaker(bind=engine)()

def q(label, sql, params={}):
    try:
        rows = db.execute(text(sql), params).fetchall()
        print(f"\n=== {label} ===")
        if rows:
            cols = rows[0]._fields if hasattr(rows[0], '_fields') else []
            if cols:
                print("  " + " | ".join(cols))
                print("  " + "-" * 60)
            for r in rows:
                print("  " + " | ".join(str(v) for v in r))
        else:
            print("  (no rows)")
    except Exception as e:
        print(f"\n=== {label} ===\n  ERROR: {e}")

print("=" * 70)
print("NDIP D5A CONFORMANCE AUDIT — DATABASE STATE")
print("=" * 70)

# 1. All tables
q("ALL TABLES IN agora_db", """
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' ORDER BY table_name
""")

# 2. D5A kernel tables
q("D5A KERNEL TABLES (S1-S3)", """
    SELECT table_name,
           (SELECT COUNT(*) FROM information_schema.columns c
            WHERE c.table_name = t.table_name AND c.table_schema = 'public') as col_count
    FROM information_schema.tables t
    WHERE table_schema = 'public'
    AND table_name IN (
        'countries','sdg_goals','skills','competencies','activity_types',
        'industry_classifications','workflow_definitions','platform_config',
        'tenants','tenant_config','organisations','platform_identities',
        'platform_identity_auth','identity_skills','kernel_roles','platform_admins',
        'memberships','membership_roles'
    )
    ORDER BY table_name
""")

# 3. Row counts for key tables
q("ROW COUNTS — KEY TABLES", """
    SELECT 'tenants' as tbl, COUNT(*) as rows FROM tenants
    UNION ALL SELECT 'organisations', COUNT(*) FROM organisations
    UNION ALL SELECT 'platform_identities', COUNT(*) FROM platform_identities
    UNION ALL SELECT 'kernel_roles', COUNT(*) FROM kernel_roles
    UNION ALL SELECT 'memberships', COUNT(*) FROM memberships
    UNION ALL SELECT 'membership_roles', COUNT(*) FROM membership_roles
    UNION ALL SELECT 'countries', COUNT(*) FROM countries
    UNION ALL SELECT 'activity_types', COUNT(*) FROM activity_types
    UNION ALL SELECT 'members (v2)', COUNT(*) FROM members
    UNION ALL SELECT 'ng_states', COUNT(*) FROM ng_states
    UNION ALL SELECT 'ng_lgas', COUNT(*) FROM ng_lgas
    UNION ALL SELECT 'ng_wards', COUNT(*) FROM ng_wards
    ORDER BY tbl
""")

# 4. Tenants
q("TENANTS", """
    SELECT t.id, t.name, t.slug, t.tenant_type, t.status,
           tc.platform_name_override, tc.enabled_modules
    FROM tenants t
    LEFT JOIN tenant_config tc ON tc.tenant_id = t.id
""")

# 5. Memberships breakdown
q("MEMBERSHIPS BY STATUS", """
    SELECT status, membership_type, COUNT(*) as count
    FROM memberships GROUP BY status, membership_type ORDER BY status
""")

# 6. Platform identities vs v2 members
q("IDENTITY MODEL — platform_identities vs members", """
    SELECT
        (SELECT COUNT(*) FROM platform_identities) as platform_identities,
        (SELECT COUNT(*) FROM members) as v2_members,
        (SELECT COUNT(*) FROM platform_identity_auth) as auth_records,
        (SELECT COUNT(*) FROM platform_admins) as platform_admins
""")

# 7. RLS policies
q("RLS POLICIES", """
    SELECT tablename, policyname, cmd, roles
    FROM pg_policies
    WHERE schemaname = 'public'
    ORDER BY tablename
""")

# 8. RLS status on tables
q("RLS STATUS ON D5A TABLES", """
    SELECT relname, relrowsecurity, relforcerowsecurity
    FROM pg_class
    WHERE relname IN ('tenants','organisations','platform_identities',
                      'kernel_roles','memberships','membership_roles')
    ORDER BY relname
""")

# 9. v3 API routes — check main.py for registrations
q("V3 ROUTES IN platform_config", """
    SELECT key, value FROM platform_config ORDER BY key
""")

# 10. Activity types seeded
q("ACTIVITY TYPES", """
    SELECT name, requires_evidence, requires_location FROM activity_types ORDER BY name
""")

# 11. Workflow definitions
q("WORKFLOW DEFINITIONS", """
    SELECT name, is_system_default, allowed_transitions FROM workflow_definitions
""")

# 12. Kernel roles
q("KERNEL ROLES", """
    SELECT name, description, is_system_role FROM kernel_roles ORDER BY name
""")

# 13. Independent project support — does projects table exist?
q("D5A-S4+ TABLES (NOT YET IMPLEMENTED)", """
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN (
        'activities','volunteer_records','projects','project_participants',
        'donations','communications','evidence_items','verification_events',
        'stakeholders','stakeholder_engagements','timeline_events',
        'platform_audit_log','sponsorships','ward_registrations',
        'ward_executives','identity_relationships','network_nodes',
        'knowledge_nodes','impact_profiles','marketplace_modules'
    )
    ORDER BY table_name
""")

# 14. v2 tables still present
q("V2 TABLES PRESERVED", """
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN (
        'members','chapters','engagement_reports','ward_sponsorships',
        'platform_projects','verification_submissions','audit_log',
        'member_sessions','member_onboarding_state'
    )
    ORDER BY table_name
""")

# 15. Geography completeness
q("GEOGRAPHY — STATE/LGA/WARD COVERAGE", """
    SELECT
        (SELECT COUNT(*) FROM ng_states) as states,
        (SELECT COUNT(*) FROM ng_lgas) as lgas,
        (SELECT COUNT(*) FROM ng_wards) as wards,
        (SELECT COUNT(*) FROM ng_polling_units) as polling_units,
        (SELECT COUNT(*) FROM ng_wards WHERE code IS NOT NULL) as wards_with_code
""")

# 16. Super-admin identity linkage
q("SUPERADMIN LINKAGE (v2 <-> v3)", """
    SELECT
        m.membership_number,
        m.email as v2_email,
        pi.email as v3_email,
        pi.identity_status,
        mb.status as membership_status,
        kr.name as role
    FROM members m
    LEFT JOIN platform_identities pi ON pi.id = m.id
    LEFT JOIN memberships mb ON mb.identity_id = pi.id
    LEFT JOIN membership_roles mr ON mr.membership_id = mb.id
    LEFT JOIN kernel_roles kr ON kr.id = mr.role_id
    WHERE m.membership_number = 'NDIP-2026-000001'
""")

db.close()
print("\n" + "=" * 70)
print("AUDIT QUERIES COMPLETE")
print("=" * 70)
