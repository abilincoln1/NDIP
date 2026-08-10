"""
D5A-T1A Geographic Completion
Supplementary ward reconciliation for:
  - Akwa Ibom (source: akwa-ibom)
  - Cross River (source: cross-river)
  - Federal Capital Territory (source: abuja)

Source: github.com/afeibukun/nigerian-state-lgas-wards-polling-units
Run: docker exec ndip-backend-1 python3 /tmp/t1a_geography_completion.py [--dry-run]
"""
import sys, os, json, urllib.request

DRY_RUN = '--dry-run' in sys.argv
os.environ['DATABASE_URL'] = 'postgresql://agora_user:agora_pass@db:5432/agora_db'

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine('postgresql://agora_user:agora_pass@db:5432/agora_db')
db = sessionmaker(bind=engine)()

SOURCE_URL = 'https://raw.githubusercontent.com/afeibukun/nigerian-state-lgas-wards-polling-units/main/states-and-lgas-and-wards.json'

print('=' * 70)
print('D5A-T1A: GEOGRAPHIC COMPLETION — THREE-STATE RECONCILIATION')
print(f'Mode: {"DRY RUN" if DRY_RUN else "LIVE IMPORT"}')
print('=' * 70)

# ── Download source ────────────────────────────────────────────────────────────
print('\nDownloading source dataset...')
req = urllib.request.Request(SOURCE_URL, headers={'User-Agent': 'NDIP-T1A/1.0'})
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode('utf-8'))
print(f'Downloaded: {len(data)} states in source')

# ── Build source name → state mapping ─────────────────────────────────────────
# The three target states have these slugs in the source:
TARGET_MAP = {
    'akwa-ibom':  'Akwa Ibom',
    'cross-river': 'Cross River',
    'abuja':       'Federal Capital Territory',
}

# ── Load DB state and LGA data ─────────────────────────────────────────────────
db_states = {r.name: r.id for r in db.execute(text('SELECT id, name FROM ng_states')).fetchall()}
db_lgas_by_state = {}
for r in db.execute(text('SELECT id, name, state_id FROM ng_lgas')).fetchall():
    if r.state_id not in db_lgas_by_state:
        db_lgas_by_state[r.state_id] = {}
    db_lgas_by_state[r.state_id][r.name.upper()] = r.id

# ── Get max existing ward ID ───────────────────────────────────────────────────
max_id = db.execute(text('SELECT COALESCE(MAX(id), 0) FROM ng_wards')).scalar()
ward_id_counter = max_id + 1

print(f'\nExisting wards in DB: {max_id}')
print(f'Starting new ward IDs from: {ward_id_counter}')

# ── Process each target state ─────────────────────────────────────────────────
all_results = {}
total_to_insert = []

for source_slug, db_state_name in TARGET_MAP.items():
    print(f'\n{"─"*60}')
    print(f'Processing: {source_slug} → DB: {db_state_name}')

    # Find in source
    source_state = None
    for s in data:
        sname = s.get('name', s.get('state', ''))
        if sname.lower() == source_slug.lower():
            source_state = s
            break

    if not source_state:
        print(f'  ERROR: {source_slug} not found in source dataset')
        all_results[db_state_name] = {'error': 'not found in source'}
        continue

    # Get DB state ID
    state_id = db_states.get(db_state_name)
    if not state_id:
        print(f'  ERROR: {db_state_name} not found in DB')
        all_results[db_state_name] = {'error': 'not found in DB'}
        continue

    state_lgas = db_lgas_by_state.get(state_id, {})
    print(f'  DB LGAs for this state: {len(state_lgas)}')

    lgas = source_state.get('lgas', [])
    print(f'  Source LGAs: {len(lgas)}')
    print(f'  Source wards: {sum(len(l.get("wards",[])) for l in lgas)}')

    matched_lgas = 0
    unmatched_lgas = []
    wards_resolved = []
    wards_skipped_dup = []

    # Get existing ward names for this state (to detect duplicates)
    existing_wards = set()
    existing = db.execute(text("""
        SELECT w.name, w.lga_id FROM ng_wards w
        JOIN ng_lgas l ON l.id = w.lga_id
        WHERE l.state_id = :sid
    """), {'sid': state_id}).fetchall()
    for ew in existing:
        existing_wards.add((ew.name.upper(), ew.lga_id))

    for lga in lgas:
        lga_name = lga.get('name', '')
        lga_upper = lga_name.upper()

        # Try exact match first
        lga_id = state_lgas.get(lga_upper)

        # Try without common suffixes
        if not lga_id:
            cleaned = lga_upper.replace(' LOCAL GOVERNMENT AREA','').replace(' LGA','').replace(' L.G.A','').strip()
            lga_id = state_lgas.get(cleaned)

        # Try partial match
        if not lga_id:
            for db_lname, lid in state_lgas.items():
                if cleaned in db_lname or db_lname in cleaned:
                    lga_id = lid
                    break

        if not lga_id:
            unmatched_lgas.append(lga_name)
            continue

        matched_lgas += 1
        for ward in lga.get('wards', []):
            ward_name = ward if isinstance(ward, str) else ward.get('name', '')
            if not ward_name:
                continue
            ward_name = ward_name.strip()

            # Check duplicate
            if (ward_name.upper(), lga_id) in existing_wards:
                wards_skipped_dup.append(ward_name)
                continue

            wards_resolved.append({
                'id': ward_id_counter,
                'name': ward_name,
                'lga_id': lga_id,
                'code': f'NG-W-{ward_id_counter:05d}'
            })
            existing_wards.add((ward_name.upper(), lga_id))
            ward_id_counter += 1

    print(f'  LGAs matched: {matched_lgas}/{len(lgas)}')
    if unmatched_lgas:
        print(f'  Unmatched LGAs ({len(unmatched_lgas)}):')
        for u in unmatched_lgas:
            print(f'    - {u}')
    print(f'  Wards to insert: {len(wards_resolved)}')
    print(f'  Wards skipped (already loaded): {len(wards_skipped_dup)}')

    all_results[db_state_name] = {
        'source_lgas': len(lgas),
        'matched_lgas': matched_lgas,
        'unmatched_lgas': unmatched_lgas,
        'wards_to_insert': len(wards_resolved),
        'wards_skipped': len(wards_skipped_dup),
    }
    total_to_insert.extend(wards_resolved)

# ── 8813 reconciliation ────────────────────────────────────────────────────────
print(f'\n{"─"*60}')
print('8,813 Source Record Reconciliation:')
source_total = sum(len(l.get('wards',[])) for s in data for l in s.get('lgas',[]))
print(f'  Source total wards:          {source_total}')

# Count duplicates in source (same state/lga/ward name)
seen = set()
source_dups = 0
for s in data:
    sname = s.get('name', s.get('state',''))
    for lga in s.get('lgas',[]):
        lname = lga.get('name','')
        for ward in lga.get('wards',[]):
            wname = ward if isinstance(ward, str) else ward.get('name','')
            key = f'{sname}|{lname}|{wname}'
            if key in seen:
                source_dups += 1
            seen.add(key)

print(f'  Duplicate keys in source:    {source_dups}')
print(f'  After dedup:                 {source_total - source_dups}')
print(f'  Currently in DB:             {max_id}')
print(f'  T1A will add:                {len(total_to_insert)}')
print(f'  Expected final total:        {max_id + len(total_to_insert)}')
print(f'  Unexplained gap:             {(source_total - source_dups) - (max_id + len(total_to_insert))}')

if DRY_RUN:
    print(f'\nDRY RUN: {len(total_to_insert)} wards would be inserted. No changes made.')
    for state, res in all_results.items():
        print(f'  {state}: {res}')
    db.close()
    sys.exit(0)

# ── Live import ────────────────────────────────────────────────────────────────
print(f'\n{"─"*60}')
print(f'LIVE IMPORT: inserting {len(total_to_insert)} wards...')
inserted = 0
skipped = 0

try:
    for i in range(0, len(total_to_insert), 200):
        batch = total_to_insert[i:i+200]
        for r in batch:
            result = db.execute(text("""
                INSERT INTO ng_wards (id, name, lga_id, code, created_at)
                VALUES (:id, :name, :lga_id, :code, NOW())
                ON CONFLICT DO NOTHING
            """), r)
            if result.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        db.commit()
    print(f'Import complete. Inserted: {inserted}  Skipped: {skipped}')
except Exception as e:
    db.rollback()
    print(f'IMPORT FAILED: {e}')
    db.close()
    sys.exit(1)

# ── Final verification ─────────────────────────────────────────────────────────
print(f'\n{"─"*60}')
print('FINAL VERIFICATION:')

final_counts = db.execute(text("""
    SELECT s.name as state, COUNT(w.id) as ward_count
    FROM ng_wards w
    JOIN ng_lgas l ON l.id = w.lga_id
    JOIN ng_states s ON s.id = l.state_id
    GROUP BY s.name ORDER BY s.name
""")).fetchall()

total_final = sum(r.ward_count for r in final_counts)
states_with_wards = len(final_counts)

print(f'\nFinal ward counts by state:')
for r in final_counts:
    marker = ' *** T1A' if r.state in TARGET_MAP.values() else ''
    print(f'  {r.state:<35} {r.ward_count:4d}{marker}')

print(f'\nTotal states with wards: {states_with_wards}/37')
print(f'Total wards:             {total_final}')

orphans = db.execute(text("""
    SELECT COUNT(*) FROM ng_wards w
    LEFT JOIN ng_lgas l ON l.id = w.lga_id WHERE l.id IS NULL
""")).scalar()
print(f'Orphan wards:            {orphans}')

unique_codes = db.execute(text('SELECT COUNT(DISTINCT code) FROM ng_wards')).scalar()
print(f'Unique ward codes:       {unique_codes}')

# Three-state specific
for state_name in TARGET_MAP.values():
    count = db.execute(text("""
        SELECT COUNT(w.id) FROM ng_wards w
        JOIN ng_lgas l ON l.id = w.lga_id
        JOIN ng_states s ON s.id = l.state_id
        WHERE s.name = :sname
    """), {'sname': state_name}).scalar()
    print(f'  {state_name}: {count} wards')

if states_with_wards == 37 and orphans == 0:
    print('\nT1A STATUS: COMPLETE')
    print('GEOGRAPHY STATUS: NATIONALLY COMPLETE — all 37 states have ward data')
elif states_with_wards >= 35:
    print(f'\nT1A STATUS: SUBSTANTIALLY COMPLETE — {states_with_wards}/37 states')
else:
    print(f'\nT1A STATUS: INCOMPLETE — only {states_with_wards}/37 states')

db.close()
print('\n' + '=' * 70)
print('T1A GEOGRAPHIC COMPLETION DONE')
print('=' * 70)
