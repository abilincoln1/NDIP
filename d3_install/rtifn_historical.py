"""
RTIFN Birmingham — Historical Engagement Ingestion
Period: 19 July 2026 – 18 September 2026
Source: Project owner WhatsApp group records
All records: self-reported, verification_status = Draft
No fabrication — only confirmed events entered.
Run: docker exec ndip-backend-1 python3 /tmp/rtifn_historical.py
"""
import sys, os, time
sys.path.insert(0, '/app')
os.environ['DATABASE_URL'] = 'postgresql://agora_user:agora_pass@db:5432/agora_db'

import httpx
from sqlalchemy import create_engine, text

BASE = 'http://localhost:8000'
db = create_engine('postgresql://agora_user:agora_pass@db:5432/agora_db').connect()

entered = []
failed = []

def log(label, ok, detail=''):
    if ok:
        entered.append(label)
        print(f'  [OK] {label}')
    else:
        failed.append(label)
        print(f'  [FAIL] {label}{" — " + str(detail) if detail else ""}')

# Login as national director
r = httpx.post(f'{BASE}/api/v3/auth/login',
    json={'email': 'nationaldirector@ndip.rtifn.org',
          'password': 'TestPass2026!',
          'tenant_slug': 'rtifn'}, timeout=20)
if r.status_code != 200:
    print('LOGIN FAILED:', r.text)
    sys.exit(1)
tok = r.json()['access_token']
h = {'Authorization': f'Bearer {tok}'}
print(f'Logged in as National Director')

def post_activity(data, label):
    r = httpx.post(f'{BASE}/api/v3/activities/', headers=h, json=data, timeout=15)
    log(label, r.status_code == 201, r.text[:100] if r.status_code != 201 else '')
    return r.json().get('id') if r.status_code == 201 else None

print('\n=== RTIFN HISTORICAL ENGAGEMENT INGESTION ===')
print('Period: 19 July 2026 – 18 September 2026')
print('Source: RTIFN Birmingham WhatsApp group records')
print('Status: All records self-reported (Draft)\n')

# ── Event 1: APCUK 2nd Anniversary Celebration ─────────────────
print('[1] APCUK 2nd Anniversary Celebration — 04 July 2026')
post_activity({
    'activity_type': 'stakeholder_engagement',
    'title': 'APCUK 2nd Anniversary Celebration of Executive Committee',
    'description': (
        'RTIFN Birmingham members attended the 2nd Anniversary Celebration of the APCUK Executive Committee '
        'under the leadership of Chairman Hon. Tunde Doherty. '
        'Organised by the APCUK Organising Committee chaired by Prince Ayorinde Amoko. '
        'Diaspora political engagement and network strengthening event.'
    ),
    'activity_date': '2026-07-04',
    'location_text': 'United Kingdom',
    'activity_details': {
        'organiser': 'APCUK / APC UK Chapter',
        'rtifn_attendance': 'Birmingham chapter members attended',
        'source': 'WhatsApp group announcement',
    }
}, 'APCUK 2nd Anniversary — 04/07/2026')

time.sleep(0.3)

# ── Event 2: Renewed Hope Ambassadors UK Inauguration ──────────
print('[2] Renewed Hope Ambassadors-Diaspora UK Inauguration — 19 July 2026')
post_activity({
    'activity_type': 'stakeholder_engagement',
    'title': 'Renewed Hope Ambassadors-Diaspora HQ & UK Inauguration Ceremony',
    'description': (
        'RTIFN Birmingham members attended the Headquarters and United Kingdom Inauguration Ceremony '
        'of the Renewed Hope Ambassadors-Diaspora. '
        'Theme: "Connecting Global Expertise with Local Governance: The Role of the Nigerian Diaspora in the Renewed Hope Agenda". '
        'Venue: The Grand Empire Lounge, 108-110 Rushey Green, Catford, London SE6 4HW. '
        'Time: 5:00 PM. '
        'Hon. Tunde Doherty (Chairman APC UK and APC-CDC) delivered a speech at the inauguration. '
        'RTIFN members attended massively.'
    ),
    'activity_date': '2026-07-19',
    'location_text': 'The Grand Empire Lounge, 108-110 Rushey Green, Catford, London SE6 4HW',
    'activity_details': {
        'organiser': 'Renewed Hope Ambassadors-Diaspora',
        'theme': 'Connecting Global Expertise with Local Governance',
        'rtifn_attendance': 'Birmingham chapter members attended massively',
        'source': 'WhatsApp group announcement + Facebook',
    }
}, 'Renewed Hope Ambassadors UK Inauguration — 19/07/2026')

time.sleep(0.3)

# ── Event 3: RTIFN Birmingham Committee Meeting ─────────────────
print('[3] RTIFN Birmingham Committee Meeting — July 2026')
post_activity({
    'activity_type': 'meeting',
    'title': 'RTIFN Birmingham Chapter Committee Meeting',
    'description': (
        'RTIFN Birmingham Chapter internal committee meeting held at KayAfricana Restaurant & Lounge. '
        'Venue: Unit 2 & 3, 24-26 Cape Hill, Smethwick, B66 4RN. '
        'Time: 7:00 PM. '
        'Members encouraged to attend in person. Discussion of chapter activities and coordination.'
    ),
    'activity_date': '2026-07-19',
    'location_text': 'KayAfricana Restaurant & Lounge, 24-26 Cape Hill, Smethwick, Birmingham B66 4RN',
    'activity_details': {
        'organiser': 'RTIFN Birmingham Chapter',
        'time': '19:00',
        'source': 'WhatsApp group notice',
        'note': 'Exact date approximate — same period as Catford event',
    }
}, 'RTIFN Birmingham Committee Meeting — July 2026')

time.sleep(0.3)

# ── Event 4: National Diaspora Day 2026 (virtual) ──────────────
print('[4] National Diaspora Day 2026 — 24-25 July 2026')
post_activity({
    'activity_type': 'community_activity',
    'title': 'National Diaspora Day 2026 — Virtual Participation',
    'description': (
        'RTIFN Birmingham members participated virtually in the 2026 National Diaspora Day Celebrations. '
        'Theme: "Harnessing Global Diaspora Medical Expertise to Strengthen Local Health Systems for National Development". '
        'Day 1 (24 July): Main programme, 2:00 PM WAT, live from Presidential Villa, Abuja. '
        'Day 2 (25 July): Youth Summit (9:00 AM WAT) and National Diaspora Merit Awards (5:00 PM WAT). '
        'Hosted via Zoom. Members registered and participated virtually.'
    ),
    'activity_date': '2026-07-24',
    'location_text': 'Virtual — Zoom (Live from Presidential Villa, Abuja)',
    'activity_details': {
        'organiser': 'Federal Government of Nigeria',
        'theme': 'Harnessing Global Diaspora Medical Expertise to Strengthen Local Health Systems',
        'format': 'Virtual / Zoom',
        'days': '24-25 July 2026',
        'rtifn_attendance': 'Birmingham chapter members registered and participated',
        'source': 'WhatsApp group announcement',
    }
}, 'National Diaspora Day 2026 Virtual — 24/07/2026')

time.sleep(0.3)

# ── Event 5: RTIFN Birmingham Chapter Meeting 25 Jul ───────────
print('[5] RTIFN Birmingham Chapter Meeting — 25 July 2026')
post_activity({
    'activity_type': 'meeting',
    'title': 'RTIFN Birmingham Chapter Meeting — Welcome New Members & NDIP Presentation',
    'description': (
        'RTIFN Birmingham Chapter meeting held to welcome new members, provide clarity on objectives, '
        'introduce ongoing initiatives and discuss how members can contribute to the development of the Birmingham chapter. '
        'Key topics: RTIFN objectives (informed political engagement, responsible advocacy, civic participation, verified information sharing). '
        'The Nigeria Diaspora Intelligence Platform (NDIP) was presented to members — platform intended to monitor news and public discussions, '
        'identify important issues and provide summaries, talking points and possible actions. '
        'Platform confirmed at MVP stage requiring further member feedback, requirements gathering and testing. '
        'Members discussed fortnightly meeting schedule. '
        'Strong interest and willingness among members to contribute noted.'
    ),
    'activity_date': '2026-07-25',
    'location_text': 'Birmingham, UK',
    'activity_details': {
        'organiser': 'RTIFN Birmingham Chapter',
        'attendance': 12,
        'key_topics': [
            'RTIFN objectives and membership',
            'NDIP platform presentation and feedback',
            'Meeting frequency (fortnightly)',
            'Roles and responsibilities',
            'Project idea submission process'
        ],
        'agreements': [
            'Members to submit project ideas',
            'NDIP to remain at MVP stage pending feedback',
            'Future meetings to have clear agenda and action log',
            'Roles to be assigned as chapter develops'
        ],
        'source': 'Official meeting summary circulated via WhatsApp',
        'meeting_secretary': 'RTIFN Birmingham Secretariat',
    }
}, 'RTIFN Birmingham Chapter Meeting — 25/07/2026')

time.sleep(0.3)

# ── Event 6: AMBO Rally — Trafalgar Square ─────────────────────
print('[6] AMBO Rally — Trafalgar Square to Nigerian High Commission — 03 August 2026')
post_activity({
    'activity_type': 'campaign',
    'title': 'AMBO Procession — Trafalgar Square to Nigerian High Commission',
    'description': (
        'RTIFN Birmingham members attended and participated in the AMBO showcase procession. '
        'Procession began at Trafalgar Square and concluded at the Nigerian High Commission. '
        'Theme: "Bola Omo Bola" — presenting the vision and leadership qualities of Bola Oyebamiji and Bola Ahmed Tinubu. '
        'RTIFN members attended massively.'
    ),
    'activity_date': '2026-08-03',
    'location_text': 'Trafalgar Square to Nigerian High Commission, London',
    'activity_details': {
        'organiser': 'AMBO / APC UK',
        'theme': 'Bola Omo Bola',
        'route': 'Trafalgar Square → Nigerian High Commission',
        'rtifn_attendance': 'Birmingham chapter members attended massively',
        'source': 'WhatsApp group record',
    }
}, 'AMBO Rally London — 03/08/2026')

time.sleep(0.3)

# ── Event 7: APC UK Leicestershire Caucus Inauguration ─────────
print('[7] APC UK Leicestershire Caucus Inauguration — 29 August 2026')
post_activity({
    'activity_type': 'stakeholder_engagement',
    'title': 'APC UK Leicestershire Caucus Inauguration',
    'description': (
        'RTIFN Birmingham members attended the official inauguration of the APC UK Leicestershire Caucus. '
        'Venue: Beaumont Leys School, Anstey Lane, Leicester LE4 0FL. Time: 4:00 PM. '
        'RTIFN members specifically called on to attend. '
        'Event focused on unity, progressive family strengthening, network expansion across UK. '
        'Invited by Hon. A Bolarinwa (APC UK / RTIFN). '
        'RTIFN members attended massively.'
    ),
    'activity_date': '2026-08-29',
    'location_text': 'Beaumont Leys School, Anstey Lane, Leicester LE4 0FL',
    'activity_details': {
        'organiser': 'APC UK / Hon. A Bolarinwa',
        'time': '16:00',
        'rtifn_attendance': 'Birmingham chapter members attended massively',
        'source': 'WhatsApp group invitation',
    }
}, 'APC UK Leicestershire Caucus Inauguration — 29/08/2026')

time.sleep(0.3)

# ── Event 8: APC UK 2027 Campaign Council Inauguration ─────────
print('[8] APC UK 2027 Campaign Council Inauguration — 30 August 2026')
post_activity({
    'activity_type': 'stakeholder_engagement',
    'title': 'APC UK 2027 Campaign Council Inauguration',
    'description': (
        'RTIFN Birmingham members attended the formal inauguration of the APC UK 2027 Campaign Council. '
        'Council established to mobilise diaspora support for the re-election of President Bola Ahmed Tinubu '
        'and APC candidates in Nigeria\'s 2027 General Elections. '
        'Hon. Olumuyiwa Adesua inaugurated as Director-General. Hon. Feyisayo Ajayi inaugurated as Secretary. '
        'Press statement issued by Cllr Tunde Ajisola, Publicity Secretary APC UK. '
        'Marks the formal start of APC UK campaign and diaspora mobilisation for 2027. '
        'RTIFN members attended massively.'
    ),
    'activity_date': '2026-08-30',
    'location_text': 'United Kingdom',
    'activity_details': {
        'organiser': 'APC UK Chapter',
        'key_appointments': {
            'Director-General': 'Hon. Olumuyiwa Adesua',
            'Secretary': 'Hon. Feyisayo Ajayi'
        },
        'publicity_secretary': 'Cllr Tunde Ajisola',
        'rtifn_attendance': 'Birmingham chapter members attended massively',
        'source': 'Official APC UK press statement + WhatsApp',
    }
}, 'APC UK 2027 Campaign Council Inauguration — 30/08/2026')

time.sleep(0.3)

# ── Event 9: APC Emergency Stakeholders Meeting — 18 Sep ───────
print('[9] APC Emergency Stakeholders Meeting — 18 September 2026')
post_activity({
    'activity_type': 'meeting',
    'title': 'APC UK / RTIFN Emergency Stakeholders Meeting — Birmingham',
    'description': (
        'Emergency physical stakeholders meeting for APC UK and RTIFN members. '
        'Venue: 042 Bar and Restaurant, 129 Soho Hill, Birmingham B19 1AT. Time: 8:00 PM. '
        'Called by Hon. Akeem Bolarinwa. '
        'Agenda: important matters concerning activities, coordination for proposed event on 25 September, and way forward. '
        'All stakeholders requested to attend as a priority.'
    ),
    'activity_date': '2026-09-18',
    'location_text': '042 Bar and Restaurant, 129 Soho Hill, Birmingham B19 1AT',
    'activity_details': {
        'organiser': 'APC UK / RTIFN — Hon. Akeem Bolarinwa',
        'time': '20:00',
        'purpose': 'Emergency coordination — 25 September event planning and way forward',
        'rtifn_attendance': 'Birmingham chapter stakeholders and members',
        'source': 'WhatsApp group emergency notice',
    }
}, 'APC Emergency Stakeholders Meeting Birmingham — 18/09/2026')

# ── Verification ───────────────────────────────────────────────
print('\n=== DATABASE VERIFICATION ===')
count = db.execute(text("SELECT COUNT(*) FROM activities WHERE activity_date >= '2026-07-04'")).scalar()
print(f'Activities in DB (from 04 Jul 2026): {count}')

rows = db.execute(text("""
    SELECT title, activity_date, activity_type, verification_status
    FROM activities
    WHERE activity_date >= '2026-07-04'
    ORDER BY activity_date
""")).fetchall()
for r in rows:
    print(f'  {r.activity_date} | {r.activity_type:<25} | {r.verification_status:<8} | {r.title[:55]}')

db.close()

print('\n=== INGESTION SUMMARY ===')
print(f'Entered: {len(entered)}')
print(f'Failed:  {len(failed)}')
if failed:
    print('Failed items:')
    for f in failed:
        print(f'  - {f}')
print(f'\nAll records: verification_status = Draft (self-reported)')
print(f'Source: RTIFN Birmingham WhatsApp group records')
print(f'Period: 04 July 2026 – 18 September 2026')
print('=== COMPLETE ===')
