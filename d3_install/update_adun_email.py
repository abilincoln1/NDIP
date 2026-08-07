"""
NDIP — one-off fix: replace Osazemen Adun's placeholder email with her real
email, now that it's been supplied by the project owner.

Run inside ndip-backend-1:

    docker cp update_adun_email.py ndip-backend-1:/tmp/update_adun_email.py
    docker exec ndip-backend-1 python3 /tmp/update_adun_email.py
"""
import sys
sys.path.insert(0, '/app')
from app.db.database import SessionLocal
from sqlalchemy import text

MEMBERSHIP_NUMBER = 'NDIP-2026-000101'
REAL_EMAIL = 'osazadun@gmail.com'

db = SessionLocal()

before = db.execute(text(
    "SELECT membership_number, full_name, email FROM members WHERE membership_number=:num"
), {'num': MEMBERSHIP_NUMBER}).fetchone()

if not before:
    print(f"No member found with membership_number={MEMBERSHIP_NUMBER}")
    db.close()
    sys.exit(1)

print(f"Before: {before.membership_number} | {before.full_name} | {before.email}")

result = db.execute(text(
    "UPDATE members SET email=:email, updated_at=now() "
    "WHERE membership_number=:num"
), {'email': REAL_EMAIL, 'num': MEMBERSHIP_NUMBER})
db.commit()

after = db.execute(text(
    "SELECT membership_number, full_name, email FROM members WHERE membership_number=:num"
), {'num': MEMBERSHIP_NUMBER}).fetchone()

print(f"After:  {after.membership_number} | {after.full_name} | {after.email}")
print(f"\nRows updated: {result.rowcount}")
db.close()
