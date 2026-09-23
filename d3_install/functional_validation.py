"""
NDIP Functional Validation — Three End-to-End Workflows
Workflow A: Activity (Create → Retrieve → Confirm)
Workflow B: Volunteer (Create → Retrieve → Confirm)
Workflow C: Project (Create → Retrieve → Confirm)
Plus: Donation and Communication record creation
Run: docker exec ndip-backend-1 python3 /tmp/functional_validation.py
"""
import sys, os, json
sys.path.insert(0, '/app')
os.environ['DATABASE_URL'] = 'postgresql://agora_user:agora_pass@db:5432/agora_db'

import httpx
from sqlalchemy import create_engine, text

BASE = 'http://localhost:8000'
db = create_engine('postgresql://agora_user:agora_pass@db:5432/agora_db').connect()

passed = []
failed = []

def chk(label, cond, detail=''):
    if cond:
        passed.append(label)
        print(f'  [PASS] {label}')
    else:
        failed.append(label)
        print(f'  [FAIL] {label}{" — " + str(detail) if detail else ""}')

def login(email, slug='rtifn'):
    r = httpx.post(f'{BASE}/api/v3/auth/login',
        json={'email': email, 'password': 'TestPass2026!', 'tenant_slug': slug}, timeout=20)
    return r.json().get('access_token') if r.status_code == 200 else None

def h(tok): return {'Authorization': f'Bearer {tok}'}

print('=' * 65)
print('NDIP FUNCTIONAL VALIDATION — END-TO-END WORKFLOWS')
print('19 September 2026')
print('=' * 65)

# Get tokens
print('\n[SETUP]')
tok_member = login('member@ndip.rtifn.org')
tok_director = login('nationaldirector@ndip.rtifn.org')
tok_verifier = login('verifier@ndip.rtifn.org')
chk('Standard member login', tok_member is not None)
chk('National director login', tok_director is not None)
chk('Verifier login', tok_verifier is not None)

# Get geography for ward-level test
ward = db.execute(text("""
    SELECT w.id, w.name, l.id as lga_id, l.name as lga_name,
           s.id as state_id, s.name as state_name
    FROM ng_wards w
    JOIN ng_lgas l ON l.id = w.lga_id
    JOIN ng_states s ON s.id = l.state_id
    WHERE s.name = 'Lagos'
    LIMIT 1
""")).fetchone()
chk('Lagos ward available for geographic test',
    ward is not None, 'no Lagos wards found' if ward is None else '')

# ── Workflow A: Activity ───────────────────────────────────────
print('\n[WORKFLOW A] Activity: Create → Retrieve → Confirm Persistence')

# A1 — Create outreach activity (Birmingham, UK context)
r = httpx.post(f'{BASE}/api/v3/activities/', headers=h(tok_member),
    json={
        'activity_type': 'outreach',
        'title': 'RTIFN Birmingham Community Outreach — Validation Test',
        'description': 'End-to-end functional validation record. Self-reported.',
        'activity_date': '2026-09-19',
        'location_text': 'Birmingham, UK',
        'activity_details': {'participants': 1, 'outcome': 'Validation successful'},
    }, timeout=10)
chk('A1 Create outreach activity (201)', r.status_code == 201, r.text[:80])
act_id = r.json().get('id') if r.status_code == 201 else None

# A2 — Create ward_visit with full geographic chain
if ward:
    r2 = httpx.post(f'{BASE}/api/v3/activities/', headers=h(tok_member),
        json={
            'activity_type': 'ward_visit',
            'title': f'Ward Engagement Validation — {ward.ward_name if hasattr(ward, "ward_name") else ward.name}, Lagos',
            'description': 'Geographic chain test: State → LGA → Ward',
            'activity_date': '2026-09-19',
            'location_state_id': ward.state_id,
            'location_lga_id': ward.lga_id,
            'location_ward_id': ward.id,
            'activity_details': {'engagement_notes': 'Ward-level geographic resolution test'},
        }, timeout=10)
    chk('A2 Create ward_visit with State→LGA→Ward chain (201)', r2.status_code == 201, r2.text[:80])
    ward_act_id = r2.json().get('id') if r2.status_code == 201 else None
else:
    ward_act_id = None

# A3 — Retrieve the activity
if act_id:
    r = httpx.get(f'{BASE}/api/v3/activities/{act_id}', headers=h(tok_member), timeout=10)
    chk('A3 Retrieve activity returns 200', r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        chk('A3 Title preserved', d.get('title') == 'RTIFN Birmingham Community Outreach — Validation Test')
        chk('A3 Status is Draft (self-reported)', d.get('verification_status') == 'Draft')
        chk('A3 is_verified = False (not verified)', d.get('is_verified') == False)

# A4 — Confirm persistence via DB
if act_id:
    count = db.execute(text('SELECT COUNT(*) FROM activities WHERE id = :id'), {'id': act_id}).scalar()
    chk('A4 Activity persisted in database', count == 1)

# A5 — Ward activity geographic resolution
if ward_act_id:
    r = httpx.get(f'{BASE}/api/v3/activities/{ward_act_id}', headers=h(tok_member), timeout=10)
    chk('A5 Ward activity geographic data returned', r.status_code == 200)
    if r.status_code == 200:
        geo = r.json().get('geography', {})
        chk('A5 State resolved in response', geo.get('state') is not None)
        chk('A5 Ward resolved in response', geo.get('ward') is not None)

# A6 — Submit for verification (Draft → Submitted)
if act_id:
    r = httpx.post(f'{BASE}/api/v3/activities/{act_id}/verify',
        headers=h(tok_member), json={'action': 'submit'}, timeout=10)
    chk('A6 Submit activity (Draft → Submitted)', r.status_code == 200)

# ── Workflow B: Volunteer ──────────────────────────────────────
print('\n[WORKFLOW B] Volunteer: Create → Retrieve → Confirm Persistence')

r = httpx.post(f'{BASE}/api/v3/volunteer/', headers=h(tok_member),
    json={
        'volunteer_type': 'community',
        'description': 'RTIFN Birmingham volunteer validation record. Self-reported.',
        'hours_contributed': 3.0,
        'volunteer_date': '2026-09-19',
        'skills_used': [],
    }, timeout=10)
chk('B1 Create volunteer record (201)', r.status_code == 201, r.text[:80])
vol_id = r.json().get('id') if r.status_code == 201 else None

if vol_id:
    r = httpx.get(f'{BASE}/api/v3/volunteer/{vol_id}', headers=h(tok_member), timeout=10)
    chk('B2 Retrieve volunteer record (200)', r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        chk('B2 Hours preserved', d.get('hours_contributed') == 3.0)
        chk('B2 Status is Draft', d.get('verification_status') == 'Draft')
    count = db.execute(text('SELECT COUNT(*) FROM volunteer_records WHERE id = :id'), {'id': vol_id}).scalar()
    chk('B3 Volunteer record persisted in database', count == 1)

# ── Workflow C: Project ────────────────────────────────────────
print('\n[WORKFLOW C] Project: Create → Retrieve → Confirm Persistence')

r = httpx.post(f'{BASE}/api/v3/projects/', headers=h(tok_director),
    json={
        'name': 'RTIFN Birmingham Community Engagement Programme 2026',
        'description': 'Functional validation project record. RTIFN tenant-owned.',
        'project_type': 'community',
        'visibility': 'tenant',
        'is_independent': False,
        'geo_scope': 'unspecified',
    }, timeout=10)
chk('C1 Create tenant project (201)', r.status_code == 201, r.text[:80])
proj_id = r.json().get('id') if r.status_code == 201 else None

if proj_id:
    r = httpx.get(f'{BASE}/api/v3/projects/{proj_id}', headers=h(tok_director), timeout=10)
    chk('C2 Retrieve project (200)', r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        chk('C2 Name preserved', 'Birmingham' in d.get('name', ''))
        chk('C2 Status is Draft', d.get('status') == 'Draft')
        chk('C2 is_independent = False', d.get('is_independent') == False)
    count = db.execute(text('SELECT COUNT(*) FROM projects WHERE id = :id'), {'id': proj_id}).scalar()
    chk('C3 Project persisted in database', count == 1)

    # Link activity to project
    if act_id:
        r = httpx.post(f'{BASE}/api/v3/activities/', headers=h(tok_member),
            json={
                'activity_type': 'meeting',
                'title': 'Project Kick-off — Birmingham Engagement Programme',
                'activity_date': '2026-09-19',
                'project_id': proj_id,
                'description': 'Project-linked activity validation record',
            }, timeout=10)
        chk('C4 Create activity linked to project (201)', r.status_code == 201, r.text[:80])

# ── Donation record ────────────────────────────────────────────
print('\n[DONATION] Donation record creation')
r = httpx.post(f'{BASE}/api/v3/donations/', headers=h(tok_director),
    json={
        'donation_type': 'donation',
        'donation_date': '2026-09-19',
        'donor_external_name': 'Validation Test Donor',
        'amount': 1.0,
        'currency': 'GBP',
        'notes': 'Functional validation record — not a real donation',
    }, timeout=10)
chk('D1 Create donation record (201)', r.status_code == 201, r.text[:80])
don_id = r.json().get('id') if r.status_code == 201 else None
if don_id:
    r = httpx.get(f'{BASE}/api/v3/donations/{don_id}', headers=h(tok_director), timeout=10)
    chk('D2 Retrieve donation (200)', r.status_code == 200)

# ── Communication record ───────────────────────────────────────
print('\n[COMMUNICATION] Communication record creation')
r = httpx.post(f'{BASE}/api/v3/communications/', headers=h(tok_director),
    json={
        'communication_type': 'email',
        'subject': 'RTIFN Birmingham — Validation Test Communication',
        'communication_date': '2026-09-19',
        'recipient_external': 'validation@test.ndip',
        'notes': 'Functional validation record',
        'status': 'sent',
    }, timeout=10)
chk('E1 Create communication record (201)', r.status_code == 201, r.text[:80])
comm_id = r.json().get('id') if r.status_code == 201 else None
if comm_id:
    r = httpx.get(f'{BASE}/api/v3/communications/{comm_id}', headers=h(tok_director), timeout=10)
    chk('E2 Retrieve communication (200)', r.status_code == 200)

# ── List endpoints ──────────────────────────────────────────────
print('\n[LISTS] List all entity types')
for label, url in [
    ('Activities list', f'{BASE}/api/v3/activities/'),
    ('Volunteer list', f'{BASE}/api/v3/volunteer/'),
    ('Projects list', f'{BASE}/api/v3/projects/'),
    ('Donations list', f'{BASE}/api/v3/donations/'),
    ('Communications list', f'{BASE}/api/v3/communications/'),
]:
    r = httpx.get(url, headers=h(tok_member), timeout=10)
    chk(f'{label} (200)', r.status_code == 200,
        f"total={r.json().get('total', '?')}" if r.status_code == 200 else r.text[:50])

# ── Intelligence endpoints ─────────────────────────────────────
print('\n[INTELLIGENCE] Intelligence endpoints')
for label, url in [
    ('Health check', f'{BASE}/health'),
    ('Readiness', f'{BASE}/readiness'),
    ('Geography states', f'{BASE}/api/v2/geography/states'),
]:
    r = httpx.get(url, timeout=10)
    chk(f'{label} (200)', r.status_code == 200)

# ── Record counts ───────────────────────────────────────────────
print('\n[COUNTS] Final record counts')
for table in ['activities', 'volunteer_records', 'projects', 'donations', 'communications']:
    count = db.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar()
    print(f'  {table}: {count} rows')

print(f'  ng_wards: {db.execute(text("SELECT COUNT(*) FROM ng_wards")).scalar()} rows')
print(f'  normalised_posts: {db.execute(text("SELECT COUNT(*) FROM normalised_posts")).scalar()} rows')

db.close()

# ── Summary ────────────────────────────────────────────────────
print('\n' + '=' * 65)
print('FUNCTIONAL VALIDATION SUMMARY')
print(f'Passed: {len(passed)}  Failed: {len(failed)}')
if failed:
    print('\nFailed:')
    for f in failed: print(f'  - {f}')
verdict = 'GREEN' if len(failed) == 0 else ('AMBER' if len(failed) <= 3 else 'RED')
print(f'\nRESULT: {verdict}')
print('=' * 65)
