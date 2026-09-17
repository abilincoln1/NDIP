"""
S6 Assessment — read-only database inspection
Run: docker exec ndip-backend-1 python3 /tmp/s6_inspect.py
"""
import os, sys
sys.path.insert(0, '/app')
os.environ['DATABASE_URL'] = 'postgresql://agora_user:agora_pass@db:5432/agora_db'
from sqlalchemy import create_engine, text
db = create_engine('postgresql://agora_user:agora_pass@db:5432/agora_db').connect()

print('=== ALL TABLES ===')
rows = db.execute(text("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema='public' ORDER BY table_name
""")).fetchall()
for r in rows:
    print(f'  {r[0]}')

print('\n=== DONATION/COMMUNICATION-RELATED TABLES ===')
rows = db.execute(text("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema='public'
    AND (table_name ILIKE '%donat%' OR table_name ILIKE '%communic%'
         OR table_name ILIKE '%payment%' OR table_name ILIKE '%receipt%'
         OR table_name ILIKE '%message%' OR table_name ILIKE '%sponsor%')
    ORDER BY table_name
""")).fetchall()
for r in rows:
    print(f'  {r[0]}')

print('\n=== WARD_SPONSORSHIPS SCHEMA ===')
rows = db.execute(text("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name='ward_sponsorships'
    ORDER BY ordinal_position
""")).fetchall()
for r in rows:
    print(f'  {r[0]} | {r[1]} | nullable={r[2]}')

print('\n=== WARD_SPONSORSHIPS ROWS ===')
count = db.execute(text('SELECT COUNT(*) FROM ward_sponsorships')).scalar()
print(f'  {count} rows')

print('\n=== V3 ROUTES IN OPENAPI (projects/activities) ===')
# Check main.py for registered routers
with open('/app/app/main.py') as f:
    main = f.read()
v3_routers = [l.strip() for l in main.split('\n') if 'include_router' in l and 'v3' in l.lower()]
for r in v3_routers:
    print(f'  {r}')

print('\n=== EXISTING EVIDENCE/VERIFICATION STRUCTURES ===')
rows = db.execute(text("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema='public'
    AND (table_name ILIKE '%evidence%' OR table_name ILIKE '%verif%')
    ORDER BY table_name
""")).fetchall()
for r in rows:
    print(f'  {r[0]}')

print('\n=== PLATFORM_PROJECTS SCHEMA ===')
rows = db.execute(text("""
    SELECT column_name, data_type FROM information_schema.columns
    WHERE table_name='platform_projects' ORDER BY ordinal_position
""")).fetchall()
for r in rows:
    print(f'  {r[0]} | {r[1]}')

print('\n=== PROJECTS TABLE (S5) COLUMN COUNT ===')
count = db.execute(text("""
    SELECT COUNT(*) FROM information_schema.columns WHERE table_name='projects'
""")).scalar()
print(f'  projects table: {count} columns')

print('\n=== PLATFORM_CONFIG ===')
rows = db.execute(text('SELECT key, value FROM platform_config ORDER BY key')).fetchall()
for r in rows:
    print(f'  {r[0]}: {r[1]}')

db.close()
