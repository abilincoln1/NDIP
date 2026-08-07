"""
Replaces the RLS test block by line number injection.
Run: docker exec ndip-backend-1 python3 /tmp/patch_rls_test2.py
"""
TARGET = '/tmp/test_v3_auth.py'

with open(TARGET, 'r') as f:
    lines = f.readlines()

# Find the RLS test section start
start = None
for i, line in enumerate(lines):
    if '# 5. RLS isolation test' in line:
        start = i
        break

if start is None:
    print("ERROR: Could not find RLS test section")
    exit(1)

# Find the end of the block (next blank line after the if/else)
end = start
for i in range(start, len(lines)):
    if 'FAIL: RLS broken' in lines[i]:
        end = i + 1
        break

print(f"Replacing lines {start+1} to {end+1}")
print("Old block:")
for l in lines[start:end]:
    print(f"  {l}", end='')

new_block = '''    # 5. RLS isolation test — SET LOCAL requires active transaction context
    print()
    print('Testing RLS cross-tenant isolation ...')
    import psycopg2
    conn2 = psycopg2.connect("host=db dbname=agora_db user=agora_user password=agora_pass")
    conn2.autocommit = False
    cur2 = conn2.cursor()
    cur2.execute("SET LOCAL app.current_tenant_id = '00000000-0000-0000-0000-000000000000'")
    cur2.execute("SELECT COUNT(*) FROM organisations")
    count = cur2.fetchone()[0]
    conn2.rollback()
    conn2.close()
    if count == 0:
        print(f'  PASS: RLS confirmed - cross-tenant query returns 0 rows')
    else:
        print(f'  FAIL: RLS broken - cross-tenant query returned {count} rows')
'''

lines[start:end] = [new_block]

with open(TARGET, 'w') as f:
    f.writelines(lines)

print("\nRLS test replaced. Running verification:")
with open(TARGET, 'r') as f:
    content = f.read()
print("psycopg2 direct connection:", "psycopg2" in content)
