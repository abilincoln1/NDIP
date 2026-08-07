"""
D5A-S3: Test memberships and v3 login with roles.
Run: docker exec ndip-backend-1 python3 /tmp/test_v3_s3.py
"""
import sys, os
sys.path.insert(0, '/app')
os.environ['DATABASE_URL'] = 'postgresql://agora_user:agora_pass@db:5432/agora_db'
import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine('postgresql://agora_user:agora_pass@db:5432/agora_db')
Session = sessionmaker(bind=engine)
db = Session()

print('=== D5A-S3: Membership & Role Test ===')
print()

# 1. Check membership counts
total = db.execute(text("SELECT COUNT(*) FROM memberships")).scalar()
active = db.execute(text("SELECT COUNT(*) FROM memberships WHERE status='active'")).scalar()
invited = db.execute(text("SELECT COUNT(*) FROM memberships WHERE status='invited'")).scalar()
roles = db.execute(text("SELECT COUNT(*) FROM membership_roles")).scalar()
print(f'Memberships total:  {total} (expect 17)')
print(f'Memberships active: {active} (expect 7)')
print(f'Memberships invited:{invited} (expect 10)')
print(f'Membership roles:   {roles} (expect 17)')
print()

# 2. Test v3 login now returns roles
print('Testing v3 login returns roles...')
resp = httpx.post('http://localhost:8000/api/v3/auth/login',
    json={'email':'superadmin@ndip.rtifn.org','password':'TestPass2026!','tenant_slug':'rtifn'},
    timeout=10)
if resp.status_code == 200:
    d = resp.json()
    print(f'  PASS: login successful')
    print(f'  roles: {d["roles"]}')
    print(f'  admin_level: {d["admin_level"]}')
    token = d['access_token']
else:
    print(f'  FAIL: {resp.status_code} {resp.text}')
    db.close()
    sys.exit(1)

# 3. Test /me shows memberships
print()
print('Testing /me shows memberships...')
me = httpx.get('http://localhost:8000/api/v3/auth/me',
    headers={'Authorization': f'Bearer {token}'}, timeout=10)
if me.status_code == 200:
    d = me.json()
    print(f'  PASS: {len(d["memberships"])} active membership(s)')
    for m in d['memberships']:
        print(f'  - {m["membership_number"]} | {m["organisation"]} | {m["status"]}')
else:
    print(f'  FAIL: {me.status_code} {me.text}')

# 4. Test standard_member login gets correct role
print()
print('Testing standard_member role assignment...')
r2 = httpx.post('http://localhost:8000/api/v3/auth/login',
    json={'email':'member@ndip.rtifn.org','password':'TestPass2026!','tenant_slug':'rtifn'},
    timeout=10)
if r2.status_code == 200:
    d2 = r2.json()
    print(f'  PASS: standard_member login')
    print(f'  roles: {d2["roles"]}')
else:
    print(f'  FAIL: {r2.status_code} {r2.text}')

db.close()
print()
print('=== D5A-S3 TEST COMPLETE ===')
