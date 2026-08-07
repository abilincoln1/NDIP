"""
NDIP D4 SAT — Defect Fix Script
Fixes:
  D4-002: Seed a test ward so sponsorship creation works
  D4-003: Fix audit_log middleware DB URL (localhost vs db hostname)
"""
import sys, re
sys.path.insert(0, "/app")

from app.db.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# ── Fix D4-002: Seed test ward ────────────────────────────────────────────
print("=== Fix D4-002: Seeding test ward ===")

# Check ng_lgas has data (it does — 774 rows)
lga_count = db.execute(text("SELECT COUNT(*) FROM ng_lgas")).scalar()
print(f"LGAs in DB: {lga_count}")

# Insert a test ward referencing Lagos Island LGA (id=513 in our seed)
# Actually use Alimosho LGA (id=502, Lagos) — large ward area
db.execute(text("""
    INSERT INTO ng_wards (id, name, code, lga_id, created_at)
    VALUES (1, 'Alimosho Ward 1 (SAT Test)', 'LG-ALM-001', 502, now())
    ON CONFLICT (id) DO NOTHING
"""))
db.execute(text("""
    INSERT INTO ng_wards (id, name, code, lga_id, created_at)
    VALUES (2, 'Lagos Island Ward 1 (SAT Test)', 'LG-LI-001', 513, now())
    ON CONFLICT (id) DO NOTHING
"""))
db.execute(text("""
    INSERT INTO ng_wards (id, name, code, lga_id, created_at)
    VALUES (3, 'Ikeja Ward 1 (SAT Test)', 'LG-IK-001', 510, now())
    ON CONFLICT (id) DO NOTHING
"""))
db.commit()

ward_count = db.execute(text("SELECT COUNT(*) FROM ng_wards")).scalar()
print(f"Wards after fix: {ward_count}")

# ── Fix D4-003: Check audit_log middleware DB connection ──────────────────
print("\n=== Fix D4-003: Diagnosing audit_log ===")

# The AuditLogMiddleware creates its own SessionLocal()
# Check what DATABASE_URL it picks up
import os
db_url = os.environ.get('DATABASE_URL', 'NOT SET')
print(f"DATABASE_URL from env: {db_url}")

# The middleware uses app.db.database.SessionLocal which reads from settings
from app.core.config import get_settings
s = get_settings()
print(f"Settings DATABASE_URL: {s.database_url}")

# If DATABASE_URL has 'localhost' it will fail inside the container
# The correct URL inside Docker is: postgresql://agora_user:agora_pass@db:5432/agora_db
if 'localhost' in s.database_url:
    print("PROBLEM: DATABASE_URL uses 'localhost' — middleware can't reach DB from container")
    print("Fixing .env to use 'db' hostname...")

    env_path = "/app/.env"
    content = open(env_path).read()
    # Fix DATABASE_URL to use 'db' hostname
    content = re.sub(
        r'DATABASE_URL=postgresql://([^@]+)@localhost:(\d+)/(\S+)',
        r'DATABASE_URL=postgresql://\1@db:\2/\3',
        content
    )
    open(env_path, 'w').write(content)
    print("Fixed DATABASE_URL in .env")

    # Reload and verify
    from dotenv import load_dotenv
    load_dotenv(env_path, override=True)
    get_settings.cache_clear()
    s2 = get_settings()
    print(f"New DATABASE_URL: {s2.database_url}")
else:
    print(f"DATABASE_URL hostname looks correct: {s.database_url[:40]}...")

# Write a test audit log entry directly to verify the table works
try:
    db.execute(text("""
        INSERT INTO audit_log (action, endpoint, method, response_code, duration_ms)
        VALUES ('SAT_TEST', '/sat/test', 'GET', 200, 1)
    """))
    db.commit()
    count = db.execute(text("SELECT COUNT(*) FROM audit_log")).scalar()
    print(f"\naudit_log write test: OK — {count} entries now")
except Exception as e:
    print(f"audit_log write test FAILED: {e}")

db.close()

print("\n=== Fixes applied ===")
print("Restart backend to apply DATABASE_URL fix:")
print("  docker restart ndip-backend-1")
print("\nThen re-run targeted tests:")
print("  python sat_defect_retest.py")
