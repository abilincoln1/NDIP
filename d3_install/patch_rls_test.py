"""
Patches the RLS test in test_v3_auth.py to use explicit transaction.
Run: docker exec ndip-backend-1 python3 /tmp/patch_rls_test.py
"""
TARGET = '/tmp/test_v3_auth.py'

with open(TARGET, 'r') as f:
    c = f.read()

old = '''    # 5. RLS isolation test
    print()
    print('Testing RLS cross-tenant isolation ...')
    db2 = Session()
    db2.execute(text("SET LOCAL app.current_tenant_id = '00000000-0000-0000-0000-000000000000'"))
    count = db2.execute(text("SELECT COUNT(*) FROM organisations")).scalar()
    db2.close()
    if count == 0:
        print(f'  PASS: RLS confirmed — cross-tenant query returns 0 rows')
    else:
        print(f'  FAIL: RLS broken — cross-tenant query returned {count} rows')'''

new = '''    # 5. RLS isolation test — SET LOCAL requires explicit transaction
    print()
    print('Testing RLS cross-tenant isolation ...')
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    eng2 = create_engine('postgresql://agora_user:agora_pass@db:5432/agora_db')
    with eng2.connect() as conn:
        conn.execute(text("SET LOCAL app.current_tenant_id = '00000000-0000-0000-0000-000000000000'"))
        count = conn.execute(text("SELECT COUNT(*) FROM organisations")).scalar()
    if count == 0:
        print(f'  PASS: RLS confirmed — cross-tenant query returns 0 rows')
    else:
        print(f'  FAIL: RLS broken — cross-tenant query returned {count} rows')'''

if old in c:
    c = c.replace(old, new)
    print("RLS test fix applied")
else:
    print("Pattern not found — checking what's there:")
    for i, line in enumerate(c.split('\n')):
        if 'RLS' in line or 'cross-tenant' in line:
            print(f"  {i+1}: {line}")

with open(TARGET, 'w') as f:
    f.write(c)
print("Done")
