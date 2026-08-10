"""
Patch activities_v3.py and volunteer_v3.py to fix JSONB parameter handling.
The issue: str(dict) produces Python repr not JSON. Need json.dumps().
Also: SQLAlchemy named params cannot mix with ::jsonb cast - use cast() instead.
Run: docker exec ndip-backend-1 python3 /tmp/patch_s4_jsonb.py
"""
import json

# ── Fix activities_v3.py ───────────────────────────────────────────────────────
TARGET_A = '/app/app/api/routes/activities_v3.py'

with open(TARGET_A, 'r') as f:
    c = f.read()

# Add json import if not present
if 'import json' not in c:
    c = c.replace('import uuid', 'import uuid\nimport json')

# Fix activity_details JSONB - replace str() with json.dumps() and fix cast
c = c.replace(
    '"details": str(payload.activity_details or {}),',
    '"details": json.dumps(payload.activity_details or {}),')
c = c.replace(
    '"details": str(payload.activity_details),',
    '"details": json.dumps(payload.activity_details),')

# Fix the SQL to use CAST instead of ::jsonb with named param
c = c.replace(
    'activity_details = :details::jsonb',
    'activity_details = CAST(:details AS jsonb)')
c = c.replace(
    'activity_details = :details::jsonb',
    'activity_details = CAST(:details AS jsonb)')

# Fix the INSERT to use CAST
c = c.replace(
    ':details::jsonb,',
    'CAST(:details AS jsonb),')

with open(TARGET_A, 'w') as f:
    f.write(c)

import subprocess
r = subprocess.run(['python3', '-m', 'py_compile', TARGET_A], capture_output=True, text=True)
print(f'activities_v3.py patched — syntax: {"PASS" if r.returncode == 0 else r.stderr}')

# ── Fix volunteer_v3.py ────────────────────────────────────────────────────────
TARGET_V = '/app/app/api/routes/volunteer_v3.py'

with open(TARGET_V, 'r') as f:
    c = f.read()

if 'import json' not in c:
    c = c.replace('import uuid', 'import uuid\nimport json')

# Fix skills_used JSONB
c = c.replace(
    '"skills": str(payload.skills_used or []),',
    '"skills": json.dumps(payload.skills_used or []),')
c = c.replace(
    '"skills": str(payload.skills_used),',
    '"skills": json.dumps(payload.skills_used),')

# Fix SQL cast
c = c.replace(':skills::jsonb,', 'CAST(:skills AS jsonb),')
c = c.replace('skills_used = :skills::jsonb', 'skills_used = CAST(:skills AS jsonb)')

with open(TARGET_V, 'w') as f:
    f.write(c)

r = subprocess.run(['python3', '-m', 'py_compile', TARGET_V], capture_output=True, text=True)
print(f'volunteer_v3.py patched — syntax: {"PASS" if r.returncode == 0 else r.stderr}')

# Verify the fixes
with open(TARGET_A, 'r') as f:
    ca = f.read()
with open(TARGET_V, 'r') as f:
    cv = f.read()

print(f'activities: json.dumps present: {"json.dumps" in ca}')
print(f'activities: CAST present: {"CAST(:details AS jsonb)" in ca}')
print(f'volunteer: json.dumps present: {"json.dumps" in cv}')
print(f'volunteer: CAST present: {"CAST(:skills AS jsonb)" in cv}')
print('Done. Watchfiles will auto-reload.')
