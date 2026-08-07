"""
Patches sat_host_runner_v2.py to add a warmup request before the login loop.
This prevents the first login from timing out due to cold connection pool.
Run: docker exec ndip-backend-1 python3 /tmp/patch_sat_warmup.py
"""
TARGET = '/tmp/sat_host_runner_v2.py'

with open(TARGET, 'r') as f:
    lines = f.readlines()

# Find the line where AREA 1 AUTHENTICATION starts
# We want to insert warmup BEFORE the first login attempt
insert_before = None
for i, line in enumerate(lines):
    if 'AREA 1' in line and 'AUTHENTICATION' in line:
        insert_before = i
        break

if insert_before is None:
    print("Could not find AREA 1 AUTHENTICATION marker")
    exit(1)

print(f"Found AREA 1 at line {insert_before + 1}")

warmup_block = [
    '\n',
    '# Warmup request — prevents cold connection pool timeout on first login\n',
    'try:\n',
    '    _warmup = httpx.get(f"{BASE}/health", timeout=10)\n',
    '    import time as _time\n',
    '    _time.sleep(1)\n',
    'except Exception:\n',
    '    pass\n',
    '\n',
]

lines[insert_before:insert_before] = warmup_block

with open(TARGET, 'w') as f:
    f.writelines(lines)

# Verify syntax
import subprocess
result = subprocess.run(['python3', '-m', 'py_compile', TARGET], capture_output=True, text=True)
if result.returncode == 0:
    print("Warmup patch applied. Syntax check: PASS")
else:
    print(f"Syntax check: FAIL\n{result.stderr}")
