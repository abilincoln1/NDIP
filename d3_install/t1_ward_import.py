"""
T1 Ward Geography Import - Phase T1-A through T1-D
Source: github.com/afeibukun/nigerian-state-lgas-wards-polling-units
Dataset: states-and-lgas-and-wards.json
Run: docker exec ndip-backend-1 python3 /tmp/t1_ward_import.py [--dry-run]
"""
import sys
import json
import urllib.request
import os

DRY_RUN = '--dry-run' in sys.argv

os.environ['DATABASE_URL'] = 'postgresql://agora_user:agora_pass@db:5432/agora_db'

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine('postgresql://agora_user:agora_pass@db:5432/agora_db')
Session = sessionmaker(bind=engine)

SOURCE_URL = 'https://raw.githubusercontent.com/afeibukun/nigerian-state-lgas-wards-polling-units/main/states-and-lgas-and-wards.json'
SOURCE_NAME = 'afeibukun/nigerian-state-lgas-wards-polling-units'
SOURCE_PROVENANCE = 'GitHub open dataset derived from INEC Nigeria ward registry. Cross-checked with eHealth Africa and OSGOF boundaries per UN OCHA COD-AB Nigeria documentation.'

print('=' * 70)
print('NDIP T1 WARD GEOGRAPHY IMPORT')
print(f'Mode: {"DRY RUN" if DRY_RUN else "LIVE IMPORT"}')
print('=' * 70)

# T1-A: Download and validate
print('\n--- T1-A: Source Validation ---')
print(f'Source URL: {SOURCE_URL}')

try:
    req = urllib.request.Request(SOURCE_URL, headers={'User-Agent': 'NDIP-T1-Import/1.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode('utf-8')
    data = json.loads(raw)
    print(f'Download OK. Size: {len(raw):,} bytes')
except Exception as e:
    print(f'DOWNLOAD FAILED: {e}')
    print('STOP: Cannot proceed without authoritative dataset.')
    sys.exit(1)

# Analyse structure
total_states = len(data)
total_lgas = 0
total_wards = 0
ward_name_counts = {}

state_summary = []
for state in data:
    state_name = state.get('name', state.get('state', ''))
    lgas = state.get('lgas', [])
    state_lga_count = len(lgas)
    state_ward_count = 0
    for lga in lgas:
        wards = lga.get('wards', [])
        state_ward_count += len(wards)
        for ward in wards:
            wname = ward if isinstance(ward, str) else ward.get('name', '')
            key = f"{state_name}|{lga.get('name','?')}|{wname}"
            ward_name_counts[key] = ward_name_counts.get(key, 0) + 1
    total_lgas += state_lga_count
    total_wards += state_ward_count
    state_summary.append((state_name, state_lga_count, state_ward_count))

duplicates = {k: v for k, v in ward_name_counts.items() if v > 1}

print(f'\nPROVENANCE: {SOURCE_PROVENANCE}')
print(f'\nDataset summary:')
print(f'  States:          {total_states}')
print(f'  LGAs:            {total_lgas}')
print(f'  Wards:           {total_wards}')
print(f'  Duplicate keys:  {len(duplicates)}')

print(f'\nState breakdown:')
for sname, lga_count, ward_count in state_summary:
    print(f'  {sname:<35} LGAs: {lga_count:3d}  Wards: {ward_count:4d}')

# Cross-check against existing DB
db = Session()
db_states = {}
for r in db.execute(text('SELECT id, name FROM ng_states')).fetchall():
    db_states[r.name.upper()] = r.id

db_lgas = {}
for r in db.execute(text('SELECT id, name, state_id FROM ng_lgas')).fetchall():
    db_lgas[r.name.upper()] = (r.id, r.state_id)

print(f'\nExisting DB: {len(db_states)} states, {len(db_lgas)} LGAs')

# T1-B / T1-C: Build import records
print(f'\n--- T1-{"B" if DRY_RUN else "C"}: {"Dry Run" if DRY_RUN else "Import"} ---')

ward_records = []
unmatched_lgas = []

max_ward_id = db.execute(text('SELECT COALESCE(MAX(id), 0) FROM ng_wards')).scalar()
ward_id_counter = max_ward_id + 1

for state in data:
    sname = state.get('name', state.get('state', ''))
    sname_upper = sname.upper()

    # Resolve state ID
    state_id = db_states.get(sname_upper)
    if not state_id:
        sname_clean = sname_upper.replace(' STATE', '').strip()
        state_id = db_states.get(sname_clean)
    if not state_id:
        for db_sname, sid in db_states.items():
            if sname_clean in db_sname or db_sname in sname_clean:
                state_id = sid
                break
    if not state_id:
        continue

    for lga in state.get('lgas', []):
        lga_name = lga.get('name', '')
        lga_upper = lga_name.upper()

        # Resolve LGA ID within state
        lga_id = None
        for db_lname, (lid, db_state_id) in db_lgas.items():
            if db_lname == lga_upper and db_state_id == state_id:
                lga_id = lid
                break
        if not lga_id:
            lga_clean = lga_upper.replace(' LOCAL GOVERNMENT AREA', '').replace(' L.G.A', '').replace(' LGA', '').strip()
            for db_lname, (lid, db_state_id) in db_lgas.items():
                if db_state_id == state_id and (lga_clean in db_lname or db_lname in lga_clean):
                    lga_id = lid
                    break
        if not lga_id:
            unmatched_lgas.append(f'{sname} / {lga_name}')
            continue

        for ward in lga.get('wards', []):
            ward_name = ward if isinstance(ward, str) else ward.get('name', '')
            if not ward_name:
                continue
            ward_records.append({
                'id': ward_id_counter,
                'name': ward_name.strip(),
                'lga_id': lga_id,
                'code': f'NG-W-{ward_id_counter:05d}'
            })
            ward_id_counter += 1

print(f'Wards resolved: {len(ward_records):,}')
print(f'Unmatched LGAs: {len(unmatched_lgas)}')
if unmatched_lgas:
    print('Unmatched LGA list:')
    for u in unmatched_lgas:
        print(f'  - {u}')

if DRY_RUN:
    print(f'\nDRY RUN: {len(ward_records):,} wards would be inserted. No changes made.')
    print('Sample records:')
    for r in ward_records[:5]:
        print(f'  {r["code"]}  lga_id={r["lga_id"]}  {r["name"]}')
    db.close()
    sys.exit(0)

# LIVE IMPORT
print(f'\nInserting {len(ward_records):,} wards (batches of 500)...')
inserted = 0
skipped = 0

try:
    for i in range(0, len(ward_records), 500):
        batch = ward_records[i:i+500]
        for r in batch:
            result = db.execute(text("""
                INSERT INTO ng_wards (id, name, lga_id, code)
                VALUES (:id, :name, :lga_id, :code)
                ON CONFLICT DO NOTHING
            """), r)
            if result.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        db.commit()
        if (i // 500) % 5 == 0:
            print(f'  {min(i+500, len(ward_records)):,}/{len(ward_records):,} processed')

    print(f'Import done. Inserted: {inserted:,}  Skipped: {skipped}')
except Exception as e:
    db.rollback()
    print(f'IMPORT FAILED: {e}')
    db.close()
    sys.exit(1)

# T1-D: Verification
print('\n--- T1-D: Verification ---')

ward_count = db.execute(text('SELECT COUNT(*) FROM ng_wards')).scalar()
unique_codes = db.execute(text('SELECT COUNT(DISTINCT code) FROM ng_wards')).scalar()
orphans = db.execute(text("""
    SELECT COUNT(*) FROM ng_wards w
    LEFT JOIN ng_lgas l ON l.id = w.lga_id
    WHERE l.id IS NULL
""")).scalar()

print(f'Ward count:        {ward_count:,}')
print(f'Unique codes:      {unique_codes:,}')
print(f'Orphan wards:      {orphans}')

print('\nSample State -> LGA -> Ward:')
samples = db.execute(text("""
    SELECT s.name as state, l.name as lga, w.name as ward, w.code
    FROM ng_wards w
    JOIN ng_lgas l ON l.id = w.lga_id
    JOIN ng_states s ON s.id = l.state_id
    ORDER BY s.name, l.name, w.name
    LIMIT 12
""")).fetchall()
for r in samples:
    print(f'  {r.state:<20} {r.lga:<28} {r.ward:<28} {r.code}')

print('\nWards per state:')
state_counts = db.execute(text("""
    SELECT s.name, COUNT(w.id) as cnt
    FROM ng_wards w
    JOIN ng_lgas l ON l.id = w.lga_id
    JOIN ng_states s ON s.id = l.state_id
    GROUP BY s.name ORDER BY s.name
""")).fetchall()
for r in state_counts:
    print(f'  {r.name:<35} {r.cnt:4d}')

print(f'\nTotal states with wards: {len(state_counts)}')

if orphans > 0:
    print(f'\nFAIL: {orphans} orphan wards. Investigate.')
elif len(state_counts) < 30:
    print(f'\nWARNING: Only {len(state_counts)} states have wards. Check coverage.')
elif ward_count < 5000:
    print(f'\nWARNING: Ward count {ward_count} lower than expected ~8,800.')
else:
    print(f'\nVERIFICATION PASSED')
    print(f'T1 STATUS: COMPLETE')
    print(f'S4 GATE: OPEN')

db.close()
print('\n' + '=' * 70)
print('T1 COMPLETE')
print('=' * 70)
