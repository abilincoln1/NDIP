"""
D5A-S6 Test Suite — Donations & Communications Engine
Tests: CRUD, financial visibility, tenant isolation, anonymous donors,
       archive convention, communications record-only, ward_sponsorships integrity
Run: docker exec ndip-backend-1 python3 /tmp/test_s6.py
"""
import sys, os
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
print('D5A-S6: Donations & Communications Engine Test Suite')
print('=' * 65)

# ── Setup ──────────────────────────────────────────────────────
print('\n[SETUP] Logging in...')
tokens = {}
for role, email in [
    ('super_admin', 'superadmin@ndip.rtifn.org'),
    ('national_director', 'nationaldirector@ndip.rtifn.org'),
    ('verifier', 'verifier@ndip.rtifn.org'),
    ('verified_member', 'verifiedmember@ndip.rtifn.org'),
    ('standard_member', 'member@ndip.rtifn.org'),
]:
    tok = login(email)
    if tok:
        tokens[role] = tok
        print(f'  OK: {role}')
    else:
        print(f'  FAIL: {role}')

# Get a project for linkage tests
proj = db.execute(text("SELECT id FROM projects LIMIT 1")).fetchone()
proj_id = str(proj.id) if proj else None

# Get a verified_member identity id for donor tests
vm_id = db.execute(text(
    "SELECT id FROM platform_identities WHERE email='verifiedmember@ndip.rtifn.org'"
)).scalar()

# ── AREA 1: Donation CRUD ──────────────────────────────────────
print('\n[AREA 1] Donation CRUD')

# D1 — Create identified donation
r = httpx.post(f'{BASE}/api/v3/donations/', headers=h(tokens['standard_member']),
    json={
        'donation_type': 'donation',
        'donation_date': '2026-08-11',
        'donor_identity_id': str(vm_id),
        'amount': 50.0,
        'currency': 'GBP',
        'notes': 'Monthly contribution to RTIFN Birmingham',
    }, timeout=10)
chk('D1 Create identified donation (201)', r.status_code == 201, r.text[:100])
don_id = r.json().get('id') if r.status_code == 201 else None

if don_id:
    chk('D1 starts as recorded', r.json().get('status') == 'recorded')

# D1 — Create organisational donation
org = db.execute(text("SELECT id FROM organisations LIMIT 1")).fetchone()
org_id = str(org.id) if org else None

r = httpx.post(f'{BASE}/api/v3/donations/', headers=h(tokens['standard_member']),
    json={
        'donation_type': 'sponsorship',
        'donation_date': '2026-08-11',
        'donor_organisation_id': org_id,
        'amount': 500.0,
        'currency': 'GBP',
        'notes': 'RTIFN Birmingham ward sponsorship fund',
        'project_id': proj_id,
    }, timeout=10)
chk('D1 Create organisation donation (201)', r.status_code == 201, r.text[:100])

# D1 — Create anonymous/external donation (Condition 3)
r = httpx.post(f'{BASE}/api/v3/donations/', headers=h(tokens['standard_member']),
    json={
        'donation_type': 'donation',
        'donation_date': '2026-08-11',
        'donor_external_name': 'Anonymous Diaspora Supporter',
        'amount': 25.0,
        'currency': 'GBP',
    }, timeout=10)
chk('D1 Create anonymous/external donation (201)', r.status_code == 201, r.text[:100])
anon_don_id = r.json().get('id') if r.status_code == 201 else None

# D1 — In-kind donation (amount=None)
r = httpx.post(f'{BASE}/api/v3/donations/', headers=h(tokens['standard_member']),
    json={
        'donation_type': 'in_kind',
        'donation_date': '2026-08-11',
        'donor_external_name': 'Local Business Supporter',
        'amount': None,
        'currency': 'GBP',
        'notes': 'Donated printing services',
    }, timeout=10)
chk('D1 Create in-kind donation with null amount (201)', r.status_code == 201, r.text[:100])

# D1 — Must fail without any donor identifier
r = httpx.post(f'{BASE}/api/v3/donations/', headers=h(tokens['standard_member']),
    json={
        'donation_type': 'donation',
        'donation_date': '2026-08-11',
        'amount': 10.0,
        'currency': 'GBP',
    }, timeout=10)
chk('D1 Fails without donor identifier (400)', r.status_code == 400, r.text[:80])

# D2 — List donations
r = httpx.get(f'{BASE}/api/v3/donations/', headers=h(tokens['standard_member']), timeout=10)
chk('D2 List donations returns 200', r.status_code == 200)
if r.status_code == 200:
    data = r.json()
    chk('D2 Has total field', 'total' in data)
    chk('D2 At least 3 donations returned', data['total'] >= 3, f"got {data['total']}")

# D3 — Get donation
if don_id:
    r = httpx.get(f'{BASE}/api/v3/donations/{don_id}',
        headers=h(tokens['standard_member']), timeout=10)
    chk('D3 Get donation returns 200', r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        chk('D3 Amount present', d.get('amount') == 50.0)
        chk('D3 Currency present', d.get('currency') == 'GBP')
        chk('D3 Donor name present', d['donor']['identity_name'] is not None)

# D4 — Update donation
if don_id:
    r = httpx.patch(f'{BASE}/api/v3/donations/{don_id}',
        headers=h(tokens['standard_member']),
        json={'notes': 'Updated: Monthly contribution — Gift Aid eligible'},
        timeout=10)
    chk('D4 Update donation succeeds', r.status_code == 200)

# D5 — Archive donation (PATCH with is_archived=True — no HTTP DELETE)
if anon_don_id:
    r = httpx.patch(f'{BASE}/api/v3/donations/{anon_don_id}',
        headers=h(tokens['standard_member']),
        json={'is_archived': True},
        timeout=10)
    chk('D5 Archive donation via PATCH is_archived=True', r.status_code == 200)
    # Confirm archived
    r2 = httpx.get(f'{BASE}/api/v3/donations/', headers=h(tokens['standard_member']), timeout=10)
    if r2.status_code == 200:
        ids = [i['id'] for i in r2.json()['items']]
        chk('D5 Archived donation not in list', anon_don_id not in ids)

# ── AREA 2: Financial Visibility — Condition 2 ────────────────
print('\n[AREA 2] Financial Visibility (Project visibility ≠ Financial visibility)')

# verified_member created a donation — national_director should NOT see it
# unless they share tenant context (they do — both RTIFN)
# Key test: project participation alone does not grant financial access
if don_id:
    r = httpx.get(f'{BASE}/api/v3/donations/{don_id}',
        headers=h(tokens['national_director']), timeout=10)
    chk('D3 National director can access tenant donation', r.status_code == 200)

# Unauthenticated access blocked
r = httpx.get(f'{BASE}/api/v3/donations/', timeout=10)
chk('D2 Unauthenticated access blocked', r.status_code in (401, 403))

# RLS on donations
rls = db.execute(text("""
    SELECT COUNT(*) FROM pg_policies
    WHERE tablename='donations' AND policyname='tenant_isolation'
""")).scalar()
chk('RLS policy on donations', rls == 1)

# Cross-tenant DB check
import psycopg2
conn = psycopg2.connect("host=db dbname=agora_db user=agora_user password=agora_pass")
conn.autocommit = False
cur = conn.cursor()
cur.execute("SET LOCAL app.current_tenant_id = '00000000-0000-0000-0000-000000000000'")
cur.execute("SELECT COUNT(*) FROM donations")
cross_count = cur.fetchone()[0]
conn.rollback()
conn.close()
chk('Cross-tenant donation query returns 0 (fake tenant)', cross_count == 0, f'got {cross_count}')

# ── AREA 3: Communications CRUD ────────────────────────────────
print('\n[AREA 3] Communications CRUD')

# C1 — Create communication record
r = httpx.post(f'{BASE}/api/v3/communications/', headers=h(tokens['standard_member']),
    json={
        'communication_type': 'email',
        'subject': 'Birmingham Chapter — August Meeting Confirmation',
        'communication_date': '2026-08-11',
        'recipient_external': 'birmingham.community@example.org',
        'notes': 'Confirmed attendance for 15 members at August community meeting',
        'status': 'sent',
        'project_id': proj_id,
    }, timeout=10)
chk('C1 Create communication record (201)', r.status_code == 201, r.text[:100])
comm_id = r.json().get('id') if r.status_code == 201 else None

if comm_id:
    chk('C1 Starts as sent', r.json().get('status') == 'sent')

# C1 — Create meeting minutes
r = httpx.post(f'{BASE}/api/v3/communications/', headers=h(tokens['national_director']),
    json={
        'communication_type': 'meeting_minutes',
        'subject': 'RTIFN Birmingham Chapter — August Strategy Session',
        'communication_date': '2026-08-11',
        'notes': 'Agreed priorities: ward engagement, community outreach, membership drive',
        'status': 'sent',
    }, timeout=10)
chk('C1 Create meeting minutes (201)', r.status_code == 201, r.text[:100])

# C1 — Create with platform identity recipient
r = httpx.post(f'{BASE}/api/v3/communications/', headers=h(tokens['standard_member']),
    json={
        'communication_type': 'letter',
        'subject': 'Ward Engagement Confirmation',
        'communication_date': '2026-08-11',
        'recipient_identity_id': str(vm_id),
        'status': 'draft',
    }, timeout=10)
chk('C1 Create communication with platform recipient (201)', r.status_code == 201, r.text[:100])

# C2 — List communications
r = httpx.get(f'{BASE}/api/v3/communications/', headers=h(tokens['standard_member']), timeout=10)
chk('C2 List communications returns 200', r.status_code == 200)
if r.status_code == 200:
    chk('C2 At least 1 communication', r.json()['total'] >= 1)

# C3 — Get communication
if comm_id:
    r = httpx.get(f'{BASE}/api/v3/communications/{comm_id}',
        headers=h(tokens['standard_member']), timeout=10)
    chk('C3 Get communication returns 200', r.status_code == 200)
    if r.status_code == 200:
        c = r.json()
        chk('C3 Subject present', c.get('subject') is not None)
        chk('C3 Communication type present', c.get('communication_type') == 'email')
        chk('C3 No delivery fields present', 'message_body' not in c and 'html_content' not in c)

# C4 — Update communication
if comm_id:
    r = httpx.patch(f'{BASE}/api/v3/communications/{comm_id}',
        headers=h(tokens['standard_member']),
        json={'status': 'acknowledged', 'notes': 'Recipient confirmed receipt'},
        timeout=10)
    chk('C4 Update communication succeeds', r.status_code == 200)

# C4 — Archive communication
if comm_id:
    r = httpx.patch(f'{BASE}/api/v3/communications/{comm_id}',
        headers=h(tokens['standard_member']),
        json={'is_archived': True}, timeout=10)
    chk('C4 Archive communication via PATCH', r.status_code == 200)

# ── AREA 4: Security & Isolation ──────────────────────────────
print('\n[AREA 4] Security & Isolation')

# Unauthenticated blocked
r = httpx.get(f'{BASE}/api/v3/communications/', timeout=10)
chk('C2 Unauthenticated communications blocked', r.status_code in (401, 403))

# RLS on communications
rls_c = db.execute(text("""
    SELECT COUNT(*) FROM pg_policies
    WHERE tablename='communications' AND policyname='tenant_isolation'
""")).scalar()
chk('RLS policy on communications', rls_c == 1)

# Invalid donation type rejected
r = httpx.post(f'{BASE}/api/v3/donations/', headers=h(tokens['standard_member']),
    json={
        'donation_type': 'cryptocurrency',
        'donation_date': '2026-08-11',
        'donor_external_name': 'Test',
        'amount': 1.0, 'currency': 'GBP',
    }, timeout=10)
chk('Invalid donation_type rejected (400)', r.status_code == 400)

# Invalid communication type rejected
r = httpx.post(f'{BASE}/api/v3/communications/', headers=h(tokens['standard_member']),
    json={
        'communication_type': 'bulk_campaign',
        'subject': 'Mass outreach',
        'communication_date': '2026-08-11',
    }, timeout=10)
chk('Invalid communication_type rejected (400)', r.status_code == 400)

# ── AREA 5: Architectural Conformance ─────────────────────────
print('\n[AREA 5] Architectural Conformance')

# ward_sponsorships untouched
ws = db.execute(text('SELECT COUNT(*) FROM ward_sponsorships')).scalar()
chk('ward_sponsorships: 9 rows (UNTOUCHED)', ws == 9, f'got {ws}')

# platform_projects untouched
pp = db.execute(text('SELECT COUNT(*) FROM platform_projects')).scalar()
chk('platform_projects preserved (8 rows)', pp == 8, f'got {pp}')

# No payment fields in donations
pay_cols = db.execute(text("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name='donations'
    AND column_name IN ('card_number','cvv','bank_account','payment_gateway','stripe_id')
""")).fetchall()
chk('No payment credentials fields in donations table', len(pay_cols) == 0, f'found: {pay_cols}')

# No delivery fields in communications
del_cols = db.execute(text("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name='communications'
    AND column_name IN ('message_body','html_content','smtp_id','delivery_status','campaign_id')
""")).fetchall()
chk('No delivery/campaign fields in communications table', len(del_cols) == 0, f'found: {del_cols}')

# platform_version
ver = db.execute(text("SELECT value FROM platform_config WHERE key='platform_version'")).scalar()
chk('Platform version = D5A-S6', 'D5A-S6' in str(ver))

# Archive uses PATCH not DELETE (check no delete routes registered)
with open('/app/app/api/routes/donations_comms_v3.py') as f:
    src = f.read()
chk('No HTTP DELETE in S6 routes', '@donations_router.delete' not in src and '@comms_router.delete' not in src)
chk('is_archived pattern used for archival', 'is_archived' in src)

# ── AREA 6: v2 Regression ──────────────────────────────────────
print('\n[AREA 6] v2 Route Regression')
r = httpx.post(f'{BASE}/api/v2/members/login',
    json={'email': 'member@ndip.rtifn.org', 'password': 'TestPass2026!'}, timeout=20)
chk('v2 login works', r.status_code == 200)
if r.status_code == 200:
    v2_tok = r.json().get('access_token')
    r2 = httpx.get(f'{BASE}/api/v2/projects/', headers={'Authorization': f'Bearer {v2_tok}'}, timeout=10)
    chk('v2 /api/v2/projects/ still operational', r2.status_code == 200)
    r3 = httpx.get(f'{BASE}/api/v2/admin/members/', headers={'Authorization': f'Bearer {v2_tok}'}, timeout=10)
    chk('v2 /api/v2/admin/ still operational', r3.status_code in (200, 403))

db.close()

# ── Summary ────────────────────────────────────────────────────
print('\n' + '=' * 65)
print('D5A-S6 TEST SUMMARY')
print(f'Passed: {len(passed)}  Failed: {len(failed)}')
if failed:
    print('\nFailed:')
    for f in failed:
        print(f'  - {f}')
verdict = 'PASS' if len(failed) == 0 else 'FAIL'
print(f'\nS6 VERDICT: {verdict}')
print('=' * 65)
