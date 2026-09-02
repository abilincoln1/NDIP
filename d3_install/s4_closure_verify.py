"""
D5A-S4 Closure Verification
Read-only. Confirms national geography, S4 tables, and RLS.
Run: docker exec ndip-backend-1 python3 /tmp/s4_closure_verify.py
"""
import os
os.environ['DATABASE_URL'] = 'postgresql://agora_user:agora_pass@db:5432/agora_db'
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://agora_user:agora_pass@db:5432/agora_db')
db = engine.connect()

passed = []
failed = []

def chk(label, cond, detail=''):
    if cond:
        passed.append(label)
        print(f'  [PASS] {label}')
    else:
        failed.append(label)
        print(f'  [FAIL] {label}{" — " + detail if detail else ""}')

print('=' * 65)
print('D5A-S4 CLOSURE VERIFICATION')
print('=' * 65)

# ── Geography ──────────────────────────────────────────────────
print('\n[1] National Geography')

states = db.execute(text('SELECT COUNT(*) FROM ng_states')).scalar()
lgas   = db.execute(text('SELECT COUNT(*) FROM ng_lgas')).scalar()
wards  = db.execute(text('SELECT COUNT(*) FROM ng_wards')).scalar()
orphans = db.execute(text('''
    SELECT COUNT(*) FROM ng_wards w
    LEFT JOIN ng_lgas l ON l.id = w.lga_id WHERE l.id IS NULL
''')).scalar()
unique_codes = db.execute(text('SELECT COUNT(DISTINCT code) FROM ng_wards')).scalar()

chk('States: 37', states == 37, f'got {states}')
chk('LGAs: 774', lgas == 774, f'got {lgas}')
chk('Wards: 8,714', wards == 8714, f'got {wards}')
chk('Orphan wards: 0', orphans == 0, f'got {orphans}')
chk('Unique ward codes = ward count', unique_codes == wards, f'{unique_codes} vs {wards}')

# Three previously missing states
for state_name, expected_min in [
    ('Akwa Ibom', 320), ('Cross River', 190), ('Federal Capital Territory', 60)
]:
    count = db.execute(text('''
        SELECT COUNT(w.id) FROM ng_wards w
        JOIN ng_lgas l ON l.id = w.lga_id
        JOIN ng_states s ON s.id = l.state_id
        WHERE s.name = :n
    '''), {'n': state_name}).scalar()
    chk(f'{state_name} has wards (>{expected_min})', count > expected_min, f'got {count}')

states_with_wards = db.execute(text('''
    SELECT COUNT(DISTINCT s.id) FROM ng_states s
    JOIN ng_lgas l ON l.state_id = s.id
    JOIN ng_wards w ON w.lga_id = l.id
''')).scalar()
chk('All 37 states have ward coverage', states_with_wards == 37, f'got {states_with_wards}')

# ── S4 Tables ──────────────────────────────────────────────────
print('\n[2] S4 Tables')

for tbl in ['activities', 'volunteer_records']:
    exists = db.execute(text('''
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = :t AND table_schema = 'public'
    '''), {'t': tbl}).scalar()
    chk(f'{tbl} table exists', exists == 1)

# activities columns
act_cols = [r[0] for r in db.execute(text('''
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'activities' AND table_schema = 'public'
'''))]
for col in ['tenant_id','recorded_by','activity_type_id','verification_status',
            'location_state_id','location_lga_id','location_ward_id',
            'location_polling_unit_id']:
    chk(f'activities.{col} exists', col in act_cols)

# PU FK stub
pu_nullable = db.execute(text('''
    SELECT is_nullable FROM information_schema.columns
    WHERE table_name = 'activities' AND column_name = 'location_polling_unit_id'
''')).scalar()
chk('location_polling_unit_id is nullable', pu_nullable == 'YES', f'got {pu_nullable}')

# ── Activity Types ─────────────────────────────────────────────
print('\n[3] Activity Types')
at_count = db.execute(text('SELECT COUNT(*) FROM activity_types')).scalar()
schemas  = db.execute(text('SELECT COUNT(*) FROM activity_types WHERE detail_schema IS NOT NULL')).scalar()
chk('15 activity types', at_count == 15, f'got {at_count}')
chk('All 15 have detail_schema', schemas == 15, f'got {schemas}')

# ── RLS ────────────────────────────────────────────────────────
print('\n[4] RLS Policies')
for tbl in ['activities', 'volunteer_records', 'memberships', 'organisations', 'kernel_roles']:
    rls = db.execute(text('''
        SELECT relrowsecurity FROM pg_class WHERE relname = :t
    '''), {'t': tbl}).scalar()
    chk(f'RLS enabled: {tbl}', rls == True)

# ── Workflow ───────────────────────────────────────────────────
print('\n[5] Verification Workflow')
wf = db.execute(text('''
    SELECT allowed_transitions FROM workflow_definitions WHERE is_system_default = TRUE
''')).scalar()
chk('Standard workflow defined', wf is not None)
if wf:
    import json
    transitions = wf if isinstance(wf, dict) else json.loads(wf)
    required_states = ['Draft','Submitted','Under Review','Verified','Rejected','Archived']
    for s in required_states:
        chk(f'Workflow state: {s}', s in transitions)

# ── Platform version ───────────────────────────────────────────
print('\n[6] Platform Version')
ver = db.execute(text("SELECT value FROM platform_config WHERE key = 'platform_version'")).scalar()
chk('Platform version = D5A-S4', 'D5A-S4' in str(ver), f'got {ver}')

# ── Polling unit table ─────────────────────────────────────────
print('\n[7] Polling Unit Architecture')
pu_exists = db.execute(text('''
    SELECT COUNT(*) FROM information_schema.tables
    WHERE table_name = 'ng_polling_units' AND table_schema = 'public'
''')).scalar()
pu_rows = db.execute(text('SELECT COUNT(*) FROM ng_polling_units')).scalar()
chk('ng_polling_units table exists', pu_exists == 1)
chk('ng_polling_units intentionally empty (0 rows)', pu_rows == 0, f'got {pu_rows}')

db.close()

print(f'\n{"=" * 65}')
print(f'S4 CLOSURE VERIFICATION SUMMARY')
print(f'Passed: {len(passed)}  Failed: {len(failed)}')
if failed:
    print('FAILED:')
    for f in failed:
        print(f'  - {f}')
verdict = 'CONFORMANT' if len(failed) == 0 else 'NON-CONFORMANT — see above'
print(f'S4 STATUS: {verdict}')
print('=' * 65)
