"""
Install D5A-S4 routes into main.py
Run: docker exec ndip-backend-1 python3 /tmp/install_s4_routes.py
"""
import os

MAIN = '/app/app/main.py'

with open(MAIN, 'r') as f:
    content = f.read()

if 'activities_v3' in content:
    print('S4 routes already registered in main.py')
else:
    append_block = """
# ── D5A-S4 Activity & Volunteer Engine ─────────────────────────────────────────
from app.api.routes.activities_v3 import router as activities_v3_router
from app.api.routes.volunteer_v3 import router as volunteer_v3_router

app.include_router(activities_v3_router)
app.include_router(volunteer_v3_router)
"""
    with open(MAIN, 'a') as f:
        f.write(append_block)
    print('S4 routes registered in main.py')

# Verify route files exist
for path in [
    '/app/app/api/routes/activities_v3.py',
    '/app/app/api/routes/volunteer_v3.py',
]:
    if os.path.exists(path):
        print(f'OK: {path}')
    else:
        print(f'MISSING: {path}')

# Syntax check
import subprocess
for path in [
    '/app/app/api/routes/activities_v3.py',
    '/app/app/api/routes/volunteer_v3.py',
]:
    r = subprocess.run(['python3', '-m', 'py_compile', path], capture_output=True, text=True)
    status = 'PASS' if r.returncode == 0 else f'FAIL: {r.stderr}'
    print(f'Syntax {path.split("/")[-1]}: {status}')

print('Done. Backend will auto-reload.')
