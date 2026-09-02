"""
D5A-S5 Test Suite — Project Engine
Tests: CRUD, independent projects, visibility, tenant isolation,
       multi-org participation, identity reuse, verification lifecycle,
       activity/volunteer integration, platform_projects preservation
Run: docker exec ndip-backend-1 python3 /tmp/test_s5.py
"""
import sys, os, json
sys.path.insert(0, '/app')
os.environ['DATABASE_URL'] = 'postgresql://agora_user:agora_pass@db:5432/agora_db'

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

BASE = 'http://localhost:8000'
engine = create_engine('postgresql://agora_user:agora_pass@db:5432/agora_db')
Session = sessionmaker(bind=engine)
db = Session()

passed = []
failed = []

def chk(label, cond, detail=''):
    if cond:
        passed.append(label)
        print(f'  [PASS] {label}')
    else:
        failed.append(label)
        print(f'  [FAIL] {label}{" — " + str(detail) if detail else ""}')

def login(email, password='TestPass2026!', slug='rtifn'):
    r = httpx.post(f'{BASE}/api/v3/auth/login',
        json={'email': email, 'password': password, 'tenant_slug': slug}, timeout=20)
    return r.json().get('access_token') if r.status_code == 200 else None

def h(token):
    return {'Authorization': f'Bearer {token}'}

print('=' * 65)
print('D5A-S5: Project Engine Test Suite')
print('=' * 65)

# ── Setup ──────────────────────────────────────────────────────
print('\n[SETUP] Logging in...')
tokens = {}
accounts = {
    'super_admin':      'superadmin@ndip.rtifn.org',
    'national_director':'nationaldirector@ndip.rtifn.org',
    'chapter_admin':    'chapteradmin.bham@ndip.rtifn.org',
    'verifier':         'verifier@ndip.rtifn.org',
    'verified_member':  'verifiedmember@ndip.rtifn.org',
    'standard_member':  'member@ndip.rtifn.org',
}
for role, email in accounts.items():
    tok = login(email)
    if tok:
        tokens[role] = tok
        print(f'  OK: {role}')
    else:
        print(f'  FAIL: {role}')

# Get org ID
org = db.execute(text("SELECT id FROM organisations WHERE name = 'RTIFN Birmingham'")).fetchone()
org_id = str(org.id) if org else None

# Get a ward
ward = db.execute(text("SELECT id, lga_id FROM ng_wards LIMIT 1")).fetchone()
ward_id = ward.id if ward else None
lga = db.execute(text("SELECT id, state_id FROM ng_lgas WHERE id = :lid"), {'lid': ward.lga_id}).fetchone()
lga_id = lga.id
state_id = lga.state_id

# ── AREA 1: Project Roles ──────────────────────────────────────
print('\n[AREA 1] Project Roles')
r = httpx.get(f'{BASE}/api/v3/projects/roles/list', headers=h(tokens['standard_member']), timeout=10)
chk('GET /api/v3/projects/roles/list returns 200', r.status_code == 200)
if r.status_code == 200:
    roles = r.json()
    chk('12 project roles returned', len(roles) == 12, f'got {len(roles)}')
    role_names = [r['name'] for r in roles]
    chk('originator role present', 'originator' in role_names)
    chk('funding_partner role present', 'funding_partner' in role_names)
    chk('observer role present', 'observer' in role_names)

# ── AREA 2: Tenant-Owned Project CRUD ─────────────────────────
print('\n[AREA 2] Tenant-Owned Project CRUD')
r = httpx.post(f'{BASE}/api/v3/projects/', headers=h(tokens['standard_member']),
    json={
        'name': 'RTIFN Birmingham Community Project',
        'description': 'A tenant-owned community project',
        'project_type': 'community',
        'visibility': 'tenant',
        'is_independent': False,
        'geo_scope': 'ward',
        'location_state_id': state_id,
        'location_lga_id': lga_id,
        'location_ward_id': ward_id,
    }, timeout=10)
chk('POST tenant project (201)', r.status_code == 201, r.text[:100])
tenant_project_id = r.json().get('id') if r.status_code == 201 else None

if tenant_project_id:
    chk('Tenant project starts as Draft', r.json().get('status') == 'Draft')
    chk('is_independent=False', r.json().get('is_independent') == False)

    # GET
    r = httpx.get(f'{BASE}/api/v3/projects/{tenant_project_id}',
        headers=h(tokens['standard_member']), timeout=10)
    chk('GET tenant project returns 200', r.status_code == 200)
    if r.status_code == 200:
        data = r.json()
        chk('Geographic data returned', data['geography']['ward'] is not None)
        chk('State resolved', data['geography']['state'] is not None)
        chk('is_independent=False in response', data['is_independent'] == False)

    # PATCH
    r = httpx.patch(f'{BASE}/api/v3/projects/{tenant_project_id}',
        headers=h(tokens['standard_member']),
        json={'description': 'Updated community project description'}, timeout=10)
    chk('PATCH Draft project succeeds', r.status_code == 200)

    # Status advance
    r = httpx.post(f'{BASE}/api/v3/projects/{tenant_project_id}/status',
        headers=h(tokens['standard_member']),
        json={'status': 'Proposed'}, timeout=10)
    chk('Advance status Draft → Proposed', r.status_code == 200, r.text[:100])

    # List
    r = httpx.get(f'{BASE}/api/v3/projects/', headers=h(tokens['standard_member']), timeout=10)
    chk('GET /api/v3/projects/ list works', r.status_code == 200)
    if r.status_code == 200:
        chk('Tenant project in list', r.json()['total'] >= 1)

# ── AREA 3: Independent Project ────────────────────────────────
print('\n[AREA 3] Independent Project (Waste-to-Energy)')
r = httpx.post(f'{BASE}/api/v3/projects/', headers=h(tokens['standard_member']),
    json={
        'name': 'Waste-to-Energy Initiative',
        'description': 'Cross-sector independent project — not owned by any single tenant',
        'project_type': 'independent',
        'visibility': 'participating_orgs',
        'is_independent': True,
        'geo_scope': 'national',
    }, timeout=10)
chk('POST independent project (201)', r.status_code == 201, r.text[:100])
wte_id = r.json().get('id') if r.status_code == 201 else None

if wte_id:
    chk('is_independent=True', r.json().get('is_independent') == True)

    r = httpx.get(f'{BASE}/api/v3/projects/{wte_id}',
        headers=h(tokens['standard_member']), timeout=10)
    chk('Creator can GET independent project', r.status_code == 200)
    if r.status_code == 200:
        chk('tenant_id is None', r.json()['tenant_id'] is None)
        chk('is_independent=True in response', r.json()['is_independent'] == True)

    # Add RTIFN org as partner
    r = httpx.post(f'{BASE}/api/v3/projects/{wte_id}/participants',
        headers=h(tokens['standard_member']),
        json={'organisation_id': org_id, 'role_name': 'partner'}, timeout=10)
    chk('Add RTIFN org as partner', r.status_code == 201, r.text[:100])

    # Add verifier as technical_partner individual
    verifier_id = db.execute(text(
        "SELECT id FROM platform_identities WHERE email = 'verifier@ndip.rtifn.org'"
    )).scalar()
    r = httpx.post(f'{BASE}/api/v3/projects/{wte_id}/participants',
        headers=h(tokens['standard_member']),
        json={'identity_id': str(verifier_id), 'role_name': 'technical_partner'}, timeout=10)
    chk('Add individual as technical_partner', r.status_code == 201, r.text[:100])

    # List participants
    r = httpx.get(f'{BASE}/api/v3/projects/{wte_id}/participants',
        headers=h(tokens['standard_member']), timeout=10)
    chk('GET participants returns list', r.status_code == 200)
    if r.status_code == 200:
        parts = r.json()
        chk('At least 2 participants (originator + org)', len(parts) >= 2, f'got {len(parts)}')
        roles_present = [p['role'] for p in parts]
        chk('originator role present', 'originator' in roles_present)
        chk('partner role present', 'partner' in roles_present)

# ── AREA 4: Visibility — Private Independent Project ───────────
print('\n[AREA 4] Visibility — Private Independent Project')
r = httpx.post(f'{BASE}/api/v3/projects/', headers=h(tokens['verified_member']),
    json={
        'name': 'Private Research Project',
        'description': 'Visible only to creator',
        'project_type': 'research',
        'visibility': 'private',
        'is_independent': True,
    }, timeout=10)
chk('POST private independent project (201)', r.status_code == 201, r.text[:100])
private_id = r.json().get('id') if r.status_code == 201 else None

if private_id:
    # Creator can see it
    r = httpx.get(f'{BASE}/api/v3/projects/{private_id}',
        headers=h(tokens['verified_member']), timeout=10)
    chk('Creator can access private project', r.status_code == 200)

    # Non-participant cannot see it
    r = httpx.get(f'{BASE}/api/v3/projects/{private_id}',
        headers=h(tokens['standard_member']), timeout=10)
    chk('Non-participant CANNOT access private project (403)', r.status_code == 403,
        f'got {r.status_code}')

    # Private project NOT in standard_member list
    r = httpx.get(f'{BASE}/api/v3/projects/', headers=h(tokens['standard_member']), timeout=10)
    if r.status_code == 200:
        ids = [p['id'] for p in r.json().get('items', [])]
        chk('Private project NOT in non-participant list', private_id not in ids)

# ── AREA 5: Public Independent Project ────────────────────────
print('\n[AREA 5] Visibility — Public Independent Project')
r = httpx.post(f'{BASE}/api/v3/projects/', headers=h(tokens['chapter_admin']),
    json={
        'name': 'Public Community Infrastructure Project',
        'description': 'Open for all to see',
        'project_type': 'infrastructure',
        'visibility': 'public',
        'is_independent': True,
    }, timeout=10)
chk('POST public independent project (201)', r.status_code == 201, r.text[:100])
public_id = r.json().get('id') if r.status_code == 201 else None

if public_id:
    # Any authenticated user can see public project
    r = httpx.get(f'{BASE}/api/v3/projects/{public_id}',
        headers=h(tokens['standard_member']), timeout=10)
    chk('Any user can access public project', r.status_code == 200)

    # Public project appears in list for all users
    r = httpx.get(f'{BASE}/api/v3/projects/', headers=h(tokens['standard_member']), timeout=10)
    if r.status_code == 200:
        ids = [p['id'] for p in r.json().get('items', [])]
        chk('Public project in standard_member list', public_id in ids)

# ── AREA 6: Multi-Membership Identity Reuse ───────────────────
print('\n[AREA 6] Multi-Membership Identity Reuse')
# Same identity (standard_member) added with different org contexts
# Both use the same platform_identity — no duplication
if wte_id:
    std_id = db.execute(text(
        "SELECT id FROM platform_identities WHERE email = 'member@ndip.rtifn.org'"
    )).scalar()
    chk('Standard member has single platform identity', std_id is not None)
    # Verify they're already a participant (as originator)
    part = db.execute(text("""
        SELECT COUNT(*) FROM project_participants
        WHERE project_id = :pid AND identity_id = :iid
    """), {"pid": wte_id, "iid": str(std_id)}).scalar()
    chk('Same identity used once — no duplication', part == 1, f'got {part}')

# ── AREA 7: Project → Activity Integration ────────────────────
print('\n[AREA 7] Project → Activity Integration')
if tenant_project_id:
    # Create activity linked to project
    r = httpx.post(f'{BASE}/api/v3/activities/', headers=h(tokens['standard_member']),
        json={
            'activity_type': 'meeting',
            'title': 'Project Kick-off Meeting',
            'activity_date': '2026-08-10',
            'project_id': tenant_project_id,
        }, timeout=10)
    chk('Create activity linked to project (201)', r.status_code == 201, r.text[:100])

    # Create standalone activity (no project)
    r = httpx.post(f'{BASE}/api/v3/activities/', headers=h(tokens['standard_member']),
        json={
            'activity_type': 'outreach',
            'title': 'Standalone Outreach',
            'activity_date': '2026-08-10',
        }, timeout=10)
    chk('Create standalone activity (201)', r.status_code == 201)

    # Get project activities
    r = httpx.get(f'{BASE}/api/v3/projects/{tenant_project_id}/activities',
        headers=h(tokens['standard_member']), timeout=10)
    chk('GET project activities', r.status_code == 200)
    if r.status_code == 200:
        chk('Project activity appears in list', len(r.json()) >= 1)

# ── AREA 8: Project → Volunteer Integration ───────────────────
print('\n[AREA 8] Project → Volunteer Integration')
if tenant_project_id:
    r = httpx.post(f'{BASE}/api/v3/volunteer/', headers=h(tokens['standard_member']),
        json={
            'volunteer_type': 'project_work',
            'description': 'Project volunteer work',
            'volunteer_date': '2026-08-10',
            'hours_contributed': 3.0,
            'project_id': tenant_project_id,
        }, timeout=10)
    chk('Create volunteer record linked to project (201)', r.status_code == 201, r.text[:100])

    # Standalone volunteer (no project)
    r = httpx.post(f'{BASE}/api/v3/volunteer/', headers=h(tokens['standard_member']),
        json={
            'volunteer_type': 'community',
            'description': 'Standalone volunteering',
            'volunteer_date': '2026-08-10',
        }, timeout=10)
    chk('Create standalone volunteer record (201)', r.status_code == 201)

# ── AREA 9: Verification Lifecycle ────────────────────────────
print('\n[AREA 9] Project Verification Lifecycle')
if tenant_project_id:
    # Submit
    r = httpx.post(f'{BASE}/api/v3/projects/{tenant_project_id}/verify',
        headers=h(tokens['standard_member']),
        json={'action': 'submit'}, timeout=10)
    chk('Submit project for verification', r.status_code == 200, r.text[:100])

    # Review
    r = httpx.post(f'{BASE}/api/v3/projects/{tenant_project_id}/verify',
        headers=h(tokens['verifier']),
        json={'action': 'review'}, timeout=10)
    chk('Verifier moves to Under Review', r.status_code == 200)

    # Non-verifier cannot verify
    r = httpx.post(f'{BASE}/api/v3/projects/{tenant_project_id}/verify',
        headers=h(tokens['standard_member']),
        json={'action': 'verify'}, timeout=10)
    chk('Standard member cannot verify (403)', r.status_code == 403)

    # Verify
    r = httpx.post(f'{BASE}/api/v3/projects/{tenant_project_id}/verify',
        headers=h(tokens['verifier']),
        json={'action': 'verify', 'notes': 'Project verified'}, timeout=10)
    chk('Verifier verifies project', r.status_code == 200)
    if r.status_code == 200:
        chk('is_verified=True', r.json().get('is_verified') == True)

# ── AREA 10: RBAC / Security ───────────────────────────────────
print('\n[AREA 10] RBAC & Security')
# Unauthenticated
r = httpx.get(f'{BASE}/api/v3/projects/', timeout=10)
chk('Unauthenticated access blocked', r.status_code in (401, 403))

# Invalid token
r = httpx.get(f'{BASE}/api/v3/projects/',
    headers={'Authorization': 'Bearer faketoken'}, timeout=10)
chk('Invalid token rejected', r.status_code == 401)

# RLS on projects
rls = db.execute(text("""
    SELECT COUNT(*) FROM pg_policies
    WHERE tablename = 'projects' AND policyname = 'tenant_isolation'
""")).scalar()
chk('RLS policy on projects', rls == 1)

rls_p = db.execute(text("""
    SELECT COUNT(*) FROM pg_policies
    WHERE tablename = 'project_participants' AND policyname = 'tenant_isolation'
""")).scalar()
chk('RLS policy on project_participants', rls_p == 1)

# ── AREA 11: Architectural Conformance ────────────────────────
print('\n[AREA 11] Architectural Conformance')

# platform_projects untouched
pp_count = db.execute(text('SELECT COUNT(*) FROM platform_projects')).scalar()
chk('platform_projects preserved (8 rows)', pp_count == 8, f'got {pp_count}')

# No polling unit dependency
pu_col = db.execute(text("""
    SELECT is_nullable FROM information_schema.columns
    WHERE table_name='projects' AND column_name='location_polling_unit_id'
""")).scalar()
chk('projects.location_polling_unit_id is nullable', pu_col == 'YES')
pu_rows = db.execute(text('SELECT COUNT(*) FROM ng_polling_units')).scalar()
chk('No polling units imported (0 rows)', pu_rows == 0, f'got {pu_rows}')

# Independent project: tenant_id is NULL
if wte_id:
    wte = db.execute(text('SELECT tenant_id FROM projects WHERE id = :id'), {'id': wte_id}).fetchone()
    chk('WtE project has tenant_id=NULL', wte.tenant_id is None)

# Tenant project: tenant_id is set
if tenant_project_id:
    tp = db.execute(text('SELECT tenant_id FROM projects WHERE id = :id'),
        {'id': tenant_project_id}).fetchone()
    chk('Tenant project has tenant_id set', tp.tenant_id is not None)

# project_roles is data-driven (not hardcoded)
chk('project_roles table has 12 roles',
    db.execute(text('SELECT COUNT(*) FROM project_roles')).scalar() == 12)

# RTIFN member does not become WtE project owner
if wte_id:
    wte_full = db.execute(text('SELECT tenant_id, originating_org_id FROM projects WHERE id = :id'),
        {'id': wte_id}).fetchone()
    chk('WtE originating_org_id is None (individually initiated)', wte_full.originating_org_id is None)
    chk('WtE not owned by any tenant', wte_full.tenant_id is None)

# platform_version
ver = db.execute(text("SELECT value FROM platform_config WHERE key = 'platform_version'")).scalar()
chk('Platform version = D5A-S5', 'D5A-S5' in str(ver))

# ── AREA 12: v2 Regression Check ──────────────────────────────
print('\n[AREA 12] v2 Route Regression')
# Login via v2
r = httpx.post(f'{BASE}/api/v2/members/login',
    json={'email': 'member@ndip.rtifn.org', 'password': 'TestPass2026!'}, timeout=20)
chk('v2 login works', r.status_code == 200)
if r.status_code == 200:
    v2_token = r.json().get('access_token')
    r = httpx.get(f'{BASE}/api/v2/projects/',
        headers={'Authorization': f'Bearer {v2_token}'}, timeout=10)
    chk('v2 /api/v2/projects/ still operational', r.status_code == 200, f'got {r.status_code}')

db.close()

# ── Summary ────────────────────────────────────────────────────
print('\n' + '=' * 65)
print('D5A-S5 TEST SUMMARY')
print(f'Passed: {len(passed)}  Failed: {len(failed)}')
if failed:
    print('\nFailed:')
    for f in failed:
        print(f'  - {f}')
verdict = 'PASS' if len(failed) == 0 else 'FAIL'
print(f'\nS5 VERDICT: {verdict}')
print('=' * 65)
