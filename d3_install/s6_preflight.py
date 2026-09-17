"""
D5A-S6 Phase A Pre-flight Inspection — READ ONLY
Run: docker exec ndip-backend-1 python3 /tmp/s6_preflight.py
"""
import os, sys, subprocess
sys.path.insert(0, '/app')
os.environ['DATABASE_URL'] = 'postgresql://agora_user:agora_pass@db:5432/agora_db'
from sqlalchemy import create_engine, text
db = create_engine('postgresql://agora_user:agora_pass@db:5432/agora_db').connect()

print('=' * 70)
print('D5A-S6 PHASE A — PRE-FLIGHT INSPECTION')
print('READ ONLY — NO MODIFICATIONS')
print('=' * 70)

# 1. Platform version
ver = db.execute(text("SELECT value FROM platform_config WHERE key='platform_version'")).scalar()
print(f'\n[1] Platform version: {ver}')

# 2. ward_sponsorships integrity
ws = db.execute(text('SELECT COUNT(*) FROM ward_sponsorships')).scalar()
ws_cols = [r[0] for r in db.execute(text("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name='ward_sponsorships' ORDER BY ordinal_position
""")).fetchall()]
print(f'\n[2] ward_sponsorships: {ws} rows (MUST REMAIN UNTOUCHED)')
print(f'    Columns: {", ".join(ws_cols)}')

# 3. S1-S5 tables present
s1_s5_tables = [
    'countries','sdg_goals','skills','competencies','activity_types',
    'industry_classifications','workflow_definitions','platform_config',
    'tenants','tenant_config','organisations','platform_identities',
    'platform_identity_auth','kernel_roles','platform_admins',
    'memberships','membership_roles','activities','volunteer_records',
    'projects','project_participants','project_roles'
]
print(f'\n[3] S1-S5 table integrity:')
existing = [r[0] for r in db.execute(text("""
    SELECT table_name FROM information_schema.tables WHERE table_schema='public'
""")).fetchall()]
for t in s1_s5_tables:
    status = 'OK' if t in existing else 'MISSING'
    print(f'    [{status}] {t}')

# 4. Existing v3 route conventions — inspect activities_v3.py
print(f'\n[4] Existing v3 conventions (from activities_v3.py):')
with open('/app/app/api/routes/activities_v3.py') as f:
    act = f.read()
conventions = {
    'Router prefix pattern': 'APIRouter(prefix=',
    'Auth dependency': 'get_current_v3_identity',
    'DB dependency': 'get_db',
    'Tenant context': 'set_tenant_context',
    'UUID primary keys': 'uuid.uuid4()',
    'JSONB via json.dumps': 'json.dumps',
    'CAST jsonb pattern': 'CAST(:',
    'is_archived soft delete': 'is_archived',
    'created_at/updated_at': 'created_at',
    'Pagination pattern': 'page_size',
    'Status codes 201': 'status_code=201',
}
for label, pattern in conventions.items():
    found = pattern in act
    print(f'    [{"YES" if found else "NO "}] {label}: {pattern!r}')

# 5. Archive/delete convention — how does S4/S5 handle archival?
print(f'\n[5] Archive/delete convention:')
with open('/app/app/api/routes/projects_v3.py') as f:
    proj = f.read()
has_delete = 'DELETE' in proj or '@router.delete' in proj
has_archive_field = 'is_archived' in proj
has_archive_status = 'Archived' in proj
print(f'    HTTP DELETE used: {has_delete}')
print(f'    is_archived field: {has_archive_field}')
print(f'    "Archived" status in lifecycle: {has_archive_status}')
print(f'    Convention: soft-delete via is_archived=True or status=Archived')

# 6. RLS patterns from S4/S5
print(f'\n[6] RLS patterns:')
rls_policies = db.execute(text("""
    SELECT tablename, policyname, cmd
    FROM pg_policies WHERE schemaname='public'
    ORDER BY tablename
""")).fetchall()
for r in rls_policies:
    print(f'    {r[0]}: policy={r[1]}, cmd={r[2]}')

rls_setting = "current_setting('app.current_tenant_id', TRUE)"
rls_pattern = f'tenant_id = NULLIF({rls_setting}, ' + "'')"
print(f'\n    Existing RLS WHERE clause pattern:')
print(f'    {rls_pattern}')

# 7. Identity/organisation/project FK patterns
print(f'\n[7] FK relationship patterns:')
fk_examples = db.execute(text("""
    SELECT
        tc.table_name, kcu.column_name, ccu.table_name AS foreign_table
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage ccu
        ON ccu.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_name IN ('activities','volunteer_records','projects','project_participants')
    ORDER BY tc.table_name, kcu.column_name
""")).fetchall()
for r in fk_examples:
    print(f'    {r[0]}.{r[1]} -> {r[2]}')

# 8. Existing donations/communications tables
print(f'\n[8] S6 tables (should NOT exist yet):')
for t in ['donations', 'communications']:
    exists = t in existing
    print(f'    [{"EXISTS - CONFLICT" if exists else "NOT YET - CORRECT"}] {t}')

# 9. Migration conventions
print(f'\n[9] Migration file conventions:')
import os as _os
mig_files = _os.listdir('/app/migrations') if _os.path.exists('/app/migrations') else []
print(f'    Migration files: {sorted(mig_files)}')

# 10. Current v3 main.py registrations
print(f'\n[10] v3 routes registered in main.py:')
with open('/app/app/main.py') as f:
    main = f.read()
v3_lines = [l.strip() for l in main.split('\n') if 'include_router' in l and 'v3' in l.lower()]
for l in v3_lines:
    print(f'    {l}')

# 11. Existing donation status conventions
print(f'\n[11] Status field conventions across v3 tables:')
status_check = db.execute(text("""
    SELECT table_name, column_name
    FROM information_schema.columns
    WHERE table_schema='public'
    AND column_name='status'
    AND table_name IN ('activities','projects','volunteer_records')
    ORDER BY table_name
""")).fetchall()
for r in status_check:
    print(f'    {r[0]}.{r[1]}: TEXT with CHECK constraint')

# 12. Currency convention check
print(f'\n[12] Existing currency/amount patterns:')
curr = db.execute(text("""
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema='public'
    AND (column_name ILIKE '%amount%' OR column_name ILIKE '%currency%'
         OR column_name ILIKE '%budget%' OR column_name ILIKE '%naira%')
    ORDER BY table_name, column_name
""")).fetchall()
for r in curr:
    print(f'    {r[0]}.{r[1]}: {r[2]}')

db.close()
print('\n' + '=' * 70)
print('PHASE A INSPECTION COMPLETE — NO CHANGES MADE')
print('=' * 70)
