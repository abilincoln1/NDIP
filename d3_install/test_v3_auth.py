"""
D5A-S2: Seed superadmin as a platform identity and test v3 login.
Run via: docker exec ndip-backend-1 python3 /tmp/test_v3_auth.py
"""
import sys
import os
sys.path.insert(0, '/app')

# Container DB is at hostname 'db' not 'localhost'
os.environ['DATABASE_URL'] = 'postgresql://agora_user:agora_pass@db:5432/agora_db'

from dotenv import load_dotenv
load_dotenv('/app/.env', override=True)
from app.core.config import get_settings
get_settings.cache_clear()

from app.db.database import SessionLocal
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
import bcrypt
import httpx

# Use direct engine to guarantee container DB URL
engine = create_engine('postgresql://agora_user:agora_pass@db:5432/agora_db')
Session = sessionmaker(bind=engine)
db = Session()

print('=== D5A-S2: Platform Identity Seed & v3 Auth Test ===')
print()

# 1. Check if superadmin platform identity already exists
existing = db.execute(
    text("SELECT id FROM platform_identities WHERE email = 'superadmin@ndip.rtifn.org'")
).fetchone()

if existing:
    identity_id = str(existing.id)
    print(f'Platform identity already exists: {identity_id}')
else:
    # Get v2 member record
    v2_member = db.execute(
        text("SELECT id, full_name, phone FROM members WHERE email = 'superadmin@ndip.rtifn.org'")
    ).fetchone()

    if not v2_member:
        print('ERROR: v2 superadmin member not found')
        db.close()
        sys.exit(1)

    # Get UK country id
    uk = db.execute(
        text("SELECT id FROM countries WHERE iso_code = 'GB'")
    ).fetchone()

    identity = db.execute(
        text("""
            INSERT INTO platform_identities
                (id, email, full_name, phone, identity_status, residence_country_id)
            VALUES
                (:id, 'superadmin@ndip.rtifn.org', :name, :phone, 'active', :cid)
            ON CONFLICT (email) DO UPDATE SET full_name = EXCLUDED.full_name
            RETURNING id, email, full_name
        """),
        {
            'id': str(v2_member.id),
            'name': v2_member.full_name or 'Super Admin',
            'phone': v2_member.phone,
            'cid': str(uk.id) if uk else None,
        }
    ).fetchone()
    identity_id = str(identity.id)
    print(f'Created platform identity: {identity_id}')

    # Copy password hash from v2
    v2_auth = db.execute(
        text("SELECT hashed_password AS password_hash FROM members WHERE id = :id"),
        {'id': identity_id}
    ).fetchone()

    if v2_auth:
        pw_hash = v2_auth.password_hash
        print(f'  auth: password hash copied from v2')
    else:
        pw_hash = bcrypt.hashpw(b'TestPass2026!', bcrypt.gensalt(12)).decode()
        print(f'  auth: fresh bcrypt hash generated')

    db.execute(
        text("""
            INSERT INTO platform_identity_auth (identity_id, password_hash)
            VALUES (:id, :hash)
            ON CONFLICT (identity_id) DO NOTHING
        """),
        {'id': identity_id, 'hash': pw_hash}
    )

    # Make platform super_admin
    db.execute(
        text("""
            INSERT INTO platform_admins (identity_id, admin_level)
            VALUES (:id, 'super_admin')
            ON CONFLICT (identity_id) DO NOTHING
        """),
        {'id': identity_id}
    )
    print(f'  role: platform super_admin assigned')

db.commit()

# 2. Test v3 login
print()
print('Testing POST /api/v3/auth/login ...')
response = httpx.post(
    'http://localhost:8000/api/v3/auth/login',
    json={
        'email': 'superadmin@ndip.rtifn.org',
        'password': 'TestPass2026!',
        'tenant_slug': 'rtifn'
    },
    timeout=10
)

if response.status_code == 200:
    data = response.json()
    token = data['access_token']
    print(f'  PASS: v3 login successful')
    print(f'  identity_id:  {data["identity_id"]}')
    print(f'  tenant_id:    {data["tenant_id"]}')
    print(f'  full_name:    {data["full_name"]}')
    print(f'  roles:        {data["roles"]}')
    print(f'  admin_level:  {data["admin_level"]}')

    # 3. Test /me
    print()
    print('Testing GET /api/v3/auth/me ...')
    me = httpx.get(
        'http://localhost:8000/api/v3/auth/me',
        headers={'Authorization': f'Bearer {token}'},
        timeout=10
    )
    if me.status_code == 200:
        d = me.json()
        print(f'  PASS: /me successful')
        print(f'  email:       {d["email"]}')
        print(f'  admin_level: {d["admin_level"]}')
        print(f'  memberships: {len(d["memberships"])} active')
    else:
        print(f'  FAIL: {me.status_code} {me.text}')

    # 4. Test tenant list
    print()
    print('Testing GET /api/v3/tenants/ ...')
    tenants = httpx.get(
        'http://localhost:8000/api/v3/tenants/',
        headers={'Authorization': f'Bearer {token}'},
        timeout=10
    )
    if tenants.status_code == 200:
        tlist = tenants.json()
        print(f'  PASS: {len(tlist)} tenant(s) returned')
        for t in tlist:
            print(f'  - {t["slug"]}: {t["name"]} ({t["status"]})')
    else:
        print(f'  FAIL: {tenants.status_code} {tenants.text}')

    # 5. RLS isolation test
    # SET LOCAL only works inside a transaction — must use BEGIN explicitly
    print()
    print('Testing RLS cross-tenant isolation ...')
    from sqlalchemy import event
    db2 = Session()
    # Begin explicit transaction so SET LOCAL takes effect
    db2.execute(text("BEGIN"))
    db2.execute(text("SET LOCAL app.current_tenant_id = '00000000-0000-0000-0000-000000000000'"))
    count = db2.execute(text("SELECT COUNT(*) FROM organisations")).scalar()
    db2.execute(text("ROLLBACK"))
    db2.close()
    if count == 0:
        print(f'  PASS: RLS confirmed — cross-tenant query returns 0 rows')
    else:
        print(f'  FAIL: RLS broken — cross-tenant query returned {count} rows')

else:
    print(f'  FAIL: {response.status_code} {response.text}')

db.close()
print()
print('=== D5A-S2 AUTH TEST COMPLETE ===')
