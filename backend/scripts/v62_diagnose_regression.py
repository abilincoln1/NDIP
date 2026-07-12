"""
Diagnose the Leadership Pack regression: both materialised paths are
hitting correctly, but the overall time is worse. Profile the actual
component breakdown with materialisation active.

Run: docker exec agora-backend-1 python scripts/v62_diagnose_regression.py
"""
import sys; sys.path.insert(0, '/app')
import time
import redis
r = redis.Redis(host='redis', port=6379, decode_responses=True)
r.delete("agora:leadership-pack:days=30")

from app.db.database import SessionLocal
db = SessionLocal()

# Test each expensive component individually
t = time.time()
from app.analytics.strategic_narratives import get_narrative_analysis
narratives = get_narrative_analysis(db, 30)
print(f"get_narrative_analysis: {time.time()-t:.3f}s, {len(narratives)} results, from_materialised={narratives[0].get('_from_materialised','no') if narratives else 'empty'}")

t = time.time()
from app.services.stakeholder_influence import get_top_influence_stakeholders
stakeholders = get_top_influence_stakeholders(db, limit=10, days=30)
print(f"get_top_influence_stakeholders: {time.time()-t:.3f}s, {len(stakeholders)} results, from_materialised={stakeholders[0].get('_from_materialised','no') if stakeholders else 'empty'}")

t = time.time()
from app.services.watchlist import generate_watchlist
wl = generate_watchlist(db, days=30)
print(f"generate_watchlist: {time.time()-t:.3f}s")

t = time.time()
from app.services.narrative_intelligence import generate_situation_room
sr = generate_situation_room(db, days=30)
print(f"generate_situation_room: {time.time()-t:.3f}s")

t = time.time()
from app.services.risk_opportunity import detect_all_risks, detect_all_opportunities
risks = detect_all_risks(db, 30)
opps = detect_all_opportunities(db, 30)
print(f"detect_all_risks + detect_all_opportunities: {time.time()-t:.3f}s")

db.close()
