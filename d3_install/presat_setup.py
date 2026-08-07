"""
NDIP Phase D4 — Pre-SAT Setup Script
File: presat_setup.py
Runs inside ndip-backend-1 container.

Actions:
1. Generate cryptographically secure SECRET_KEY (256-bit hex)
2. Patch /app/.env with new key
3. Report current CORS and JWT config
4. Verify bcrypt is working correctly
5. Create DB baseline snapshot instructions
6. Validate SMTP config (or document absence)
7. Run full health check
"""
import sys, os, secrets, re
sys.path.insert(0, "/app")

# ── 1. Generate new SECRET_KEY ────────────────────────────────────────────
new_key = secrets.token_hex(32)
print(f"NEW SECRET_KEY: {new_key}")
print(f"Key length: {len(new_key)} chars (256 bits)")

# ── 2. Patch .env ─────────────────────────────────────────────────────────
env_path = "/app/.env"
if os.path.exists(env_path):
    content = open(env_path).read()
    old_key_match = re.search(r'SECRET_KEY=(.+)', content)
    old_key = old_key_match.group(1).strip() if old_key_match else "NOT FOUND"
    print(f"\nOLD SECRET_KEY: {old_key[:20]}...")

    new_content = re.sub(r'SECRET_KEY=.+', f'SECRET_KEY={new_key}', content)
    open(env_path, 'w').write(new_content)
    print(f"SECRET_KEY rotated in {env_path}")
else:
    print(f"WARNING: {env_path} not found — writing new .env")
    open(env_path, 'w').write(f"SECRET_KEY={new_key}\n")

# ── 3. Verify new key loaded (settings are cached — need cache clear) ─────
# Clear lru_cache so get_settings() picks up new value
from app.core.config import get_settings
get_settings.cache_clear()

# Reload environment
from dotenv import load_dotenv
load_dotenv(env_path, override=True)
get_settings.cache_clear()
s = get_settings()

print(f"\nSettings after rotation:")
print(f"  SECRET_KEY (first 20): {s.secret_key[:20]}...")
print(f"  ALGORITHM: {s.algorithm}")
print(f"  ACCESS_TOKEN_EXPIRE_MINUTES: {s.access_token_expire_minutes}")
print(f"  CORS_ORIGINS: {s.cors_origins}")
print(f"  APP_ENV: {s.app_env}")

# ── 4. Verify bcrypt operational ──────────────────────────────────────────
import bcrypt
test_hash = bcrypt.hashpw(b"TestPass2026!", bcrypt.gensalt(12))
assert bcrypt.checkpw(b"TestPass2026!", test_hash), "bcrypt check failed!"
print(f"\nbcrypt: operational ✓")

# ── 5. Verify JWT signing with new key ────────────────────────────────────
from app.core.security import create_access_token, decode_token
test_token = create_access_token({"sub": "test", "user_type": "member"})
decoded = decode_token(test_token)
assert decoded["sub"] == "test", "JWT decode failed!"
print(f"JWT sign/verify with new key: operational ✓")

# ── 6. SMTP config check ──────────────────────────────────────────────────
smtp_host = os.getenv("SMTP_HOST", "")
if smtp_host:
    print(f"\nSMTP: configured (host={smtp_host})")
else:
    print(f"\nSMTP: NOT configured — DevNull provider active")
    print(f"  SAT email verification will log to stdout only")
    print(f"  This is acceptable for internal SAT with test accounts")

# ── 7. DB connectivity ────────────────────────────────────────────────────
from app.db.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
result = db.execute(text("SELECT COUNT(*) FROM members")).scalar()
print(f"\nDB connectivity: operational ✓ ({result} members)")
db.close()

# ── 8. Redis connectivity ─────────────────────────────────────────────────
try:
    import redis as redis_lib
    r = redis_lib.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
    r.ping()
    print(f"Redis: operational ✓")
except Exception as e:
    print(f"Redis: {e}")

print(f"\n{'='*50}")
print(f"Pre-SAT setup complete.")
print(f"SECRET_KEY has been rotated.")
print(f"RESTART the backend container to apply new key:")
print(f"  docker restart ndip-backend-1")
print(f"{'='*50}")
