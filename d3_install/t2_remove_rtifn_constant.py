"""
T2 Remediation: Remove RTIFN_TENANT_ID constant from auth_v3.py
and scan all v3 code for RTIFN-specific hardcoding.
Run: docker exec ndip-backend-1 python3 /tmp/t2_remove_rtifn_constant.py
"""
import os

# ── 1. Remove RTIFN_TENANT_ID from auth_v3.py ─────────────────────────────────
TARGET = '/app/app/api/routes/auth_v3.py'

with open(TARGET, 'r') as f:
    content = f.read()

before_count = content.count('RTIFN_TENANT_ID')
print(f'Before: RTIFN_TENANT_ID occurrences = {before_count}')

# Remove the constant line (with trailing newline)
cleaned = content.replace('RTIFN_TENANT_ID = "10000000-0000-0000-0000-000000000001"\n\n', '')
cleaned = cleaned.replace("RTIFN_TENANT_ID = '10000000-0000-0000-0000-000000000001'\n\n", '')

after_count = cleaned.count('RTIFN_TENANT_ID')
print(f'After:  RTIFN_TENANT_ID occurrences = {after_count}')

if after_count == 0:
    with open(TARGET, 'w') as f:
        f.write(cleaned)
    print('PASS: RTIFN_TENANT_ID constant removed from auth_v3.py')
else:
    print(f'WARNING: {after_count} occurrences remain — manual inspection needed')
    # Show context
    for i, line in enumerate(cleaned.split('\n')):
        if 'RTIFN_TENANT_ID' in line:
            print(f'  Line {i+1}: {line}')

# ── 2. Verify syntax ───────────────────────────────────────────────────────────
import subprocess
result = subprocess.run(['python3', '-m', 'py_compile', TARGET], capture_output=True, text=True)
if result.returncode == 0:
    print('Syntax check: PASS')
else:
    print(f'Syntax check: FAIL\n{result.stderr}')

# ── 3. Scan ALL v3 and kernel files for RTIFN hardcoding ──────────────────────
print('\n--- RTIFN Hardcode Scan ---')

SCAN_DIRS = [
    '/app/app/api/routes',
    '/app/app/core',
    '/app/app/services',
    '/app/app/models',
    '/app/app/db',
]

RTIFN_PATTERNS = [
    'RTIFN_TENANT_ID',
    '10000000-0000-0000-0000-000000000001',
    'rtifn',
    'RTIFN',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',  # Birmingham org UUID
]

findings = []

for scan_dir in SCAN_DIRS:
    if not os.path.exists(scan_dir):
        continue
    for fname in sorted(os.listdir(scan_dir)):
        if not fname.endswith('.py'):
            continue
        fpath = os.path.join(scan_dir, fname)
        with open(fpath, 'r', errors='replace') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            for pattern in RTIFN_PATTERNS:
                if pattern in line and not line.strip().startswith('#'):
                    findings.append({
                        'file': fpath.replace('/app/app/', ''),
                        'line': i + 1,
                        'pattern': pattern,
                        'content': line.strip()[:100]
                    })

if findings:
    print(f'Found {len(findings)} RTIFN reference(s):')
    for f in findings:
        print(f'\n  File: {f["file"]} line {f["line"]}')
        print(f'  Pattern: {f["pattern"]}')
        print(f'  Content: {f["content"]}')
else:
    print('No hardcoded RTIFN assumptions found in v3/kernel code.')

# ── 4. Verify tenant resolution is dynamic ────────────────────────────────────
print('\n--- Dynamic Tenant Resolution Check ---')
with open(TARGET, 'r') as f:
    auth_content = f.read()

checks = [
    ('slug from request', 'tenant_slug' in auth_content),
    ('tenant lookup by slug', 'WHERE slug' in auth_content or 'slug = :slug' in auth_content),
    ('no hardcoded tenant ID', '10000000-0000-0000-0000-000000000001' not in auth_content),
    ('no RTIFN_TENANT_ID', 'RTIFN_TENANT_ID' not in auth_content),
]

all_pass = True
for label, result in checks:
    status = 'PASS' if result else 'FAIL'
    if not result:
        all_pass = False
    print(f'  [{status}] {label}')

print(f'\nT2 STATUS: {"COMPLETE" if all_pass else "INCOMPLETE - see above"}')
print('\nNote: "rtifn" slug references in tenant_config seeded data are')
print('acceptable - these are data values, not hardcoded kernel assumptions.')
print('The kernel resolves tenants dynamically by slug from the request.')
