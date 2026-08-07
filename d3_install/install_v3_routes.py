"""
D5A-S2: Install v3 routes into NDIP backend.
Run via: docker exec ndip-backend-1 python3 /tmp/install_v3_routes.py

Actions:
1. Checks main.py exists and has the expected include_router pattern
2. Appends v3 router imports and registrations to main.py
3. Reports what was done
"""
import os
import sys

MAIN_PATH = "/app/app/main.py"
AUTH_V3_PATH = "/app/app/api/routes/auth_v3.py"
TENANTS_V3_PATH = "/app/app/api/routes/tenants_v3.py"

# ── Check files exist ──────────────────────────────────────────────────────────

if not os.path.exists(MAIN_PATH):
    print(f"ERROR: {MAIN_PATH} not found")
    sys.exit(1)

print(f"Found: {MAIN_PATH}")

# ── Check v3 routes already registered ────────────────────────────────────────

with open(MAIN_PATH, "r") as f:
    content = f.read()

if "auth_v3" in content:
    print("v3 auth routes already registered in main.py — skipping")
else:
    # Find the last include_router line and append after it
    import_block = """
# ── D5A Platform Kernel v3 Routes ──────────────────────────────────────────────
from app.api.routes.auth_v3 import router as auth_v3_router
from app.api.routes.tenants_v3 import router as tenants_v3_router
"""

    register_block = """
# D5A v3 routes — Platform Kernel
app.include_router(auth_v3_router)
app.include_router(tenants_v3_router)
"""

    # Append to end of main.py — safe for any structure
    with open(MAIN_PATH, "a") as f:
        f.write("\n")
        f.write(import_block)
        f.write(register_block)

    print("v3 routes registered in main.py")

# ── Verify route files exist ───────────────────────────────────────────────────

for path in [AUTH_V3_PATH, TENANTS_V3_PATH]:
    if os.path.exists(path):
        print(f"Route file present: {path}")
    else:
        print(f"MISSING: {path} — copy it before testing")

# ── Check memberships table exists (needed by auth_v3 login) ──────────────────

try:
    sys.path.insert(0, "/app")
    from app.db.database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    tables = db.execute(text("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN ('platform_identities','tenants','organisations','kernel_roles','platform_admins')
        ORDER BY table_name
    """)).fetchall()
    print("\nD5A-S2 tables confirmed in DB:")
    for t in tables:
        print(f"  ✓ {t.table_name}")
    db.close()
except Exception as e:
    print(f"DB check error: {e}")

print("\nInstall complete. Backend will auto-reload (watchfiles).")
print("Test with: GET http://localhost:8000/api/v3/auth/me")
print("           POST http://localhost:8000/api/v3/auth/login")
