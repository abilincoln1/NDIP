import sys
sys.path.insert(0, '/app')
from app.db.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

chapter_id = db.execute(text("SELECT id FROM chapters WHERE name = 'RTIFN Birmingham'")).scalar()
print(f'Chapter ID: {chapter_id}')

cohort = [
    {'num': 'NDIP-2026-000101', 'name': 'Osazemen Adun',       'phone': '+447832915625', 'email': 'osazadun@gmail.com'},
    {'num': 'NDIP-2026-000102', 'name': 'Rotimi Shote',         'phone': None,            'email': 'rotimiadebambo@gmail.com'},
    {'num': 'NDIP-2026-000103', 'name': 'Femi Olumiwaga',       'phone': '+447459858657', 'email': None},
    {'num': 'NDIP-2026-000104', 'name': 'Aminu Ogbolu',         'phone': '+447903282429', 'email': None},
    {'num': 'NDIP-2026-000105', 'name': 'Rotimi Oladini-Cole',  'phone': '+447400168085', 'email': 'cole_rotimi@yahoo.com'},
    {'num': 'NDIP-2026-000106', 'name': 'Tony Doherty',         'phone': '+447979796779', 'email': 'tomidoherti@presidency.com'},
    {'num': 'NDIP-2026-000107', 'name': 'Frank Golden',         'phone': None,            'email': 'info@frangolden.co.uk'},
    {'num': 'NDIP-2026-000108', 'name': 'Gbolahan Olayiwola',   'phone': '+447867024871', 'email': 'rockolayiwola@gmail.com'},
    {'num': 'NDIP-2026-000109', 'name': 'Adefolake Durosinmi',  'phone': '+44734408683',  'email': 'adurosinmi1985@gmail.com'},
]

# Members without a real email get a non-deliverable placeholder.
# @invited.ndip.rtifn.org is not a real mail domain — established in D2.5.
# Chapter Admin must update to real email before invitation can be sent.
# Slot number extracted from membership_number for uniqueness.
for c in cohort:
    if not c['email']:
        slot = c['num'].split('-')[-1]
        c['email'] = f"pending.{slot}@invited.ndip.rtifn.org"
        c['email_is_placeholder'] = True
    else:
        c['email_is_placeholder'] = False

print('Updating cohort records...')
updated = 0
for c in cohort:
    result = db.execute(text(
        "UPDATE members SET full_name=:name, phone=:phone, email=:email, "
        "residence_country='United Kingdom', chapter_id=:cid, "
        "is_active=FALSE, is_verified=FALSE, updated_at=now() "
        "WHERE membership_number=:num AND is_active=FALSE"
    ), {'name': c['name'], 'phone': c['phone'], 'email': c['email'], 'cid': str(chapter_id), 'num': c['num']})

    rows = result.rowcount
    updated += rows
    status = 'OK' if rows == 1 else 'NOT FOUND'
    email_disp = f"{c['email']} [PLACEHOLDER]" if c.get('email_is_placeholder') else c['email']
    print(f"  {c['num']}: {c['name']} | email={email_disp} | {status}")

db.commit()
print(f'\nUpdated: {updated}/9 records')
print()
print('=== COHORT VERIFICATION ===')
rows = db.execute(text(
    "SELECT membership_number, full_name, email, phone, is_active, is_verified "
    "FROM members WHERE membership_number LIKE 'NDIP-2026-0001%' "
    "ORDER BY membership_number"
)).fetchall()
for r in rows:
    print(f"  {r.membership_number}: {r.full_name} | {r.email or 'NULL'} | {r.phone or 'NULL'} | active={r.is_active}")

db.close()
print()
print('Cohort population complete. No invitations sent.')
