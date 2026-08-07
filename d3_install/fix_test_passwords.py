import sys
sys.path.insert(0, "/app")
import bcrypt
from app.db.database import SessionLocal
from sqlalchemy import text

password = b"TestPass2026!"
hashed = bcrypt.hashpw(password, bcrypt.gensalt(12)).decode()
print(f"Hash: {hashed}")
print(f"Verify: {bcrypt.checkpw(password, hashed.encode())}")

db = SessionLocal()
result = db.execute(text("""
    UPDATE members
    SET hashed_password = :hash
    WHERE email LIKE '%@ndip.rtifn.org'
      AND is_active = TRUE
"""), {"hash": hashed})
db.commit()
db.close()
print(f"Updated {result.rowcount} test accounts with valid bcrypt hash")
