"""
Install D5A-S5 project routes into main.py
Run: docker exec ndip-backend-1 python3 /tmp/install_s5_routes.py
"""
import os, subprocess

MAIN = '/app/app/main.py'

with open(MAIN, 'r') as f:
    content = f.read()

if 'projects_v3' in content:
    print('S5 routes already registered in main.py')
else:
    append_block = """
# ── D5A-S5 Project Engine ────────────────────────────────────────────────────
from app.api.routes.projects_v3 import router as projects_v3_router

app.include_router(projects_v3_router)
"""
    with open(MAIN, 'a') as f:
        f.write(append_block)
    print('S5 routes registered in main.py')

# Verify
for path in ['/app/app/api/routes/projects_v3.py']:
    exists = os.path.exists(path)
    print(f'{"OK" if exists else "MISSING"}: {path}')
    if exists:
        r = subprocess.run(['python3', '-m', 'py_compile', path], capture_output=True, text=True)
        print(f'Syntax: {"PASS" if r.returncode == 0 else r.stderr}')

print('Done. Watchfiles will auto-reload.')
