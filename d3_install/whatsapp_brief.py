"""
RTIFN Birmingham — WhatsApp Intelligence Brief Generator
Pulls live data from NDIP APIs and formats for WhatsApp.
Run: docker exec ndip-backend-1 python3 /tmp/whatsapp_brief.py
"""
import sys, os, json
from datetime import datetime, date
sys.path.insert(0, '/app')
os.environ['DATABASE_URL'] = 'postgresql://agora_user:agora_pass@db:5432/agora_db'

import httpx
from sqlalchemy import create_engine, text

BASE = 'http://localhost:8000'
db = create_engine('postgresql://agora_user:agora_pass@db:5432/agora_db').connect()

# Login
r = httpx.post(f'{BASE}/api/v2/members/login',
    json={'email': 'nationaldirector@ndip.rtifn.org', 'password': 'TestPass2026!'}, timeout=20)
tok = r.json().get('access_token')
h = {'Authorization': f'Bearer {tok}'}

# National Pulse
pulse = httpx.get(f'{BASE}/national-pulse/executive', headers=h, timeout=30).json()
score = pulse.get('pulse_score', 0)
label = pulse.get('pulse_label', '—')
trend = pulse.get('pulse_trend', '—')
interpretation = pulse.get('interpretation', '')
# Shorten interpretation to 1 sentence
insight = interpretation.split('.')[0] + '.' if interpretation else '—'

# Narrative trends
narratives = db.execute(text("""
    SELECT narrative, mention_count, velocity
    FROM narrative_trends
    WHERE date_bucket = (SELECT MAX(date_bucket) FROM narrative_trends)
    ORDER BY mention_count DESC
    LIMIT 5
""")).fetchall()

# Activity counts
total_acts = db.execute(text("SELECT COUNT(*) FROM activities WHERE is_archived = FALSE")).scalar()
week_acts = db.execute(text("""
    SELECT COUNT(*) FROM activities
    WHERE is_archived = FALSE
    AND created_at >= NOW() - INTERVAL '7 days'
""")).scalar()
real_acts = db.execute(text("""
    SELECT COUNT(*) FROM activities
    WHERE activity_date >= '2026-07-04'
    AND title NOT ILIKE '%validation%'
    AND title NOT ILIKE '%test%'
    AND title NOT ILIKE '%standalone%'
    AND title NOT ILIKE '%ward engagement validation%'
""")).scalar()

week_end = date.today().strftime('%d %B %Y')

# Pulse emoji
if score >= 70:
    pulse_emoji = '🟢'
elif score >= 50:
    pulse_emoji = '🟡'
elif score >= 30:
    pulse_emoji = '🟠'
else:
    pulse_emoji = '🔴'

# Trend emoji
trend_emoji = '📈' if 'improv' in trend.lower() else ('📉' if 'declin' in trend.lower() else '➡️')

# Format narratives
narr_lines = []
for i, n in enumerate(narratives[:3], 1):
    vel = n.velocity
    vel_str = f'(+{vel:.0f})' if vel > 0 else f'({vel:.0f})'
    narr_lines.append(f'{i}. {n.narrative} — {n.mention_count:,} mentions {vel_str}')

brief = f"""🇳🇬 *RTIFN BIRMINGHAM — INTELLIGENCE BRIEF*
_Week ending {week_end}_

{pulse_emoji} *NATIONAL PULSE: {score}/100 — {label}*
{trend_emoji} {trend}

🔥 *TOP NARRATIVES*
{chr(10).join(narr_lines)}

📍 *CHAPTER ENGAGEMENT*
Events on record: {real_acts} (Jul–Sep 2026)
Total activity records: {total_acts}

💡 *KEY INSIGHT*
_{insight}_

📱 _RTIFN Birmingham | NDIP Platform_
_Understanding Nigeria. Understanding the Diaspora._"""

print(brief)
print('\n' + '='*50)
print('Copy the text above and paste into the RTIFN Birmingham WhatsApp group.')
print('='*50)

db.close()
